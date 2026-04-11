"""
Authentication tests for the Flask application.
Tests login, logout, and unauthorized access protection.
"""
import pytest
from app import hashed_users, VALID_USERS


class TestAuthentication:
    """Test authentication-related functionality."""

    def test_login_page_get(self, client):
        """Test that login page is accessible."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_login_success(self, client):
        """Test successful login."""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        # Should redirect to home page (302) or return success (200)
        assert response.status_code in [200, 302]

    def test_login_wrong_password(self, client):
        """Test login with wrong password."""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        })
        # Should return error message
        assert b'Invalid username or password' in response.data
        assert response.status_code == 401

    def test_login_wrong_username(self, client):
        """Test login with wrong username."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'password'
        })
        assert b'Invalid username or password' in response.data
        assert response.status_code == 401

    def test_logout(self, client):
        """Test logout endpoint."""
        # First login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        response = client.get('/logout')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_home_requires_login(self, client):
        """Test that home page requires authentication."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_home_page_display_username(self, client):
        """Test that home page displays logged-in username."""
        # Login first
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        response = client.get('/')
        assert response.status_code == 200
        assert b'admin' in response.data

    def test_logout_clears_session(self, client):
        """Test that logout clears the session."""
        # Login first
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        # Check we're authenticated
        response = client.get('/')
        assert response.status_code == 200

        # Logout
        client.get('/logout')

        # Verify we can't access home anymore
        response = client.get('/')
        assert response.status_code == 302
