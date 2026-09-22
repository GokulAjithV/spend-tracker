import re
from datetime import date, datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, model_validator

from app.models import Expense

# Up to 15 rupee digits keeps the largest value (~10^17 paise) inside SQLite's
# signed 64-bit INTEGER; anything longer would overflow at insert time and
# surface as a 500 instead of a 422.
_AMOUNT_RE = re.compile(r"\d{1,15}(\.\d{1,2})?")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_amount(value: Any) -> int:
    """"250.5" -> 25050. Only strings are accepted: a JSON number would already
    have been parsed into a float, and the precision may be gone by then."""
    if not isinstance(value, str) or not _AMOUNT_RE.fullmatch(value):
        raise ValueError("amount must be a string like '250' or '250.50', with at most 2 decimals")
    rupees, _, fraction = value.partition(".")
    paise = int(rupees) * 100 + int(fraction.ljust(2, "0"))
    if paise <= 0:
        raise ValueError("amount must be greater than 0")
    return paise


def _parse_date(value: Any) -> date:
    """Exactly YYYY-MM-DD. The regex comes first because date.fromisoformat
    also accepts forms like '20260921' and '2026-W38-1'."""
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError("date must be a string in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("date is not a valid calendar date") from None


def format_paise(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


Category = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=50)
]
IsoDate = Annotated[date, BeforeValidator(_parse_date)]


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Sent as "amount", held as paise so nothing downstream can mistake the unit.
    amount_paise: Annotated[int, BeforeValidator(_parse_amount)] = Field(alias="amount")
    category: Category
    note: str | None = Field(default=None, max_length=500)
    spent_on: IsoDate


class ExpenseOut(BaseModel):
    id: str
    amount: str
    category: str
    note: str | None
    spent_on: date
    created_at: datetime

    @classmethod
    def from_model(cls, expense: Expense) -> "ExpenseOut":
        return cls(
            id=expense.id,
            amount=format_paise(expense.amount_paise),
            category=expense.category,
            note=expense.note,
            spent_on=expense.spent_on,
            # Stored as naive UTC (see models._utcnow); re-attach the zone so the
            # API emits "...Z" and clients don't read it as their local time.
            created_at=expense.created_at.replace(tzinfo=timezone.utc),
        )


class ExpenseList(BaseModel):
    expenses: list[ExpenseOut]


class ExpenseFilters(BaseModel):
    """Query string for GET /expenses. Unknown params are rejected so a typo
    like ?categroy=food fails loudly instead of silently returning everything."""

    model_config = ConfigDict(extra="forbid")

    # Normalised like ExpenseCreate.category, so ?category=Food matches stored "food".
    category: list[Category] = []
    date_from: IsoDate | None = None
    date_to: IsoDate | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check_range(self) -> "ExpenseFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self
