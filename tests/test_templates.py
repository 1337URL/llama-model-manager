"""
Template tests for the Flask application.
Tests that templates are rendered correctly.
"""
import pytest


class TestTemplates:
    """Test template rendering."""

    def test_login_page_structure(self, client):
        """Test that login page renders with correct structure."""
        response = client.get('/login')
        assert response.status_code == 200

        # Check for expected elements in the page
        response_text = response.data.decode()
        assert 'username' in response_text.lower()
        assert 'password' in response_text.lower()
        assert 'login' in response_text.lower()

    def test_home_page_requires_auth(self, client):
        """Test that home page requires authentication."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_login_page_has_demo_credentials(self, client):
        """Test that login page shows demo credentials."""
        response = client.get('/login')
        assert response.status_code == 200

        # Check for demo credentials message
        response_text = response.data.decode()
        assert 'admin' in response_text or 'example' in response_text.lower()

    def test_home_page_redirects_to_login(self, client):
        """Test that home page redirects when not authenticated."""
        response = client.get('/')
        assert response.status_code == 302

        # After redirect, we get login page
        response = client.get('/login')
        response_text = response.data.decode()
        assert '<form' in response_text


class TestTemplateContent:
    """Test template content and accessibility features."""

    def test_login_page_has_title(self, client):
        """Test that login page has a proper title."""
        response = client.get('/login')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert '<title>' in response_text

    def test_login_page_has_welcome(self, client):
        """Test that login page has welcome message."""
        response = client.get('/login')
        response_text = response.data.decode()
        assert 'welcome' in response_text.lower()

    def test_login_page_has_demo_info(self, client):
        """Test that login page has demo credentials info."""
        response = client.get('/login')
        response_text = response.data.decode()
        assert 'demo' in response_text.lower() or 'admin' in response_text
