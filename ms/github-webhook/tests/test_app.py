import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GH_PAT", "test-token")
os.environ.setdefault("GH_REPO", "test/repo")


@pytest.fixture
def app():
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        from app import app as _app
        yield _app


@pytest.fixture
def client(app):
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data == {"status": "ok"}


class TestWebhook:
    def test_webhook_ignores_non_firing(self, client):
        response = client.post('/webhook', json={"status": "resolved"})
        assert response.status_code == 200
        data = response.get_json()
        assert data == {"ignored": True, "status": "resolved"}

    def test_webhook_dispatches_on_firing(self, client):
        payload = {
            "status": "firing",
            "commonLabels": {
                "service": "auth-service",
                "namespace": "application",
                "alertname": "High5xxErrorRate"
            },
            "commonAnnotations": {
                "summary": "Summary text",
                "description": "Description text"
            }
        }
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.text = ""
            mock_post.return_value = mock_response

            response = client.post('/webhook', json=payload)
            assert response.status_code == 200
            data = response.get_json()
            assert data["dispatched"] is True
            assert data["github_status"] == 204

            kwargs = mock_post.call_args.kwargs
            assert "dispatches" in mock_post.call_args.args[0]
            assert kwargs["headers"]["Authorization"] == "Bearer test-token"
            body = kwargs["json"]
            assert body["client_payload"]["service"] == "auth-service"
            assert body["client_payload"]["alertname"] == "High5xxErrorRate"

    def test_webhook_dispatch_failure(self, client):
        payload = {
            "status": "firing",
            "commonLabels": {"service": "auth-service", "alertname": "TestAlert"},
            "commonAnnotations": {}
        }
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            response = client.post('/webhook', json=payload)
            assert response.status_code == 500
            data = response.get_json()
            assert data["dispatched"] is False
            assert data["github_status"] == 500

    def test_webhook_dispatch_request_exception(self, client):
        import requests
        payload = {
            "status": "firing",
            "commonLabels": {"service": "auth-service", "alertname": "TestAlert"},
            "commonAnnotations": {}
        }
        with patch('requests.post', side_effect=requests.RequestException("Connection error")):
            response = client.post('/webhook', json=payload)
            assert response.status_code == 502
            data = response.get_json()
            assert data["dispatched"] is False
            assert "Connection error" in data["error"]

    def test_webhook_defaults_when_labels_missing(self, client):
        payload = {"status": "firing"}
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.text = ""
            mock_post.return_value = mock_response

            response = client.post('/webhook', json=payload)
            assert response.status_code == 200
            kwargs = mock_post.call_args.kwargs
            body = kwargs["json"]
            assert body["client_payload"]["service"] == "auth-service"
            assert body["client_payload"]["namespace"] == "application"
            assert body["client_payload"]["alertname"] == "High5xxErrorRate"