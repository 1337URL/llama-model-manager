import os
import re
import threading
import uuid
import requests
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, redirect, url_for, request, Response, Blueprint
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash

# Background jobs storage
jobs = {}

# Create Flask app first
app = Flask(__name__)

# Load .env file at startup (if it exists)
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_file):
    for line in open(env_file):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            app.config[key.strip()] = value.strip()

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Load proxy rules from config (supports both .env and API updates)
proxy_rules = []
rules_config = app.config.get('PROXY_RULES', '[]')
if rules_config:
    import json
    try:
        proxy_rules = json.loads(rules_config)
    except json.JSONDecodeError:
        proxy_rules = []

# Check if SECRET_KEY is set, generate one if not
if not app.config.get('SECRET_KEY'):
    secret_key = os.urandom(12).hex()
    app.config['SECRET_KEY'] = secret_key
    print(f"[INFO] No SECRET_KEY found in .env. Generated a new one: {secret_key}")
    print(f"[INFO] For production, add SECRET_KEY={secret_key} to your .env file")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Initialize Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect to login page when user is not authenticated."""
    return redirect(url_for('login'))


# Custom user class
class User(UserMixin):
    def __init__(self, username):
        self.username = username
        self.id = username  # Flask-Login requires an 'id' attribute

    @staticmethod
    def load_user_by_username(username):
        if username in VALID_USERS:
            return User(username)
        return None


# Default credentials
VALID_USERS = {
    'admin': 'admin123'
}


# Pre-compute hashed passwords
hashed_users = {
    username: generate_password_hash(password)
    for username, password in VALID_USERS.items()
}


@login_manager.user_loader
def load_user(username):
    return User.load_user_by_username(username)


@app.route('/')
@login_required
def index():
    """Home page with download form."""
    return render_template('index.html', username=current_user.username)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username in hashed_users and check_password_hash(hashed_users[username], password):
            user = User.load_user_by_username(username)
            login_user(user)
            next_url = request.args.get('next', url_for('index'))
            return redirect(next_url)
        return 'Invalid username or password', 401

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout endpoint."""
    logout_user()
    return redirect(url_for('login'))


def download_job(job_id, url):
    """Background job to download a URL and save to file."""
    try:
        save_dir = app.config.get('LLAMA_ARG_MODELS_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads'))
        os.makedirs(save_dir, exist_ok=True)

        # Generate a safe filename from URL
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        safe_filename = unquote(parsed.path.split('/')[-1]) or 'download'
        file_path = os.path.join(save_dir, safe_filename)
        jobs[job_id] = {'status': 'pending', 'url': url, 'path': file_path}

        # Use streaming to download large files without loading into memory
        response = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        # Stream the content directly to disk in chunks
        chunk_size = 8192  # 8KB chunks
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)

        file_size = os.path.getsize(file_path)

        # Update job status with success
        jobs[job_id] = {
            'status': 'completed',
            'path': file_path,
            'saved_to': save_dir,
            'filename': safe_filename,
            'content_type': response.headers.get('content-type'),
            'content_length': file_size,
            'status_code': response.status_code
        }
    except Exception as e:
        # Update job status with error
        jobs[job_id] = {
            'status': 'error',
            'error': str(e)
        }


@app.route('/api/download', methods=['POST'])
def api_download():
    """API endpoint to submit a download job.

    Can be authenticated via:
    - Session authentication (login)
    - API_TOKEN header (from .env or environment)

    Returns a job_id for polling status.
    """
    # Check for API token authentication
    api_token = request.headers.get('Authorization') or request.headers.get('X-API-Token')

    # Get token from config if not in headers
    expected_token = app.config.get('API_TOKEN')

    if api_token and expected_token:
        # Use API token authentication (no login required)
        if api_token == expected_token:
            pass  # Token valid, proceed
        else:
            return jsonify({'error': 'Invalid API token'}), 401

    # If no valid authentication, redirect to login
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required. Provide API_TOKEN in headers or login first.'}), 401

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    url = data['url']

    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'URL must start with http:// or https://'}), 400

    # Create a job ID
    job_id = str(uuid.uuid4())
    jobs[job_id] = {'status': 'pending', 'url': url}

    # Start background thread
    thread = threading.Thread(target=download_job, args=(job_id, url))
    thread.daemon = True
    thread.start()

    return jsonify({
        'job_id': job_id,
        'status': 'pending',
        'message': 'Download started in background'
    })


