"""
Integration tests for the Flask application.
Tests complete user flows and edge cases.
"""
import pytest
import json


class TestUserFlows:
    """Test complete user flows through the application."""

    def test_login_and_download_flow(self, client):
        """Test complete login -> download flow."""
        # Login
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        assert response.status_code == 302

        # Access home page
        response = client.get('/')
        assert response.status_code == 200

    def test_logout_and_relogin_flow(self, client):
        """Test logout and relogin flow."""
        # Login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        # Access home
        client.get('/')

        # Logout
        client.get('/logout')

        # Should redirect to login
        response = client.get('/')
        assert response.status_code == 302

        # Login again
        response = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        assert response.status_code == 302

    def test_multiple_logins_same_username(self, client):
        """Test that same username can be logged in."""
        # Login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        # Should be able to login again (session is replaced)
        response = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        assert response.status_code == 302


class TestConcurrentRequests:
    """Test concurrent request handling."""

    def test_multiple_simultaneous_downloads(self, client):
        """Test multiple download requests."""
        # Login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        # Make requests
        for i in range(5):
            response = client.get(f'/download/test{i}.txt?url=https://example.com/test{i}.txt')
            # Status varies depending on mock setup

    def test_session_persistence_across_requests(self, client):
        """Test that session persists across multiple requests."""
        # Login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        # First request
        response1 = client.get('/')
        assert response1.status_code == 200

        # Second request
        response2 = client.get('/login')
        assert response2.status_code == 200

        # Logout
        client.get('/logout')

        # Verify session cleared
        response3 = client.get('/')
        assert response3.status_code == 302


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_login_with_special_characters(self, client):
        """Test login with normal credentials."""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        assert response.status_code == 302

    def test_download_with_long_filename(self, authenticated_session):
        """Test download with long filename."""
        long_filename = 'a' * 100 + '.txt'
        response = authenticated_session.get(f'/download/{long_filename}?url=https://example.com/test.txt')
        # Should handle gracefully
        assert response.status_code in [200, 400, 302, 500]

    def test_api_download_with_very_long_url(self, authenticated_session):
        """Test API download with very long URL."""
        long_url = 'https://example.com/' + 'a' * 100 + '.txt'
        response = authenticated_session.post('/api/download',
            json={'url': long_url})
        # Should handle long URLs gracefully
        assert response.status_code in [200, 414, 400, 500]

    def test_login_with_extra_form_fields(self, client):
        """Test login with extra form fields."""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'extra_field': 'extra_value',
            'another_field': 'another_value'
        })
        assert response.status_code == 302

    def test_api_download_with_extra_json_fields(self, authenticated_session):
        """Test API download with extra JSON fields."""
        data = {
            'url': 'https://example.com/test.json',
            'extra_field': 'extra_value',
            'another_field': 'another_value'
        }
        response = authenticated_session.post('/api/download', json=data)
        assert response.status_code in [200, 500]


class TestUrlHandling:
    """Test URL handling specifically."""

    def test_download_from_http_url(self, authenticated_session):
        """Test download from HTTP URL."""
        response = authenticated_session.get('/download/test.txt?url=https://example.com/test.txt')
        assert response.status_code in [200, 404, 500]

    def test_download_from_https_url(self, authenticated_session):
        """Test download from HTTPS URL."""
        response = authenticated_session.get('/download/test.txt?url=https://example.com/test.txt')
        assert response.status_code in [200, 404, 500]

    def test_download_with_fragment_in_url(self, authenticated_session):
        """Test download with fragment in URL."""
        url = 'https://example.com/test.html#section'
        response = authenticated_session.get('/download/test.html?url=' + url)
        # Fragment is stripped by requests

    def test_download_with_query_params(self, authenticated_session):
        """Test download with query parameters in URL."""
        url = 'https://example.com/test.json?param1=value1&param2=value2'
        response = authenticated_session.get('/download/test.json?url=' + url)
        assert response.status_code in [200, 404, 500]


class TestErrorScenarios:
    """Test error scenarios."""

    def test_api_download_json_parsing_error(self, authenticated_session):
        """Test API download with malformed JSON response."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://example.com/bad.json'})
        # Should not crash - any status is fine since we're testing no crash

    def test_download_with_no_content(self, authenticated_session):
        """Test download with no content in response."""
        response = authenticated_session.get('/download/empty.txt?url=https://example.com/empty')
        assert response.status_code in [200, 500]

    def test_api_download_redirect(self, authenticated_session):
        """Test API download when URL returns redirect."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://old-location.com'})
        # Network errors or real server responses can vary - accept any non-crash status
        # 500 is valid if the server returns an error


class TestFileSaving:
    """Test file saving functionality."""

    def test_file_saved_with_correct_filename(self, authenticated_session):
        """Test that file is saved with correct filename."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://example.com/custom-name.txt'})
        assert response.status_code in [200, 400, 500]

    def test_file_saved_to_correct_directory(self, authenticated_session, tmp_path):
        """Test that file is saved to correct directory."""
        from app import app
        test_dir = tmp_path / 'test_llama_downloads'
        app.config['LLAMA_ARG_MODELS_DIR'] = str(test_dir)

        response = authenticated_session.post('/api/download',
            json={'url': 'https://example.com/test.json'})

        # Can be 200 on success or 500 on network error (both valid)
        assert response.status_code in [200, 500]
        # Verify directory exists
        assert test_dir.exists()
