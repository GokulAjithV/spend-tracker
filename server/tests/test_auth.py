import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import API_KEY

PROTECTED = [
    ("POST", "/expenses"),
    ("GET", "/expenses"),
    ("GET", "/summary"),
]


def assert_unauthorized(res) -> None:
    assert res.status_code == 401
    assert res.json() == {"detail": "Invalid or missing API key"}
    assert res.headers["WWW-Authenticate"] == "APIKey"


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_missing_key_rejected(client: TestClient, method, path):
    del client.headers["X-API-Key"]
    assert_unauthorized(client.request(method, path))


@pytest.mark.parametrize(("method", "path"), PROTECTED)
# b"\xc3\xa9" is UTF-8 "é" as raw bytes; the server decodes it to non-ASCII text,
# which secrets.compare_digest rejects with TypeError if compared as str.
@pytest.mark.parametrize("key", ["wrong", "", API_KEY + "x", API_KEY.upper(), b"\xc3\xa9"])
def test_wrong_key_rejected(client: TestClient, method, path, key):
    assert_unauthorized(client.request(method, path, headers={"X-API-Key": key}))


def test_auth_runs_before_validation(client: TestClient):
    # An unauthenticated caller learns nothing about the request format.
    res = client.post("/expenses", json={"amount": 5}, headers={"X-API-Key": "wrong"})
    assert_unauthorized(res)


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_correct_key_accepted(client: TestClient, method, path):
    body = {"amount": "1.00", "category": "food", "spent_on": "2026-09-01"}
    res = client.request(method, path, json=body if method == "POST" else None)
    assert res.status_code in (200, 201)


def test_health_is_open(client: TestClient):
    del client.headers["X-API-Key"]
    assert client.get("/health").status_code == 200


def test_openapi_declares_api_key_scheme(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"] == {
        "APIKeyHeader": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    }
    assert "security" not in schema["paths"]["/health"]["get"]
    assert schema["paths"]["/summary"]["get"]["security"] == [{"APIKeyHeader": []}]


@pytest.mark.parametrize("value", [None, "", "   "])
def test_startup_fails_without_key(monkeypatch: pytest.MonkeyPatch, value):
    if value is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", value)
    with pytest.raises((KeyError, RuntimeError)):
        with TestClient(app):
            pass
