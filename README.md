# URL Downloader Flask App

A password-protected Flask application that provides a web interface and API to download URLs.

## Features

- Password-protected access using Flask-Login (admin/admin123 by default)
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

- `POST /api/download` - Download URL and return content as JSON
- `GET /download/<filename>?url=<url>` - Direct file download (saves to `LLAMA_ARG_MODELS_DIR`, requires login)
- `GET /logout` - Log out and return to login page

## Configuration

- `SECRET_KEY` - Flask secret key (set in `.env`)
- `LLAMA_ARG_MODELS_DIR` - Directory for saved downloads (set in `.env` or environment variable, default: `./downloads`)

Create a `.env` file to configure these:
```bash
LLAMA_ARG_MODELS_DIR=/path/to/your/models/directory
```

## Architecture

- **app.py**: Flask application with Flask-Login authentication
- **templates/**: HTML templates (index.html, login.html)
- **requirements.txt**: Python dependencies

## License

MIT
