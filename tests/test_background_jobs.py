"""
Tests for the background job download system.
"""
import pytest
import time
import os
from app import app, jobs


def clear_jobs():
    """Clear all jobs before each test."""
    jobs.clear()


@pytest.fixture(autouse=True)
def clear_jobs_before_test():
    """Clear jobs before each test."""
    clear_jobs()
    yield
    clear_jobs()


class TestJobCreation:
    """Test job creation and initial state."""

    def test_create_job_returns_job_id(self, authenticated_session):
        """Test that creating a job returns a job_id."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/get'})
        data = response.get_json()
        assert 'job_id' in data
        assert data['job_id'] is not None
        assert data['status'] == 'pending'
        assert 'message' in data

    def test_job_id_is_uuid_format(self, authenticated_session):
        """Test that job_id follows UUID format."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/get'})
        data = response.get_json()
        # UUIDs are 36 characters (8-4-4-4-12 format)
        assert len(data['job_id']) == 36

    def test_job_created_in_jobs_dict(self, authenticated_session):
        """Test that job is stored in jobs dictionary."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/get'})
        data = response.get_json()
        job_id = data['job_id']
        assert job_id in jobs
        assert jobs[job_id]['status'] == 'pending'
        assert jobs[job_id]['url'] == 'https://httpbin.org/get'

    def test_multiple_jobs_created_independently(self, authenticated_session):
        """Test that multiple jobs can be created independently."""
        response1 = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/get'})
        response2 = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/headers'})

        job_id1 = response1.get_json()['job_id']
        job_id2 = response2.get_json()['job_id']

        assert job_id1 != job_id2
        assert job_id1 in jobs
        assert job_id2 in jobs


class TestJobStatusPolling:
    """Test polling job status endpoint."""

    def test_get_job_status_requires_auth(self, client):
        """Test that job status endpoint requires authentication."""
        response = client.get('/api/job/test-job-id')
        assert response.status_code == 302  # Redirect to login

    def test_get_nonexistent_job(self, authenticated_session):
        """Test getting status of non-existent job returns 404."""
        response = authenticated_session.get('/api/job/nonexistent-job-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_get_job_status_pending(self, authenticated_session):
        """Test getting status of a pending job."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/delay/2'})
        job_id = response.get_json()['job_id']

        # Give the job a moment to start
        time.sleep(0.2)

        status_response = authenticated_session.get(f'/api/job/{job_id}')
        assert status_response.status_code == 200
        data = status_response.get_json()
        assert data['status'] in ['pending', 'completed', 'error']

    def test_job_status_includes_content_length(self, authenticated_session):
        """Test that job status includes content_length during download."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/bytes/1024'})
        job_id = response.get_json()['job_id']

        data = None
        # Poll until job completes or content_length is available
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if 'content_length' in data:
                break
            time.sleep(0.5)

        assert data is not None
        assert 'content_length' in data
        assert isinstance(data['content_length'], int)
        assert data['content_length'] >= 0


class TestJobCompletion:
    """Test job completion and final state."""

    def test_job_completes_successfully(self, authenticated_session):
        """Test that a job completes successfully."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/bytes/100'})
        job_id = response.get_json()['job_id']

        # Wait for job to complete
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if data['status'] == 'completed':
                break
            time.sleep(0.5)

        assert data['status'] == 'completed'
        assert 'path' in data
        assert 'filename' in data
        assert 'saved_to' in data
        assert 'content_length' in data
        assert 'status_code' in data

    def test_completed_job_has_file_saved(self, authenticated_session):
        """Test that completed job has file saved to disk."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/html'})
        job_id = response.get_json()['job_id']

        # Wait for job to complete
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if data['status'] in ['completed', 'error']:
                break
            time.sleep(0.5)

        assert data['status'] == 'completed'
        assert os.path.exists(data['path'])

    def test_job_includes_response_metadata(self, authenticated_session):
        """Test that completed job includes response metadata."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/json'})
        job_id = response.get_json()['job_id']

        # Wait for job to complete
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if data['status'] == 'completed':
                break
            time.sleep(0.5)

        assert data['status_code'] == 200
        assert data['content_type'] is not None


class TestJobErrorHandling:
    """Test job error handling."""

    def test_invalid_url_results_in_error(self, authenticated_session):
        """Test that invalid URL results in job error."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://invalid-domain-that-does-not-exist-12345.com/test'})
        job_id = response.get_json()['job_id']

        # Wait for job to fail
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if data['status'] == 'error':
                break
            time.sleep(0.5)

        assert data['status'] == 'error'
        assert 'error' in data

    def test_http_error_results_in_job_error(self, authenticated_session):
        """Test that HTTP error results in job error."""
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/status/404'})
        job_id = response.get_json()['job_id']

        # Wait for job to fail
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if data['status'] == 'error':
                break
            time.sleep(0.5)

        assert data['status'] == 'error'
        assert 'error' in data


class TestJobProgress:
    """Test job progress tracking."""

    def test_content_length_increases_during_download(self, authenticated_session):
        """Test that content_length increases during download."""
        # Use a larger file to see progress
        response = authenticated_session.post('/api/download',
            json={'url': 'https://httpbin.org/bytes/10240'})
        job_id = response.get_json()['job_id']

        sizes = []
        for _ in range(10):
            status_response = authenticated_session.get(f'/api/job/{job_id}')
            data = status_response.get_json()
            if 'content_length' in data:
                sizes.append(data['content_length'])
            if data['status'] == 'completed':
                break
            time.sleep(0.2)

        # Should have seen some progress
        assert len(sizes) > 0
        if len(sizes) > 1:
            # Size should be non-decreasing
            assert sizes == sorted(sizes)
