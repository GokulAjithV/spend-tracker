import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

# auto_error=False: a missing header reaches require_api_key as None, so missing
# and wrong keys share one code path and one response - a caller can't tell which.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def load_api_key() -> str:
    """Called from lifespan. Raising here aborts startup, so the app never
    serves requests without a key configured."""
    key = os.environ["API_KEY"]
    if not key.strip():
        # An empty key can never be sent (the header would be empty and treated
        # as missing), so this is a misconfiguration, not an open API.
        raise RuntimeError("API_KEY is set but empty")
    return key


def require_api_key(
    request: Request, provided: Annotated[str | None, Security(api_key_header)]
) -> None:
    expected: str = request.app.state.api_key
    # Compared as bytes: compare_digest raises TypeError on non-ASCII str, and
    # header values are decoded as latin-1, so a header like "é" would be a 500.
    if provided is None or not secrets.compare_digest(
        provided.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
