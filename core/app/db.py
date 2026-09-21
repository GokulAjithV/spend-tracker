import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./spend_tracker.db")

# check_same_thread=False: sqlite3 defaults to rejecting any use of a connection
# from a thread other than the one that opened it. FastAPI runs sync endpoints in
# a threadpool, so a pooled connection is routinely handed to a different thread
# than the one that created it. Disabling the check is safe here only because
# get_db gives each request its own Session, so no two threads share one
# connection at the same time.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """One Session per request, closed when the request ends."""
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    """Create any missing tables. Existing tables are left untouched."""
    from app import models  # noqa: F401  -- registers Expense on Base.metadata

    Base.metadata.create_all(bind=engine)
