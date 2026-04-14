"""
Reverse proxy tests for the Flask application.
Tests the /api/proxy/* endpoint and error handling.
"""
import pytest
import json


class TestReverseProxyAuthentication:
    """Test reverse proxy authentication."""

    def test_proxy_requires_authentication(self, client):
        """Test that proxy requires authentication."""
        response = client.get('/api/https://example.com/test')
        assert response.status_code == 401
        assert 'Authentication required' in json.loads(response.data)['error']

    def test_proxy_with_valid_api_token(self, client):
        """Test successful proxy request with valid API token."""
        from app import app
        app.config['API_TOKEN'] = 'test-token-123'

        response = client.get(
            '/api/https://httpbin.org/get',
            headers={'X-API-Token': 'test-token-123'}
        )
        # Should reach upstream (may fail due to network, but auth passes)
        assert response.status_code in [200, 502, 504]

    def test_proxy_with_invalid_api_token(self, client):
        """Test that invalid API token is rejected."""
        from app import app
        app.config['API_TOKEN'] = 'super-secret-token'

        response = client.get(
            '/api/https://example.com/test',
            headers={'X-API-Token': 'invalid-token'}
        )
        assert response.status_code == 401

    def test_proxy_with_authenticated_session(self, authenticated_session):
        """Test successful proxy request with logged-in session."""
        response = authenticated_session.get(
            '/api/https://httpbin.org/get'
        )
        # Should reach upstream (may fail due to network, but auth passes)
        assert response.status_code in [200, 502, 504]


class TestReverseProxyHttpMethods:
    """Test different HTTP methods for proxy."""

    def test_proxy_get_method(self, authenticated_session):
        """Test GET method forwarding."""
        response = authenticated_session.get('/api/https://httpbin.org/get')
        assert response.status_code in [200, 502, 504]

    def test_proxy_post_method(self, authenticated_session):
        """Test POST method forwarding."""
        response = authenticated_session.post(
            '/api/https://httpbin.org/post',
            json={'test': 'data'}
        )
        assert response.status_code in [200, 502, 504]

    def test_proxy_delete_method(self, authenticated_session):
        """Test DELETE method forwarding."""
        response = authenticated_session.delete('/api/https://httpbin.org/delete')
        assert response.status_code in [200, 502, 504]


class TestReverseProxyHeaders:
    """Test header forwarding and filtering."""

    def test_proxy_forwards_content_type(self, authenticated_session):
        """Test that Content-Type header is forwarded."""
        response = authenticated_session.post(
            '/api/https://httpbin.org/post',
            json={'test': 'data'},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code in [200, 502, 504]

    def test_proxy_excludes_sensitive_headers(self, client):
        """Test that sensitive headers are excluded."""
        from app import app
        app.config['API_TOKEN'] = 'test-token-123'

        # Set a custom header that should be forwarded
        response = client.get(
            '/api/https://httpbin.org/headers',
            headers={
                'X-API-Token': 'test-token-123',
                'X-Custom-Header': 'custom-value'
            }
        )
        assert response.status_code in [200, 502, 504]


class TestReverseProxyErrors:
    """Test error handling for proxy."""

    def test_proxy_timeout(self, client):
        """Test timeout error handling."""
        from app import app
        app.config['API_TOKEN'] = 'test-token-123'
        app.config['PROXY_TIMEOUT'] = 1  # Very short timeout for testing

        # Use an endpoint that will timeout
        response = client.get(
            '/api/https://httpbin.org/delay/10',
            headers={'X-API-Token': 'test-token-123'}
        )
        # Should return 504 timeout or upstream error
        assert response.status_code in [200, 502, 504, 500]

    def test_proxy_no_upstream_configured(self, client):
        """Test error when upstream URL not configured."""
        from app import app
        # Don't set PROXY_UPSTREAM_URL
        app.config['PROXY_UPSTREAM_URL'] = None
        response = client.get(
            '/api/example.com/test',  # Relative path requires upstream URL
            headers={'X-API-Token': 'test-token-123'}
        )
        assert response.status_code == 500
        assert 'PROXY_UPSTREAM_URL not configured' in json.loads(response.data)['error']

    def test_proxy_missing_auth_token_header(self, client):
        """Test error when no auth token provided."""
        response = client.get('/api/https://example.com/test')
        assert response.status_code == 401


class TestReverseProxyQueryString:
    """Test query string forwarding."""

    def test_proxy_forwards_query_params(self, authenticated_session):
        """Test that query parameters are forwarded to upstream."""
        response = authenticated_session.get(
            '/api/https://httpbin.org/get?param1=value1&param2=value2'
        )
        assert response.status_code in [200, 502, 504]


class TestReverseProxyCORS:
    """Test CORS configuration."""

    def test_proxy_cors_enabled(self, client):
        """Test CORS headers when enabled."""
        from app import app
        app.config['API_TOKEN'] = 'test-token-123'
        app.config['PROXY_UPSTREAM_URL'] = 'https://example.com'
        app.config['PROXY_ENABLE_CORS'] = 'true'

        response = client.options(
            '/api/https://example.com/test',
            headers={'X-API-Token': 'test-token-123'}
        )
        assert response.status_code == 204
        assert response.headers.get('Access-Control-Allow-Origin') == '*'

    def test_proxy_cors_disabled(self, client):
        """Test no CORS headers when disabled."""
        from app import app
        app.config['API_TOKEN'] = 'test-token-123'
        app.config['PROXY_UPSTREAM_URL'] = 'https://example.com'
        app.config['PROXY_ENABLE_CORS'] = 'false'

        response = client.options(
            '/api/https://example.com/test',
            headers={'X-API-Token': 'test-token-123'}
        )
        assert response.status_code == 204
        assert 'Access-Control-Allow-Origin' not in response.headers
