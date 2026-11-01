import os
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/test")
os.environ.setdefault("AUTH_SERVICE_URL", "http://localhost:8001")


@pytest.fixture(scope="session")
def app():
    with patch('psycopg2.pool.SimpleConnectionPool', return_value=MagicMock()):
        from app import app as _app
        yield _app


@pytest.fixture
def client(app):
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def _mock_auth():
    mock_response = MagicMock()
    mock_response.status_code = 200
    return mock_response


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data == {"status": "ok"}


class TestCreateFlag:
    VALID_PAYLOAD: ClassVar[dict] = {
        "name": "new_flag",
        "description": "Test flag",
        "is_enabled": True
    }

    def test_create_flag_success(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {
            "name": "new_flag",
            "description": "Test flag",
            "is_enabled": True
        }
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.post('/flags', json=self.VALID_PAYLOAD, headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 201
            data = response.get_json()
            assert data["name"] == "new_flag"

    def test_create_flag_duplicate(self, client, app):
        import psycopg2

        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = psycopg2.IntegrityError()
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.post('/flags', json=self.VALID_PAYLOAD, headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 409


class TestGetFlags:
    def test_get_flags_success(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            {"name": "flag1", "description": "Desc 1", "is_enabled": True},
            {"name": "flag2", "description": "Desc 2", "is_enabled": False},
        ]
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.get('/flags', headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 2


class TestGetFlag:
    def test_get_flag_success(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {
            "name": "flag1",
            "description": "Desc 1",
            "is_enabled": True
        }
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.get('/flags/flag1', headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 200
            data = response.get_json()
            assert data["name"] == "flag1"

    def test_get_flag_not_found(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.get('/flags/missing', headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 404


class TestUpdateFlag:
    def test_update_flag_success(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_cur.fetchone.return_value = {
            "name": "flag1",
            "description": "Updated",
            "is_enabled": True
        }
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.put('/flags/flag1', json={"description": "Updated"}, headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 200
            data = response.get_json()
            assert data["description"] == "Updated"

    def test_update_flag_not_found(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 0
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.put('/flags/missing', json={"description": "Updated"}, headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 404


class TestDeleteFlag:
    def test_delete_flag_success(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.delete('/flags/flag1', headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 204

    def test_delete_flag_not_found(self, client, app):
        import app as app_module
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 0
        mock_conn.cursor.return_value = mock_cur

        with patch.object(app_module, 'pool') as mock_pool, \
             patch('requests.get', return_value=_mock_auth()):
            mock_pool.getconn.return_value = mock_conn
            response = client.delete('/flags/missing', headers={"Authorization": "Bearer valid-key"})
            assert response.status_code == 404
