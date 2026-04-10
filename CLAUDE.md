# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Commands

- Create venv (first time only): `python3 -m venv venv`
- Activate venv: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Run the app: `python app.py`
- Run a single test: (no tests exist yet)
- Restart Flask: `pkill -f 'python app.py' && python app.py`

## Architecture

### Application Structure

```
llama-model-manager/
├── app.py              # Flask application entry point
├── requirements.txt    # Python dependencies
├── README.md           # User documentation
└── templates/
    ├── index.html      # Home page with download form
    └── login.html      # Login page
```

### Key Components

**app.py** - Main Flask application with:

- **Flask-Login authentication**: Uses Flask-Login for session management
- **Password protection**: Default credentials are `admin` / `admin123` (passwords are hashed)
- **File saving**: Downloads are saved to directory from `app.config['LLAMA_ARG_MODELS_DIR']` (set from `.env` at startup)
- **Routes**:
  - `GET /` - Home page (requires login)
  - `GET/POST /login` - Login page and authentication
  - `GET /logout` - Logout endpoint
  - `POST /api/download` - API endpoint to download URL content as JSON
  - `GET /download/<filename>?url=<url>` - Direct file download to models directory

**templates/index.html** - Frontend with:
- URL input form
- AJAX calls to `/api/download`
- Displays preview of downloaded content (first 1000 characters)
- Links to direct download endpoints

**templates/login.html** - Login page with:
- Username/password form
- Demo credentials displayed

### Authentication Flow

1. User submits credentials via `POST /login`
2. Credentials validated against `hashed_users` dict (passwords are hashed with `werkzeug.security`)
3. On success, `login_user()` stores username in Flask-Login session
4. Protected routes use `@login_required` decorator which checks `current_user.is_authenticated`

### API Endpoints

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/api/download` | POST | Returns URL content as JSON (preview of first 1000 chars) |
| `/download/<filename>?url=<url>` | GET | Direct file download (saves to `LLAMA_ARG_MODELS_DIR`, requires authentication) |
| `/logout` | GET | Logout and redirect to login |

### Development Notes

- Uses Flask-Login for session management (stores username in session)
- For production, configure proper `SECRET_KEY` in `.env` or `app.config`
- Timeout of 30 seconds for `/api/download`, 60 seconds for direct downloads
- Uses `requests` library with `Mozilla/5.0` User-Agent header
- Environment variables from `.env` are stored in `app.config` at startup
- `LLAMA_ARG_MODELS_DIR` is retrieved from `app.config['LLAMA_ARG_MODELS_DIR']` (default: `./downloads`)
- This system runs on Debian, so use a virtual environment for pip:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
