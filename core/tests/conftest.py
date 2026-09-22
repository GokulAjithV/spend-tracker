from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  -- registers Expense on Base.metadata
from app.auth import load_api_key
from app.db import Base, get_db
from app.main import app

API_KEY = "test-key"


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    # A fresh in-memory database per test. StaticPool hands every checkout the
    # same single connection; without it each connection to "sqlite://" would
    # open its own empty database and the tables would vanish.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Not used as a context manager, so lifespan (init_db against the real
    # database file) does not run; this does lifespan's key loading instead.
    monkeypatch.setenv("API_KEY", API_KEY)
    app.state.api_key = load_api_key()
    yield TestClient(app, headers={"X-API-Key": API_KEY})
    app.dependency_overrides.clear()
    del app.state.api_key
