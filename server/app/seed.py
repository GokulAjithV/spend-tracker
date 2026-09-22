"""Demo data, placed relative to `today` so the summary always has a current
and a previous month to compare."""

from datetime import date

from sqlalchemy.orm import Session

from app import repo
from app.schemas import ExpenseCreate
from app.summary import previous_month

# (month, day, amount, category, note). "prev" days stay <= 28 so they exist in
# every month; "cur" days are clamped to today when the month is still young.
#
# Totals, previous -> current:
#   food      5000.00 -> 5200.00   +4.00%, not flagged
#   travel    3000.00 -> 4100.00   +36.67%, flagged
#   shopping  2000.00 -> none      -100%
#   medicine  none    -> 800.00    new, percent null
_ROWS: list[tuple[str, int, str, str, str | None]] = [
    ("prev", 2, "1249.50", "food", "Monthly groceries"),
    ("prev", 9, "1800.25", "food", "Dinner with friends"),
    ("prev", 16, "1450.75", "food", None),
    ("prev", 25, "499.50", "food", "Snacks"),
    ("prev", 5, "1850.00", "travel", "Train tickets"),
    ("prev", 12, "749.50", "travel", "Cab to airport"),
    ("prev", 19, "250.25", "travel", None),
    ("prev", 27, "150.25", "travel", "Metro card top-up"),
    ("prev", 7, "1299.99", "shopping", "Shoes"),
    ("prev", 21, "700.01", "shopping", None),
    ("cur", 1, "1520.25", "food", "Monthly groceries"),
    ("cur", 4, "1379.75", "food", None),
    ("cur", 8, "1650.50", "food", "Birthday dinner"),
    ("cur", 12, "649.50", "food", "Snacks"),
    ("cur", 2, "2250.00", "travel", "Flight tickets"),
    ("cur", 6, "1249.25", "travel", "Hotel"),
    ("cur", 10, "600.75", "travel", None),
    ("cur", 3, "249.50", "medicine", "Pharmacy"),
    ("cur", 5, "350.25", "medicine", "Doctor visit"),
    ("cur", 9, "200.25", "medicine", None),
]


def _expenses(today: date) -> list[ExpenseCreate]:
    this_month = today.replace(day=1)
    last_month = previous_month(this_month)
    expenses = []
    for month, day, amount, category, note in _ROWS:
        if month == "prev":
            spent_on = last_month.replace(day=day)
        else:
            spent_on = this_month.replace(day=min(day, today.day))
        # Built from the same JSON-shaped input a client sends, so every row goes
        # through the API's amount/category/date validation.
        expenses.append(
            ExpenseCreate.model_validate(
                {"amount": amount, "category": category, "note": note,
                 "spent_on": spent_on.isoformat()}
            )
        )
    return expenses


def seed_if_empty(session: Session, today: date) -> int:
    """Insert the demo rows unless any expense exists. Returns rows inserted."""
    if repo.has_expenses(session):
        return 0
    # Validate everything before the first insert, so a bad row can't leave a
    # half-seeded table that later runs would treat as "not empty".
    expenses = _expenses(today)
    for expense in expenses:
        repo.create_expense(session, **expense.model_dump())
    return len(expenses)
