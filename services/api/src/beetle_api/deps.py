from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.engine import Connection


def get_conn(request: Request) -> Iterator[Connection]:
    """One transaction per request; committed on success, rolled back on error."""
    yield from request.app.state.db.connect()
