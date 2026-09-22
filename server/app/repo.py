from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Expense


def create_expense(
    session: Session, *, amount_paise: int, category: str, note: str | None, spent_on: date
) -> Expense:
    expense = Expense(amount_paise=amount_paise, category=category, note=note, spent_on=spent_on)
    session.add(expense)
    session.commit()
    return expense


def has_expenses(session: Session) -> bool:
    return session.scalar(select(Expense.id).limit(1)) is not None


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


def sum_by_category(session: Session, start: date, end: date) -> dict[str, int]:
    """Paise per category for start <= spent_on < end. The bare column comparison
    lets SQLite use ix_expenses_spent_on; strftime(spent_on) would scan every row."""
    stmt = (
        select(Expense.category, func.sum(Expense.amount_paise))
        .where(Expense.spent_on >= start, Expense.spent_on < end)
        .group_by(Expense.category)
    )
    return {category: total for category, total in session.execute(stmt).tuples()}
