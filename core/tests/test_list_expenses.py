from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Expense


def seed(session_factory: sessionmaker[Session], *rows: tuple[str, str, str]) -> None:
    """rows: (id, category, spent_on). Explicit ids make the tiebreak predictable."""
    with session_factory() as session:
        session.add_all(
            Expense(id=id_, amount_paise=100, category=cat, spent_on=date.fromisoformat(day))
            for id_, cat, day in rows
        )
        session.commit()


def ids(client: TestClient, params=None) -> list[str]:
    res = client.get("/expenses", params=params)
    assert res.status_code == 200, res.text
    return [e["id"] for e in res.json()["expenses"]]


@pytest.fixture
def seeded(session_factory: sessionmaker[Session]) -> None:
    seed(
        session_factory,
        ("a", "food", "2026-09-01"),
        ("b", "travel", "2026-09-05"),
        ("c", "food", "2026-09-10"),
        ("d", "medicine", "2026-09-10"),
        ("e", "food", "2026-09-20"),
    )


def test_empty_database(client: TestClient):
    assert client.get("/expenses").json() == {"expenses": []}


def test_item_shape_matches_create_response(client: TestClient):
    created = client.post(
        "/expenses", json={"amount": "250.50", "category": "Food", "spent_on": "2026-09-21"}
    ).json()
    assert client.get("/expenses").json() == {"expenses": [created]}


@pytest.mark.usefixtures("seeded")
def test_orders_by_spent_on_desc_then_id_desc(client: TestClient):
    # c and d share 2026-09-10: id DESC puts d first.
    assert ids(client) == ["e", "d", "c", "b", "a"]


@pytest.mark.usefixtures("seeded")
def test_single_category(client: TestClient):
    assert ids(client, {"category": "food"}) == ["e", "c", "a"]


@pytest.mark.usefixtures("seeded")
def test_repeated_category(client: TestClient):
    assert ids(client, [("category", "travel"), ("category", "medicine")]) == ["d", "b"]


@pytest.mark.usefixtures("seeded")
def test_category_is_normalised(client: TestClient):
    assert ids(client, {"category": "  FOOD "}) == ["e", "c", "a"]


@pytest.mark.usefixtures("seeded")
def test_unknown_category_returns_empty(client: TestClient):
    assert ids(client, {"category": "rent"}) == []


@pytest.mark.usefixtures("seeded")
def test_date_range_is_inclusive(client: TestClient):
    assert ids(client, {"date_from": "2026-09-05", "date_to": "2026-09-10"}) == ["d", "c", "b"]


@pytest.mark.usefixtures("seeded")
def test_single_day_range(client: TestClient):
    assert ids(client, {"date_from": "2026-09-10", "date_to": "2026-09-10"}) == ["d", "c"]


@pytest.mark.usefixtures("seeded")
def test_open_ended_ranges(client: TestClient):
    assert ids(client, {"date_from": "2026-09-10"}) == ["e", "d", "c"]
    assert ids(client, {"date_to": "2026-09-05"}) == ["b", "a"]


@pytest.mark.usefixtures("seeded")
def test_category_and_date_combined(client: TestClient):
    assert ids(client, {"category": "food", "date_from": "2026-09-05"}) == ["e", "c"]


@pytest.mark.usefixtures("seeded")
def test_limit_and_offset(client: TestClient):
    assert ids(client, {"limit": 2}) == ["e", "d"]
    assert ids(client, {"limit": 2, "offset": 2}) == ["c", "b"]
    assert ids(client, {"limit": 2, "offset": 4}) == ["a"]
    assert ids(client, {"offset": 10}) == []


@pytest.mark.usefixtures("seeded")
def test_pages_cover_everything_exactly_once(client: TestClient):
    pages = [ids(client, {"limit": 2, "offset": o}) for o in (0, 2, 4)]
    assert [i for page in pages for i in page] == ids(client)


def test_date_from_after_date_to_rejected(client: TestClient):
    res = client.get("/expenses", params={"date_from": "2026-09-11", "date_to": "2026-09-10"})
    assert res.status_code == 422
    assert "date_from must be on or before date_to" in res.text


@pytest.mark.parametrize(
    "params",
    [
        {"date_from": "10-09-2026"},
        {"date_to": "20260910"},
        {"date_from": "2026-02-30"},
        {"category": ""},
        {"category": "x" * 51},
        {"limit": 0},
        {"limit": 101},
        {"limit": "abc"},
        {"offset": -1},
        {"categroy": "food"},  # typo: unknown params are rejected, not ignored
    ],
)
def test_invalid_params_rejected(client: TestClient, params):
    assert client.get("/expenses", params=params).status_code == 422


def test_default_limit_is_50(client: TestClient, session_factory: sessionmaker[Session]):
    seed(session_factory, *((f"id{i:03d}", "food", "2026-09-01") for i in range(60)))
    assert len(ids(client)) == 50
    assert len(ids(client, {"limit": 100})) == 60
