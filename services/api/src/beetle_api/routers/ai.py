"""Backend validation of AI care suggestions.

The AI Gateway never writes records. Before any AI suggestion is persisted on
the server it must pass this endpoint: strict schema validation (shared JSON
Schema) plus business rules against stored data (beetle exists, every cited
evidence record exists and belongs to that beetle). The result is advisory —
nothing is created or scheduled here.
"""

from __future__ import annotations

import uuid
from typing import Any

from beetle_shared_types import SuggestionValidationError, validate_suggestion
from fastapi import APIRouter, Body, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..db import EVIDENCE_TABLES
from ..deps import get_conn
from ..models import SuggestionValidationOut

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/suggestions/validate", response_model=SuggestionValidationOut)
def validate(payload: Any = Body(...), conn: Connection = Depends(get_conn)) -> SuggestionValidationOut:
    try:
        s = validate_suggestion(payload)
    except SuggestionValidationError as e:
        return SuggestionValidationOut(valid=False, schema_errors=e.errors, business_errors=[])

    business: list[str] = []
    beetle_id: uuid.UUID | None = None
    if s.beetle_id is not None:
        beetle_id = conn.execute(
            text("SELECT id FROM beetles WHERE code = :c AND deleted_at IS NULL"), {"c": s.beetle_id}
        ).scalar_one_or_none()
        if beetle_id is None:
            business.append(f"beetle {s.beetle_id} does not exist")

    for ev in s.evidence_record_ids:
        rid = ev.root
        try:
            rid_uuid = uuid.UUID(rid)
        except ValueError:
            business.append(f"evidence {rid} is not a record id")
            continue
        found = False
        for table, beetle_col in EVIDENCE_TABLES.items():
            row = conn.execute(
                text(f"SELECT {beetle_col} FROM {table} WHERE id = :id AND deleted_at IS NULL"),  # noqa: S608
                {"id": rid_uuid},
            ).first()
            if row is not None:
                found = True
                if beetle_id is not None and row[0] != beetle_id:
                    business.append(f"evidence {rid} belongs to a different beetle")
                break
        if not found and rid_uuid != beetle_id:
            business.append(f"evidence {rid} not found")

    return SuggestionValidationOut(valid=not business, schema_errors=[], business_errors=business)
