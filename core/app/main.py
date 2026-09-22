from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app import repo
from app.db import get_db, init_db
from app.schemas import ExpenseCreate, ExpenseOut


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
