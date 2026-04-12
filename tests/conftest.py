"""
Pytest configuration and fixtures for testing the Flask application.
"""
import pytest
import os
import shutil
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-flask-login-session'
    app.config['LLAMA_ARG_MODELS_DIR'] = '/tmp/test_llama_downloads'
    app.config['API_TOKEN'] = 'test-token-123'
    app.config['PROXY_UPSTREAM_URL'] = 'https://httpbin.org'
    app.config['PROXY_ENABLE_CORS'] = 'false'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Clean up any existing test downloads directory
    if os.path.exists(app.config['LLAMA_ARG_MODELS_DIR']):
        shutil.rmtree(app.config['LLAMA_ARG_MODELS_DIR'])

    with app.test_client() as client:
        yield client

    # Clean up after tests
    if os.path.exists(app.config['LLAMA_ARG_MODELS_DIR']):
        shutil.rmtree(app.config['LLAMA_ARG_MODELS_DIR'])


@pytest.fixture
def authenticated_session():
    """
    Create an authenticated test client that's logged in as admin.
    Use this fixture to test authenticated endpoints.
    """
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-flask-login-session'
    app.config['LLAMA_ARG_MODELS_DIR'] = '/tmp/test_llama_downloads'
    app.config['API_TOKEN'] = 'test-token-123'
    app.config['PROXY_UPSTREAM_URL'] = 'https://httpbin.org'
    app.config['PROXY_ENABLE_CORS'] = 'false'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    client = app.test_client()
    # Log in as admin
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    yield client
    # Cleanup happens automatically when client is garbage collected
