import os
import requests
from flask import Flask, render_template, jsonify, redirect, url_for, send_file, request
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


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


@app.route('/api/download', methods=['POST'])
def api_download():
    """API endpoint to download a URL and save to file.

    Can be authenticated via:
    - Session authentication (login)
    - API_TOKEN header (from .env or environment)
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

    return handle_url_download(url)


@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    """Download a file from URL and save to LLAMA_ARG_MODELS_DIR."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    return handle_url_download(url)


def handle_url_download(url):
    """Handle downloading a URL and saving to file using streaming."""
    save_dir = app.config.get('LLAMA_ARG_MODELS_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads'))
    os.makedirs(save_dir, exist_ok=True)

    try:
        # Generate a safe filename from URL
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        safe_filename = unquote(parsed.path.split('/')[-1]) or 'download'
        file_path = os.path.join(save_dir, safe_filename)

        # Use streaming to download large files without loading into memory
        response = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        # Stream the content directly to disk in chunks
        chunk_size = 8192  # 8KB chunks
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)

        return jsonify({
            'success': True,
            'path': file_path,
            'saved_to': save_dir,
            'filename': safe_filename,
            'content_type': response.headers.get('content-type')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
