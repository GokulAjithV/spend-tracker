from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Expense


def create_expense(
    session: Session, *, amount_paise: int, category: str, note: str | None, spent_on: date
) -> Expense:
    expense = Expense(amount_paise=amount_paise, category=category, note=note, spent_on=spent_on)
    session.add(expense)
    session.commit()
    return expense


def list_expenses(
    session: Session,
    *,
    categories: list[str],
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> list[Expense]:
    stmt = select(Expense)
    if categories:
        stmt = stmt.where(Expense.category.in_(categories))
    if date_from is not None:
        stmt = stmt.where(Expense.spent_on >= date_from)
    if date_to is not None:
        stmt = stmt.where(Expense.spent_on <= date_to)
    # id breaks ties between same-day rows so pages never overlap or skip.
    stmt = stmt.order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt))
