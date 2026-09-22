from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from sqlalchemy.orm import Session

from app import repo
from app.db import get_db, init_db
from app.schemas import ExpenseCreate, ExpenseFilters, ExpenseList, ExpenseOut


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/expenses", status_code=201, response_model=ExpenseOut)
def create_expense(body: ExpenseCreate, session: Annotated[Session, Depends(get_db)]) -> ExpenseOut:
    expense = repo.create_expense(session, **body.model_dump())
    return ExpenseOut.from_model(expense)


@app.get("/expenses", response_model=ExpenseList)
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