@app.route('/api/job/<job_id>')
@login_required
def get_job_status(job_id):
    """Get the status of a download job."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    # Add content_length if path exists
    if 'path' in job and os.path.exists(job['path']):
        job = job | {'content_length': os.path.getsize(job['path'])}
    elif 'path' in job:
        job = job | {'content_length': 0}

    return jsonify(job)


# Reverse Proxy Blueprint
def reverse_proxy_handler(method, subpath, upstream_url):
    """
    Internal handler that forwards requests to upstream API.
    Returns a Flask response object.
    """
    # If subpath is already a full URL, use it directly
    if subpath.startswith('http://') or subpath.startswith('https://'):
        final_url = subpath
    else:
        # Build upstream URL by combining upstream_url and subpath
        upstream_url = upstream_url.rstrip('/')
        if subpath and not upstream_url.endswith('/'):
            upstream_url += '/'
        final_url = upstream_url + subpath.lstrip('/')

    # Build final URL with query string
    upstream_url = final_url

    # Forward query string if present
    query_string = request.query_string.decode('utf-8')
    if query_string:
        upstream_url += '?' + query_string

    # Get headers to forward
    headers_to_forward = {}
    for key, value in request.headers:
        # Skip sensitive headers
        if key.lower() not in ['cookie', 'authorization', 'set-cookie',
                                'x-requested-with', 'x-csrf-token',
                                'host', 'content-length']:
            headers_to_forward[key] = value

    # Prepare request
    try:
        timeout = int(app.config.get('PROXY_TIMEOUT', 30))
        # Use request.args for query params and data for body
        upstream_response = requests.request(
            method=method,
            url=upstream_url,
            data=request.get_data(),
            headers=headers_to_forward,
            timeout=timeout
        )

        # Create response with streaming
        response = Response(
            upstream_response.content,
            status=upstream_response.status_code,
            mimetype=upstream_response.headers.get('Content-Type', 'application/json')
        )

        # Copy headers
        for key, value in upstream_response.headers.items():
            if key.lower() not in ['transfer-encoding', 'content-encoding']:
                response.headers[key] = value

        # Broadcast proxy request to connected clients
        request_data = {
            'id': str(uuid.uuid4()),
            'method': request.method,
            'status': upstream_response.status_code,
            'url': subpath,
            'timestamp': str(datetime.now()),
            'request': request.get_data().decode(errors='replace'),
            'request_headers': headers_to_forward,
            'response': upstream_response.content.decode(errors='replace'),
            'response_headers': dict(upstream_response.headers)
        }
        socketio.emit('proxy_traffic', request_data)

        return response

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Upstream request timed out'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Failed to connect to upstream server'}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Upstream request failed: {str(e)}'}), 502


# Rule Engine Functions
def _rule_matches(rule, method, subpath, content_type, content=None):
    """Check if a rule matches the current request/response."""
    match = rule.get('match', {})

    # Check URL pattern (prefix matching)
    url_pattern = match.get('url')
    if url_pattern:
        # Support wildcard patterns like "https://api.example.com/v1/*"
        if not subpath.startswith(url_pattern.rstrip('/*')):
            return False

    # Check content type
    content_type_pattern = match.get('content_type')
    if content_type_pattern:
        if content_type and content_type_pattern.lower() not in content_type.lower():
            return False

    # Check HTTP method
    method_pattern = match.get('method')
    if method_pattern:
        if method.upper() != method_pattern.upper():
            return False

    return True


def _apply_rule(rule, result):
    """Apply a single rule's transformation to the result."""
    transform = rule.get('transform', {})
    transform_type = transform.get('type', '')
    action = transform.get('action', '')

    if transform_type == 'json':
        return _transform_json(result, transform)
    elif transform_type == 'text':
        return _transform_text(result, transform)

    return result


