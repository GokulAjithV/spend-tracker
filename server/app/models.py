from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    """Naive UTC. SQLite cannot store an offset, so an aware value would come
    back stripped of its tzinfo and be silently misread as local time."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_expenses_amount_paise_positive"),
        Index("ix_expenses_spent_on", "spent_on"),
        Index("ix_expenses_category_spent_on", "category", "spent_on"),
    )

    def __repr__(self) -> str:
        return (
            f"Expense(id={self.id!r}, amount_paise={self.amount_paise!r}, "
            f"category={self.category!r}, spent_on={self.spent_on!r})"
        )
