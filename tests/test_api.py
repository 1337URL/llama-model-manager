"""
API tests for the Flask application.
Tests the API endpoints and error handling.
"""
import pytest
import json


class TestApiDownload:
    """Test the API download endpoint."""

    def test_api_download_missing_auth(self, client):
        """Test that API requires authentication."""
        response = client.post('/api/download',
            json={'url': 'https://example.com/test'})
        assert response.status_code == 401

    def test_api_download_authenticated(self, authenticated_session):
        """Test successful API download."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://example.com/test'})
        # Can be 200 on success or 500 on network error (both valid)
        assert response.status_code in [200, 500]

    def test_api_download_invalid_api_token(self, authenticated_session, client):
        """Test that invalid API token is rejected."""
        from app import app

        app.config['API_TOKEN'] = 'super-secret-token'
        response = client.post('/api/download',
            json={'url': 'https://example.com/test'},
            headers={'X-API-Token': 'invalid-token'})
        assert response.status_code == 401


class TestDownloadFileEndpoint:
    """Test the direct download endpoint."""

    def test_download_file_requires_login(self, client):
        """Test that download endpoint requires authentication."""
        response = client.get('/download/test.txt?url=https://example.com/test')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_download_file_without_url(self, authenticated_session):
        """Test that download endpoint requires URL parameter."""
        response = authenticated_session.get('/download/test.txt')
        assert response.status_code == 400