def _transform_json(result, transform):
    """Apply JSON transformations to the result."""
    content = result['content']
    action = transform.get('action', '')

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Not valid JSON, return as-is
        return result

    modified = False
    rules_applied = []

    if action == 'add':
        # Add new fields to JSON
        fields_to_add = transform.get('fields', {})
        for key, value in fields_to_add.items():
            data[key] = value
        modified = True
        rules_applied.append(f"Added fields: {list(fields_to_add.keys())}")

    elif action == 'remove':
        # Remove fields from JSON
        fields_to_remove = transform.get('fields', [])
        for field in fields_to_remove:
            if field in data:
                del data[field]
                modified = True
        rules_applied.append(f"Removed fields: {fields_to_remove}")

    elif action == 'rename':
        # Rename JSON keys
        renames = transform.get('renames', {})
        for old_key, new_key in renames.items():
            if old_key in data:
                data[new_key] = data.pop(old_key)
                modified = True
        rules_applied.append(f"Renamed keys: {list(renames.keys())}")

    elif action == 'set':
        # Set default values for missing fields
        fields_to_set = transform.get('fields', {})
        for key, value in fields_to_set.items():
            if key not in data:
                data[key] = value
                modified = True
        rules_applied.append(f"Set defaults for: {list(fields_to_set.keys())}")

    if modified:
        result['content'] = json.dumps(data, indent=2)
        result['modified'] = True
        result['rules_applied'] = rules_applied

    return result


def _transform_text(result, transform):
    """Apply text transformations to the result."""
    content = result['content']
    transform_type = transform.get('type', '')
    action = transform.get('action', '')

    modified = False
    rules_applied = []

    if action == 'replace':
        # Simple string replacement
        search = transform.get('search', '')
        replace = transform.get('replace', '')
        if search and search in content:
            new_content = content.replace(search, replace)
            if new_content != content:
                content = new_content
                modified = True
                rules_applied.append(f"Replaced '{search}' with '{replace}'")

    elif action == 'regex':
        # Regex-based replacement
        pattern = transform.get('pattern', '')
        replacement = transform.get('replacement', '')
        if pattern:
            try:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    modified = True
                    rules_applied.append(f"Applied regex pattern '{pattern}'")
            except re.error:
                pass  # Invalid regex, skip

    if modified:
        result['content'] = content
        result['modified'] = True
        result['rules_applied'] = rules_applied

    return result


def _sanitize_rules(rules):
    """Sanitize and validate rule configuration."""
    sanitized = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        sanitized_rule = {}
        # Sanitize match conditions
        if 'match' in rule and isinstance(rule['match'], dict):
            sanitized_match = {}
            for key in ['url', 'content_type', 'method']:
                if key in rule['match']:
                    sanitized_match[key] = str(rule['match'][key])
            sanitized_rule['match'] = sanitized_match
        # Sanitize transform
        if 'transform' in rule and isinstance(rule['transform'], dict):
            sanitized_transform = {}
            for key in ['type', 'action']:
                if key in rule['transform']:
                    sanitized_transform[key] = str(rule['transform'][key])
            sanitized_rule['transform'] = sanitized_transform
            # Sanitize action-specific fields
            if sanitized_transform.get('type') == 'json':
                if 'fields' in rule['transform']:
                    sanitized_rule['transform']['fields'] = rule['transform']['fields']
                if 'renames' in rule['transform']:
                    sanitized_rule['transform']['renames'] = {
                        k: str(v) for k, v in rule['transform']['renames'].items()
                    }
            elif sanitized_transform.get('type') == 'text':
                if 'search' in rule['transform']:
                    sanitized_rule['transform']['search'] = str(rule['transform']['search'])
                if 'replace' in rule['transform']:
                    sanitized_rule['transform']['replace'] = str(rule['transform']['replace'])
                if 'pattern' in rule['transform']:
                    sanitized_rule['transform']['pattern'] = str(rule['transform']['pattern'])
                if 'replacement' in rule['transform']:
                    sanitized_rule['transform']['replacement'] = str(rule['transform']['replacement'])
        sanitized.append(sanitized_rule)
    return sanitized


