from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import repo
from app.models import Expense
from app.seed import seed_if_empty
from app.summary import build_summary, month_range, previous_month

TODAY = date(2026, 9, 22)


def count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Expense)) or 0


def test_empty_db_is_seeded(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        inserted = seed_if_empty(session, TODAY)
        assert inserted == count(session)
        assert 18 <= inserted <= 22


def test_existing_data_is_left_alone(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        repo.create_expense(
            session, amount_paise=100, category="food", note=None, spent_on=TODAY
        )
        assert seed_if_empty(session, TODAY) == 0
        assert count(session) == 1


def test_seeding_twice_does_not_duplicate(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        first = seed_if_empty(session, TODAY)
        assert seed_if_empty(session, TODAY) == 0
        assert count(session) == first


@pytest.mark.parametrize(
    "today",
    [
        date(2026, 9, 1),   # first of the month: every current row lands on the 1st
        date(2026, 1, 1),   # previous month is last year's December
        date(2026, 3, 1),   # previous month is a 28-day February
        date(2026, 9, 22),
        date(2026, 10, 31),
    ],
)
def test_dates_stay_in_range(session_factory: sessionmaker[Session], today: date):
    this_month = today.replace(day=1)
    prev_start, _ = month_range(*_ym(previous_month(this_month)))
    with session_factory() as session:
        seed_if_empty(session, today)
        dates = session.scalars(select(Expense.spent_on)).all()

    assert all(prev_start <= d <= today for d in dates)
    assert any(d < this_month for d in dates)
    assert any(d >= this_month for d in dates)
    if today.day == 1:
        assert all(d == today for d in dates if d >= this_month)


def test_seed_produces_the_documented_summary(session_factory: sessionmaker[Session]):
    this_month = TODAY.replace(day=1)
    with session_factory() as session:
        seed_if_empty(session, TODAY)
        current = repo.sum_by_category(session, *month_range(*_ym(this_month)))
        previous = repo.sum_by_category(
            session, *month_range(*_ym(previous_month(this_month)))
        )

    summary = build_summary(this_month, current, previous, TODAY)
    rows = {
        c.category: (c.total, c.previous_total, c.change_percent, c.flagged)
        for c in summary.by_category
    }
    assert rows == {
        "food": ("5200.00", "5000.00", 4.0, False),
        "travel": ("4100.00", "3000.00", 36.67, True),
        "medicine": ("800.00", "0.00", None, False),
        "shopping": ("0.00", "2000.00", -100.0, False),
    }
    assert summary.total == "10100.00"
    assert summary.previous_month.total == "10000.00"


def _ym(month: date) -> tuple[int, int]:
    return month.year, month.month
