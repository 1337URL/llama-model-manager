# Tests for llama-model-manager

This directory contains comprehensive test suites for the Flask-based llama-model-manager application.

## Test Organization

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── pytest.ini               # Pytest configuration file
├── README.md               # This file
├── run_tests.py            # Test runner script
├── test_app_module.py      # Tests for app.py module and classes
├── test_api.py             # Tests for /api/download endpoint
├── test_auth.py            # Tests for authentication (login/logout)
├── test_error_handling.py  # Tests for error handling and edge cases
├── test_integration.py     # Integration tests for user flows
├── test_fixtures.py        # Shared test fixtures and utilities
└── test_templates.py       # Tests for template rendering
```

## Running Tests

### Quick Test Run

```bash
pytest tests/ -v
```

### With Coverage Report

```bash
pytest tests/ -v --cov=app --cov-report=html
```

### Using the Test Runner Script

```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py -m auth
python tests/run_tests.py -m api
python tests/run_tests.py -m integration

# Run with coverage
python tests/run_tests.py -c
```

## Test Categories

| Category | Description | File |
|----------|-------------|------|
| Authentication | Login, logout, session management | `test_auth.py` |
| API Endpoints | `/api/download` functionality | `test_api.py` |
| Error Handling | Timeout, network errors, validation | `test_error_handling.py` |
| Integration | Complete user flows | `test_integration.py` |
| Templates | Template rendering | `test_templates.py` |
| Module | App module tests | `test_app_module.py` |

## Dependencies

Run these to install test dependencies:

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities

## Test Coverage Areas

### Authentication Tests
- Login page accessibility
- Successful login flow
- Invalid credentials handling
- Logout functionality
- Session persistence

### API Download Tests
- URL validation
- Authentication (session and token)
- Error responses
- File saving behavior

### Error Handling Tests
- Network timeouts
- HTTP errors (404, 500)
- Invalid URLs
- Directory creation
- Special characters in URLs

### Integration Tests
- Login → Download flows
- Logout and relogin
- Concurrent requests
- Session management

### Template Tests
- Login page structure
- Home page structure
- Username display
- Demo credentials display

## Writing New Tests

### Best Practices

1. Use the `client` fixture from `conftest.py` for all Flask tests
2. Mock `requests.get` calls using pytest-mock
3. Keep tests isolated and deterministic
4. Use descriptive test names following the pattern: `test_<action>_<scenario>`

### Example Test

```python
def test_api_download_success(client, authenticated_session, mocker):
    """Test successful API download."""
    # Arrange
    mock_response = mocker.Mock()
    mock_response.content = b'{"key": "value"}'
    mock_response.status_code = 200
    mock_response.headers = {'content-type': 'application/json'}
    mock_response.raise_for_status = mocker.Mock()

    # Act
    with mocker.patch('app.requests.get', return_value=mock_response):
        response = authenticated_session.post(
            '/api/download',
            data=json.dumps({'url': 'https://example.com/data.json'}),
            content_type='application/json'
        )

    # Assert
    assert response.status_code == 200
    assert response.json['success'] is True
```

## CI/CD Integration

Tests can be run in CI/CD pipelines with:

```bash
# Basic test command
pytest tests/ -v --tb=short

# With coverage threshold
pytest tests/ -v --cov=app --cov-fail-under=80
```

## Test Output

Example output:

```
tests/test_auth.py::TestAuthentication::test_login_page_get PASSED
tests/test_auth.py::TestAuthentication::test_login_success PASSED
tests/test_auth.py::TestAuthentication::test_login_wrong_password PASSED
...

=======================
18 passed, 2 warnings in 2.34s
=======================
```

## Coverage Report

Generate an HTML coverage report:

```bash
pytest tests/ --cov=app --cov-report=html
open coverage_report/index.html  # On macOS
# or
xdg-open coverage_report/index.html  # On Linux
```
