from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Expense

VALID = {"amount": "250.50", "category": "Food", "note": "lunch", "spent_on": "2026-09-21"}


def post(client: TestClient, **overrides):
    return client.post("/expenses", json={**VALID, **overrides})


def test_create_returns_201_with_full_expense(client: TestClient):
    res = post(client, category="  Food  ")

    assert res.status_code == 201
    body = res.json()
    assert set(body) == {"id", "amount", "category", "note", "spent_on", "created_at"}
    assert body["amount"] == "250.50"
    assert body["category"] == "food"
    assert body["note"] == "lunch"
    assert body["spent_on"] == "2026-09-21"
    assert body["created_at"].endswith("Z")
    datetime.fromisoformat(body["created_at"])


def test_create_persists_paise(client: TestClient, session_factory: sessionmaker[Session]):
    res = post(client)

    with session_factory() as session:
        row = session.scalars(select(Expense)).one()
    assert row.id == res.json()["id"]
    assert row.amount_paise == 25050
    assert row.category == "food"


@pytest.mark.parametrize(
    ("amount", "paise", "echoed"),
    [
        ("250", 25000, "250.00"),
        ("250.5", 25050, "250.50"),
        ("0.01", 1, "0.01"),
        ("0.10", 10, "0.10"),
        ("999999999999999.99", 99999999999999999, "999999999999999.99"),
    ],
)
def test_amount_conversion(
    client: TestClient, session_factory: sessionmaker[Session], amount, paise, echoed
):
    res = post(client, amount=amount)

    assert res.status_code == 201
    assert res.json()["amount"] == echoed
    with session_factory() as session:
        assert session.scalars(select(Expense.amount_paise)).one() == paise


@pytest.mark.parametrize(
    "amount",
    [
        "0", "0.00", "-5", "1.234", "1.", ".5", "abc", "", " 5", "1e3", "1,000",
        "1234567890123456",  # 16 rupee digits: would overflow SQLite INTEGER
        250.5, 250, True, None,  # non-strings: floats may already have lost precision
    ],
)
def test_invalid_amount_rejected(client: TestClient, amount):
    assert post(client, amount=amount).status_code == 422


@pytest.mark.parametrize("category", ["", "   ", "x" * 51, None, 5])
def test_invalid_category_rejected(client: TestClient, category):
    assert post(client, category=category).status_code == 422


def test_category_length_counted_after_trim(client: TestClient):
    res = post(client, category="  " + "X" * 50 + "  ")
    assert res.status_code == 201
    assert res.json()["category"] == "x" * 50


def test_note_is_optional(client: TestClient):
    body = {k: v for k, v in VALID.items() if k != "note"}
    res = client.post("/expenses", json=body)
    assert res.status_code == 201
    assert res.json()["note"] is None


def test_note_max_length(client: TestClient):
    assert post(client, note="n" * 500).status_code == 201
    assert post(client, note="n" * 501).status_code == 422


@pytest.mark.parametrize(
    "spent_on",
    ["21-09-2026", "2026/09/21", "20260921", "2026-W38-1", "2026-02-30", "2026-9-21",
     "2026-09-21T00:00:00", "", None, 1758412800],
)
def test_invalid_date_rejected(client: TestClient, spent_on):
    assert post(client, spent_on=spent_on).status_code == 422


@pytest.mark.parametrize("missing", ["amount", "category", "spent_on"])
def test_required_fields(client: TestClient, missing):
    body = {k: v for k, v in VALID.items() if k != missing}
    assert client.post("/expenses", json=body).status_code == 422


@pytest.mark.parametrize("extra", [{"id": "x"}, {"amount_paise": 100}, {"created_at": "2026-01-01"}])
def test_extra_fields_rejected(client: TestClient, extra):
    assert post(client, **extra).status_code == 422


def test_rejected_request_writes_nothing(client: TestClient, session_factory: sessionmaker[Session]):
    post(client, amount="0")
    with session_factory() as session:
        assert session.scalars(select(Expense)).all() == []