def apply_proxy_rules(content, method, subpath, content_type):
    """Apply matching rules to proxied content."""
    result = {'content': content, 'modified': False, 'rules_applied': []}

    for rule in proxy_rules:
        # Check if rule matches
        if _rule_matches(rule, method, subpath, content_type, content):
            # Apply transformation
            result = _apply_rule(rule, result)

    return result


# Create reverse proxy blueprint
reverse_proxy_bp = Blueprint('reverse_proxy', __name__, url_prefix='/api')


@reverse_proxy_bp.after_request
def add_cors_headers(response):
    """Add CORS headers if enabled."""
    if app.config.get('PROXY_ENABLE_CORS', 'false').lower() == 'true':
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@reverse_proxy_bp.route('/rules', methods=['GET'])
def get_proxy_rules():
    """Get current proxy rules configuration."""
    return jsonify({'rules': proxy_rules})


@reverse_proxy_bp.route('/rules', methods=['POST'])
@login_required
def set_proxy_rules():
    """Update proxy rules configuration."""
    data = request.get_json()
    if not data or 'rules' not in data:
        return jsonify({'error': 'rules field required'}), 400

    # Sanitize and store rules
    new_rules = _sanitize_rules(data['rules'])
    app.config['PROXY_RULES'] = json.dumps(new_rules)
    global proxy_rules
    proxy_rules = new_rules

    return jsonify({'message': 'Rules updated', 'rules': new_rules})


@reverse_proxy_bp.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy_request(subpath):
    """Forward requests to upstream API.

    Authentication can be provided via:
    - API_TOKEN header (from .env or environment)
    - Session authentication (login)
    """
    # Track if we successfully authenticated
    auth_success = False

    # Check for API token authentication
    api_token = request.headers.get('Authorization') or request.headers.get('X-API-Token')
    expected_token = app.config.get('API_TOKEN')

    if api_token and expected_token:
        # Use API token authentication (no login required)
        if api_token == expected_token:
            auth_success = True  # Token valid, proceed
        else:
            return jsonify({'error': 'Invalid API token'}), 401

    # Also check if user is logged in (session authentication)
    if current_user.is_authenticated:
        auth_success = True

    # If no valid authentication, require login
    if not auth_success:
        return jsonify({'error': 'Authentication required. Provide API_TOKEN in headers or login first.'}), 401

    # Get upstream URL from config
    upstream_url = app.config.get('PROXY_UPSTREAM_URL')
    if not upstream_url:
        return jsonify({'error': 'PROXY_UPSTREAM_URL not configured'}), 500

    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        response = Response('', status=204)
        if app.config.get('PROXY_ENABLE_CORS', 'false').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '86400'
        return response

    # Forward the request
    response = reverse_proxy_handler(request.method, subpath, upstream_url)

    # Apply rules to response content if it has body
    if hasattr(response, 'data') and response.data and response.data.strip():
        content_type = response.headers.get('Content-Type', '')
        # Extract content type for matching (before any charset parameters)
        content_type_main = content_type.split(';')[0].strip() if ';' in content_type else content_type
        rules_result = apply_proxy_rules(response.data.decode('utf-8', errors='replace'),
                                         request.method, subpath, content_type_main)
        if rules_result.get('modified'):
            response = Response(rules_result['content'],
                               status=response.status_code,
                               mimetype=content_type)
            # Update response headers
            for key, value in response.headers.items():
                if key.lower() not in ['transfer-encoding', 'content-encoding']:
                    response.headers[key] = value

    return response


# Register the blueprint
app.register_blueprint(reverse_proxy_bp)


@app.route('/requests')
@login_required
def requests_page():
    """Real-time proxy requests monitoring page."""
    return render_template('requests.html', username=current_user.username)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
