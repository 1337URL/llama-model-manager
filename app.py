import os
import threading
import uuid
import requests
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
    return reverse_proxy_handler(request.method, subpath, upstream_url)


# Register the blueprint
app.register_blueprint(reverse_proxy_bp)


@app.route('/requests')
@login_required
def requests_page():
    """Real-time proxy requests monitoring page."""
    return render_template('requests.html', username=current_user.username)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
