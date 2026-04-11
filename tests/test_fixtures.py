"""
Shared test fixtures and utilities for the llama-model-manager tests.
"""
import pytest
import json
from unittest.mock import MagicMock


"""
Shared test fixtures and utilities for the llama-model-manager tests.

These fixtures should be moved to conftest.py for better pytest integration.
"""
from unittest.mock import MagicMock
import json


def create_mock_response(content, status_code=200, content_type='application/json'):
    """
    Create a mock response object for testing.

    Args:
        content: The response body as bytes or string
        status_code: HTTP status code (default: 200)
        content_type: Content type header (default: application/json)

    Returns:
        A MagicMock configured with response properties
    """
    mock = MagicMock()
    mock.content = content if isinstance(content, bytes) else content.encode()
    mock.status_code = status_code
    mock.headers = {
        'content-type': content_type,
        'content-length': str(len(content))
    } if content else {}
    mock.raise_for_status = lambda: None
    mock.text = content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
    mock.json = lambda: json.loads(mock.text) if mock.headers.get('content-type', '').startswith('application/json') else None
    return mock


# Helper function to create a mock raise_for_status that raises an exception
def create_error_mock(status_code, error_message='Error'):
    """
    Create a mock response that raises an exception on raise_for_status().

    Args:
        status_code: HTTP status code
        error_message: Error message for the exception

    Returns:
        A MagicMock with raise_for_status that raises an exception
    """
    mock = MagicMock()
    mock.content = f'{status_code} {error_message}'.encode()
    mock.status_code = status_code
    mock.headers = {'content-type': 'text/plain'}
    mock.raise_for_status = lambda: (_ for _ in ()).throw(Exception(f'{status_code} {error_message}'))
    return mock


def create_redirect_mock(location='https://new-location.com'):
    """
    Create a mock response for a redirect.

    Args:
        location: The redirect location URL

    Returns:
        A MagicMock configured as a redirect response
    """
    mock = MagicMock()
    mock.content = b''
    mock.status_code = 302
    mock.headers = {'location': location}
    mock.raise_for_status = lambda: None
    return mock


def create_empty_response(status_code=204):
    """
    Create a mock response with no content.

    Args:
        status_code: HTTP status code (default: 204 No Content)

    Returns:
        A MagicMock configured as an empty response
    """
    mock = MagicMock()
    mock.content = b''
    mock.status_code = status_code
    mock.headers = {}
    mock.raise_for_status = lambda: None
    return mock


class MockRequestsGet:
    """
    Context manager for mocking requests.get calls.

    Usage:
        with MockRequestsGet() as mock:
            mock.configure(return_value=mock_response)
            response = client.get('/download?url=...')
            assert mock.call_count == 1
    """

    def __init__(self):
        self.call_count = 0
        self.call_args_list = []

    def configure(self, **kwargs):
        """Configure the mock with new parameters."""
        self.return_value = kwargs.pop('return_value', None)
        self.side_effect = kwargs.pop('side_effect', None)
        self.kwargs = kwargs

    def __call__(self, **kwargs):
        self.call_count += 1
        self.call_args_list.append(kwargs)
        return self.return_value or MagicMock()


@pytest.fixture
def mock_requests():
    """
    Fixture to create a mock for requests.get calls.
    """
    mock = MockRequestsGet()
    return mock


class TestUtilityFunctions:
    """
    Test utility functions for validating test behavior.
    """

    @staticmethod
    def validate_download_response(response, success=True):
        """
        Validate a download API response.

        Args:
            response: The API response object
            success: Whether the download should have succeeded

        Returns:
            True if validation passes
        """
        if response.status_code != 200 and success:
            return False
        if response.status_code == 200 and response.json.get('success'):
            return True
        return None

    @staticmethod
    def validate_auth_response(response, expected_status=401):
        """
        Validate authentication-related responses.

        Args:
            response: The API response object
            expected_status: Expected status code (401 for auth failure)

        Returns:
            True if validation passes
        """
        if response.status_code == expected_status:
            response_text = response.data.decode('utf-8', errors='ignore').lower()
            if 'invalid' in response_text or 'unauthenticated' in response_text:
                return True
        return None

    @staticmethod
    def assert_json_structure(response, expected_keys):
        """
        Assert that response JSON contains expected keys.

        Args:
            response: API response object
            expected_keys: Set of expected keys in JSON

        Raises:
            AssertionError: If response is not JSON or missing keys
        """
        if response.status_code != 200:
            return
        try:
            data = response.json()
            for key in expected_keys:
                assert key in data, f"Missing key: {key}"
        except:
            raise AssertionError("Response is not valid JSON")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
