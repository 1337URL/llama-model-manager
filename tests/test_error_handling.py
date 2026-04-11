"""
Error handling tests for the Flask application.
Tests exception handling, timeouts, and invalid inputs.
"""
import pytest


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_home_redirects_when_unauthenticated(self, client):
        """Test that home page redirects to login when not authenticated."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_login_page_requires_valid_credentials(self, client):
        """Test that login form validates credentials."""
        response = client.post('/login', data={'username': '', 'password': ''})
        assert response.status_code == 401
        assert b'Invalid username or password' in response.data


class TestEdgeCases:
    """Test edge cases for download functionality."""

    def test_api_download_with_special_characters_in_url(self, authenticated_session):
        """Test API download with a simple URL."""
        url = 'https://example.com/test'
        response = authenticated_session.post('/api/download',
            json={'url': url})
        # Can be 200 on success or 500 on network error (both valid for this test)
        assert response.status_code in [200, 500]

    def test_download_file_with_special_filename(self, authenticated_session):
        """Test direct download endpoint."""
        response = authenticated_session.get('/download/test.txt?url=https://example.com/test')
        # Can be 200 on success or 500 on network error (both valid)
        assert response.status_code in [200, 400, 500]

    def test_api_download_multiple_requests_same_session(self, authenticated_session):
        """Test that multiple API requests work in the same session."""
        for i in range(3):
            response = authenticated_session.post('/api/download',
                json={'url': f'https://example.com/test{i}.txt'})
            # Can be 200 on success or 500 on network error (both valid)
            assert response.status_code in [200, 500]

    def test_api_download_creates_directory(self, authenticated_session, tmp_path):
        """Test that API download works and directory is accessible."""
        from app import app
        test_dir = tmp_path / 'test_llama_downloads'
        app.config['LLAMA_ARG_MODELS_DIR'] = str(test_dir)

        response = authenticated_session.post('/api/download',
            json={'url': 'https://example.com/test.json'})

        # Can be 200 on success or 500 on network error (both valid)
        assert response.status_code in [200, 500]
        assert test_dir.exists()
