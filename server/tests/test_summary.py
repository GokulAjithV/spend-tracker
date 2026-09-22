from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.summary import build_summary, month_range, previous_month

SEP = date(2026, 9, 1)
TODAY = date(2026, 9, 22)


def by_category(summary) -> dict:
    return {c.category: c for c in summary.by_category}

# API: empty database, validation

def test_empty_db_returns_zero_totals_and_null_percent(client: TestClient):
    res = client.get("/summary", params={"month": "2026-09"})

    assert res.status_code == 200
    body = res.json()
    body.pop("is_partial_month")  # depends on the real clock
    assert body == {
        "month": "2026-09",
        "total": "0.00",
        "previous_month": {"month": "2026-08", "total": "0.00"},
        "mom_change": {"amount": "0.00", "percent": None},
        "by_category": [],
    }


@pytest.mark.parametrize("month", ["2026-13", "2026-00", "abc", "2026-9", "2026-09-01"])
def test_invalid_month_rejected(client: TestClient, month):
    assert client.get("/summary", params={"month": month}).status_code == 422


def test_paise_sum_stays_exact(client: TestClient):
    # 0.1 + 0.2 == 0.30000000000000004 in floats. Going through the API covers
    # every step that could introduce one: parsing, SQL SUM, formatting.
    for amount in ("0.10", "0.20"):
        res = client.post(
            "/expenses", json={"amount": amount, "category": "food", "spent_on": "2026-09-05"}
        )
        assert res.status_code == 201

    body = client.get("/summary", params={"month": "2026-09"}).json()

    assert body["total"] == "0.30"
    assert body["by_category"][0]["total"] == "0.30"


# build_summary

def test_previous_month_zero_gives_null_percent():
    summary = build_summary(SEP, {"food": 50000}, {}, TODAY)

    assert summary.mom_change.amount == "500.00"
    assert summary.mom_change.percent is None
    food = by_category(summary)["food"]
    assert food.change_percent is None
    assert food.flagged is False


def test_spend_dropped_gives_negative_change():
    summary = build_summary(SEP, {"food": 75000}, {"food": 100000}, TODAY)

    assert summary.mom_change.amount == "-250.00"
    assert summary.mom_change.percent == -25.0
    assert by_category(summary)["food"].change_percent == -25.0


@pytest.mark.parametrize(
    ("current", "percent", "flagged"),
    [
        (12000, 20.0, False),  # exactly +20%: the rule is strictly greater
        (12001, 20.01, True),
    ],
)
def test_flag_threshold(current, percent, flagged):
    food = by_category(build_summary(SEP, {"food": current}, {"food": 10000}, TODAY))["food"]

    assert food.change_percent == percent
    assert food.flagged is flagged


def test_category_only_in_previous_month_shows_zero():
    summary = build_summary(SEP, {"food": 10000}, {"food": 10000, "gifts": 5000}, TODAY)

    gifts = by_category(summary)["gifts"]
    assert gifts.total == "0.00"
    assert gifts.previous_total == "50.00"
    assert gifts.change_percent == -100.0
    assert gifts.flagged is False


def test_january_compares_with_previous_december():
    # The dates the route passes to the repo for the "previous" query.
    prev = previous_month(date(2026, 1, 1))
    assert month_range(prev.year, prev.month) == (date(2025, 12, 1), date(2026, 1, 1))

    summary = build_summary(date(2026, 1, 1), {}, {}, TODAY)

    assert summary.month == "2026-01"
    assert summary.previous_month.month == "2025-12"
