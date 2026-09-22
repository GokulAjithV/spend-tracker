from datetime import date

from sqlalchemy.orm import Session

from app.models import Expense


def create_expense(
    session: Session, *, amount_paise: int, category: str, note: str | None, spent_on: date
) -> Expense:
    expense = Expense(amount_paise=amount_paise, category=category, note=note, spent_on=spent_on)
    session.add(expense)
    session.commit()
    return expense
