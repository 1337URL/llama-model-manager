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
