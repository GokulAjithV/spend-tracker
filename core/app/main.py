from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Security
from sqlalchemy.orm import Session

from app import config, repo
from app.auth import load_api_key, require_api_key
from app.db import get_db, init_db
from app.schemas import (
    ExpenseCreate,
    ExpenseFilters,
    ExpenseList,
    ExpenseOut,
    Summary,
    SummaryQuery,
)
from app.summary import build_summary, month_range, previous_month


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Before init_db, so a missing key fails fast without touching the database.
    app.state.api_key = load_api_key()
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

protected = [Security(require_api_key)]

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/expenses", status_code=201, response_model=ExpenseOut, dependencies=protected)
def create_expense(body: ExpenseCreate, session: Annotated[Session, Depends(get_db)]) -> ExpenseOut:
    expense = repo.create_expense(session, **body.model_dump())
    return ExpenseOut.from_model(expense)


@app.get("/expenses", response_model=ExpenseList, dependencies=protected)
def list_expenses(
    filters: Annotated[ExpenseFilters, Query()], session: Annotated[Session, Depends(get_db)]
) -> ExpenseList:
    expenses = repo.list_expenses(
        session,
        categories=filters.category,
        date_from=filters.date_from,
        date_to=filters.date_to,
        limit=filters.limit,
        offset=filters.offset,
    )
    return ExpenseList(expenses=[ExpenseOut.from_model(e) for e in expenses])


@app.get("/summary", response_model=Summary, dependencies=protected)
def get_summary(
    query: Annotated[SummaryQuery, Query()], session: Annotated[Session, Depends(get_db)]
) -> Summary:
    today = config.today()
    month = query.month or today.replace(day=1)
    prev = previous_month(month)
    current = repo.sum_by_category(session, *month_range(month.year, month.month))
    previous = repo.sum_by_category(session, *month_range(prev.year, prev.month))
    return build_summary(month, current, previous, today)
