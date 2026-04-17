# URL Downloader Flask App

A password-protected Flask application that provides a web interface and API to download URLs.

## Features

- Password-protected access using Flask-Login (admin/admin123 by default)
- **API Token authentication** for programmatic access
- Web interface for downloading URLs
- RESTful API endpoint: `POST /api/download`
- File download endpoint: `/download/<filename>?url=<url>`

## Setup

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the App

```bash
python app.py
```

Access at: `http://localhost:5000`

## Credentials

- Username: `admin`
- Password: `admin123`

## API Endpoints

- `POST /api/download` - Download URL and save to file
  - **Auth**: `Authorization: Bearer <API_TOKEN>` or `X-API-Token` header
  - **Or**: Log in first (session-based)
- `GET /download/<filename>?url=<url>` - Direct file download (requires login)
- `GET /logout` - Log out and return to login page

## Rule Builder

The **Rule Builder** provides a form-based interface for creating proxy rules without writing JSON. Navigate to `/rules` and click the "Rule Builder" tab.

**Features:**
- Create rules interactively with form fields
- Support for JSON and Text transformations
- Real-time JSON preview as you build rules
- Add rules directly to your rules list

**Match Conditions** (all optional):
- **URL Pattern**: Use `*` for wildcard matching (e.g., `https://api.example.com/v1/*`)
- **Content Type**: Filter by content type (application/json, text/html, etc.)
- **HTTP Method**: Filter by method (GET, POST, PUT, DELETE, etc.)

**Transformations:**

| Type | Action | Description |
|------|--------|-------------|
| JSON | add | Add new fields to JSON responses |
| JSON | remove | Remove specified fields from JSON |
| JSON | rename | Rename JSON keys |
| JSON | set | Set default values for missing fields |
| Text | replace | Simple string replacement |
| Text | regex | Regex pattern replacement |

**Quick Reference:**

**Add fields to JSON:**
1. Transform Type: JSON
2. Action: add
3. Fields: `{"processed_by": "llama-manager"}`

**Remove sensitive fields:**
1. Transform Type: JSON
2. Action: remove
3. Fields: `password, token, secret`

**Rename keys:**
1. Transform Type: JSON
2. Action: rename
3. Key pairs: `id → user_id, name → username`

**Simple text replace:**
1. Transform Type: Text
2. Action: replace
3. Search: `www.example.com`
4. Replace: `api.example.com`

## API Token Usage

Use the API token for programmatic access without login:

```bash
# Download with API token
curl -X POST http://localhost:5000/api/download \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.pdf"}'
```

Or set the token via environment variable (overrides `.env`):
```bash
API_TOKEN=your-token curl -X POST http://localhost:5000/api/download \
  -H "X-API-Token: $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.pdf"}'
```

## Configuration

Create a `.env` file to configure these:
```bash
LLAMA_ARG_MODELS_DIR=/path/to/your/models/directory
API_TOKEN=your-secret-api-token
SECRET_KEY=your-flask-secret-key
```

- `LLAMA_ARG_MODELS_DIR` - Directory for saved downloads (default: `./downloads`)
- `API_TOKEN` - Optional API token for `/api/download` endpoint (no login required)
- `SECRET_KEY` - Flask secret key (change from default in production)

## Architecture

- **app.py**: Flask application with Flask-Login authentication
- **templates/**: HTML templates (index.html, login.html)
- **requirements.txt**: Python dependencies

## License

MIT
