from fastapi.testclient import TestClient
from sqlalchemy import Table
from typing import cast

from app.main import app
from app.models import Expense


def test_health(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_expense_table_shape():
    table = cast(Table, Expense.__table__)
    cols = table.columns
    assert cols["amount_paise"].nullable is False
    assert cols["note"].nullable is True
    assert {i.name for i in table.indexes} == {
        "ix_expenses_spent_on",
        "ix_expenses_category_spent_on",
    }


def test_ui_is_served_without_api_key(client: TestClient):
    del client.headers["X-API-Key"]
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "<title>Spend Tracker</title>" in res.text
