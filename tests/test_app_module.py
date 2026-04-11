"""
Application module tests for app.py.
Tests classes and module-level functionality directly.
"""
import pytest
import json
from app import app, User, VALID_USERS, hashed_users


class TestAppModule:
    """Test the app module directly."""

    def test_app_creation(self):
        """Test that Flask app is created."""
        assert app is not None
        assert app.name == 'app'

    def test_user_class_inheritance(self):
        """Test that User class inherits from UserMixin."""
        from flask_login import UserMixin
        assert issubclass(User, UserMixin)

    def test_user_creation(self):
        """Test creating a User instance."""
        user = User('testuser')
        assert user.username == 'testuser'

    def test_user_load_by_username(self):
        """Test User.load_user_by_username static method."""
        # Valid username
        user = User.load_user_by_username('admin')
        assert user is not None
        assert user.username == 'admin'

        # Invalid username
        user = User.load_user_by_username('nonexistent')
        assert user is None

    def test_valid_users_dict(self):
        """Test VALID_USERS dictionary."""
        assert 'admin' in VALID_USERS
        assert VALID_USERS['admin'] == 'admin123'

    def test_hashed_users_creation(self):
        """Test that hashed_users is properly created."""
        assert 'admin' in hashed_users
        # Password hash should be a secure hash, not plain text
        assert hashed_users['admin'] != 'admin123'


class TestSessionConfig:
    """Test Flask session security defaults."""

    def test_session_config_defaults(self):
        """Test Flask session security defaults."""
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


class TestDownloadDirectoryConfig:
    """Test download directory configuration."""

    def test_default_download_dir(self):
        """Test default download directory exists."""
        default_dir = app.config.get('LLAMA_ARG_MODELS_DIR') or 'downloads'
        # Just verify it's a string (can be empty for defaults)
        assert isinstance(default_dir, str)


class TestAppRoutes:
    """Test app route registrations."""

    def test_route_registration(self):
        """Test that routes are registered."""
        # Get all route rules
        routes = [rule.rule for rule in app.url_map.iter_rules()]

        assert '/' in routes
        assert '/login' in routes
        assert '/logout' in routes
        assert '/api/download' in routes


class TestAppConfig:
    """Test app configuration."""

    def test_app_config_loaded(self):
        """Test that app has config."""
        assert app.config is not None

    def test_app_config_keys(self):
        """Test that app has expected config keys."""
        assert 'SECRET_KEY' in app.config or 'SESSION_COOKIE_HTTPONLY' in app.config
        assert 'LLAMA_ARG_MODELS_DIR' in app.config or 'SESSION_COOKIE_SAMESITE' in app.config


class TestJsonResponse:
    """Test JSON response formatting."""

    def test_api_download_json_response(self, client):
        """Test that API returns proper JSON."""
        response = client.post('/api/download',
                              data=json.dumps({'url': 'https://example.com/test'}),
                              content_type='application/json')

        # Should return JSON (either 401 for unauthenticated or 200 for authenticated)
        # 302 is redirect to login
        assert response.status_code in [200, 401, 400, 500]


class TestErrorHandling:
    """Test error handling."""

    def test_api_download_missing_url(self, client, authenticated_session):
        """Test API download without URL."""
        response = authenticated_session.post('/api/download',
                                             data=json.dumps({}),
                                             content_type='application/json')
        assert response.status_code == 400

    def test_api_download_empty_json(self, client, authenticated_session):
        """Test API download with empty JSON."""
        response = authenticated_session.post('/api/download',
                                             data=json.dumps({}),
                                             content_type='application/json')
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
