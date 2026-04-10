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
- **API Token**: Optional `API_TOKEN` for programmatic access (set in `.env`)
- **File saving**: Downloads are saved to directory from `app.config['LLAMA_ARG_MODELS_DIR']` (set from `.env` at startup)
- **Routes**:
  - `GET /` - Home page (requires login)
  - `GET/POST /login` - Login page and authentication
  - `GET /logout` - Logout endpoint
  - `POST /api/download` - API endpoint to download URL content as JSON (supports API token or login)
  - `GET /download/<filename>?url=<url>` - Direct file download to models directory (requires login)

**templates/index.html** - Frontend with:
- URL input form
- AJAX calls to `/api/download`
- Displays preview of downloaded content (first 1000 characters)
- Links to direct download endpoints

**templates/login.html** - Login page with:
- Username/password form
- Demo credentials displayed

### Authentication Flow

**Option 1: Login Session**
1. User submits credentials via `POST /login`
2. Credentials validated against `hashed_users` dict (passwords are hashed with `werkzeug.security`)
3. On success, `login_user()` stores username in Flask-Login session
4. Protected routes use `@login_required` decorator which checks `current_user.is_authenticated`

**Option 2: API Token** (for programmatic access)
1. Set `API_TOKEN=your-secret-token` in `.env`
2. Include token in header: `Authorization: Bearer <token>` or `X-API-Token: <token>`
3. `/api/download` endpoint accepts either login session OR valid API token

### API Endpoints

| Endpoint | Method | Auth | Description |
|---------|--------|-------------|
| `/api/download` | POST | API_TOKEN or Login | Download URL and save to file (returns JSON response) |
| `/download/<filename>?url=<url>` | GET | Login | Direct file download (saves to `LLAMA_ARG_MODELS_DIR`) |
| `/logout` | GET | N/A | Logout and redirect to login |

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

### Git Workflow

- After making changes, commit with: `git add . && git commit -m "brief description"`
- Add `.env` files to `.gitignore` to avoid committing secrets
- Run `/loop 60m git log -1 --format="%ai %s"` to check commit history periodically

### Feature Development Pattern

**Starting a new feature:**
1. Create a feature branch: `git checkout -b feat/<feature-name>`
2. Make all changes on the feature branch
3. Commit frequently with descriptive messages
4. When done: `git push origin feat/<feature-name>`

**Merging a feature:**
1. Create PR from feature branch to main
2. Review and test the feature
3. Merge PR when approved
4. Delete feature branch: `git branch -D feat/<feature-name>`

### Auto-Commit Reminder

Before finishing any feature or task:
1. Review all changes
2. Test the new functionality
3. Run: `git add . && git commit -m "feature name"`
4. Push feature branch to remote
5. Merge PR when ready
