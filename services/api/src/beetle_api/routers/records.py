"""Species, beetles and weight history.

History records are append-only; DELETE writes a tombstone (``deleted_at``).
Updates use optimistic concurrency: the client sends the revision it last saw
and receives 409 Conflict if the row changed meanwhile.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, insert, select, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from ..db import beetles, species, weight_records
from ..deps import get_conn
from ..growth import WeightPoint, compute_growth
from ..models import (
    BeetleIn,
    BeetleOut,
    BeetlePatch,
    GrowthMetricsOut,
    SpeciesIn,
    SpeciesOut,
    Status,
    WeightIn,
    WeightOut,
)

router = APIRouter(prefix="/api/v1", tags=["records"])


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def _live_beetle(conn: Connection, beetle_id: uuid.UUID) -> dict:
    row = (
        conn.execute(select(beetles).where(beetles.c.id == beetle_id, beetles.c.deleted_at.is_(None)))
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "beetle not found")
    return dict(row)


def _check_parents(
    conn: Connection, beetle_id: uuid.UUID, sire_id: uuid.UUID | None, dam_id: uuid.UUID | None
) -> None:
    """Parents must be other live beetles of a compatible sex, and a beetle may
    not become its own ancestor."""
    if sire_id is not None and sire_id == dam_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "sire_id and dam_id must differ")
    for role, parent_id, wrong_sex in (("sire", sire_id, "female"), ("dam", dam_id, "male")):
        if parent_id is None:
            continue
        if parent_id == beetle_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"a beetle cannot be its own {role}")
        sex = conn.execute(
            select(beetles.c.sex).where(beetles.c.id == parent_id, beetles.c.deleted_at.is_(None))
        ).scalar_one_or_none()
        if sex is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown {role}_id")
        if sex == wrong_sex:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{role} cannot be {wrong_sex}")
        if beetle_id in _ancestors(conn, parent_id):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{role} would create an ancestry cycle")


def _ancestors(conn: Connection, beetle_id: uuid.UUID) -> set[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    frontier = {beetle_id}
    while frontier:
        rows = conn.execute(select(beetles.c.sire_id, beetles.c.dam_id).where(beetles.c.id.in_(frontier))).all()
        frontier = {p for row in rows for p in row if p is not None and p not in seen}
        seen |= frontier
    return seen


# ------------------------------------------------------------------ species


@router.get("/species", response_model=list[SpeciesOut])
def list_species(conn: Connection = Depends(get_conn)):
    q = select(species).where(species.c.deleted_at.is_(None)).order_by(species.c.code)
    return [dict(r) for r in conn.execute(q).mappings()]


@router.post("/species", response_model=SpeciesOut, status_code=status.HTTP_201_CREATED)
def create_species(body: SpeciesIn, conn: Connection = Depends(get_conn)):
    if (
        body.expected_pupa_days_min is not None
        and body.expected_pupa_days_max is not None
        and body.expected_pupa_days_min > body.expected_pupa_days_max
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "expected_pupa_days_min > expected_pupa_days_max")
    values = body.model_dump()
    values["id"] = body.id or uuid.uuid4()
    try:
        row = conn.execute(insert(species).values(**values).returning(species)).mappings().one()
    except IntegrityError as e:
        raise _conflict(f"species code {body.code} or id already exists") from e
    return dict(row)


# ------------------------------------------------------------------ beetles


@router.get("/beetles", response_model=list[BeetleOut])
def list_beetles(
    conn: Connection = Depends(get_conn),
    status_filter: Status | None = Query(default=None, alias="status"),
    species_code: str | None = None,
    include_deleted: bool = False,
):
    q = select(beetles).order_by(beetles.c.code)
    if not include_deleted:
        q = q.where(beetles.c.deleted_at.is_(None))
    if status_filter:
        q = q.where(beetles.c.status == status_filter)
    if species_code:
        q = q.join(species, species.c.id == beetles.c.species_id).where(species.c.code == species_code.upper())
    return [dict(r) for r in conn.execute(q).mappings()]


@router.post("/beetles", response_model=BeetleOut, status_code=status.HTTP_201_CREATED)
def create_beetle(body: BeetleIn, conn: Connection = Depends(get_conn)):
    sp = conn.execute(select(species.c.code).where(species.c.id == body.species_id)).scalar_one_or_none()
    if sp is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown species_id")
    if not body.code.startswith(f"{sp}-"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"code must start with species code {sp}-")
    values = body.model_dump()
    values["id"] = body.id or uuid.uuid4()
    _check_parents(conn, values["id"], body.sire_id, body.dam_id)
    try:
        row = conn.execute(insert(beetles).values(**values).returning(beetles)).mappings().one()
    except IntegrityError as e:
        raise _conflict(f"beetle code {body.code} or id already exists") from e
    return dict(row)


@router.get("/beetles/{beetle_id}", response_model=BeetleOut)
def get_beetle(beetle_id: uuid.UUID, conn: Connection = Depends(get_conn)):
    return _live_beetle(conn, beetle_id)


@router.patch("/beetles/{beetle_id}", response_model=BeetleOut)
def update_beetle(beetle_id: uuid.UUID, body: BeetlePatch, conn: Connection = Depends(get_conn)):
    current = _live_beetle(conn, beetle_id)
    changes = body.model_dump(exclude_unset=True, exclude={"revision"})
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "no fields to update")
    if {"sire_id", "dam_id"} & changes.keys():
        _check_parents(
            conn, beetle_id, changes.get("sire_id", current["sire_id"]), changes.get("dam_id", current["dam_id"])
        )
    if changes.get("sex") in ("male", "female"):
        role = beetles.c.sire_id if changes["sex"] == "female" else beetles.c.dam_id
        has_children = conn.execute(
            select(func.count()).where(role == beetle_id, beetles.c.deleted_at.is_(None))
        ).scalar_one()
        if has_children:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"sex conflicts with this beetle's role as parent of {has_children}"
            )
    row = (
        conn.execute(
            update(beetles)
            .where(beetles.c.id == beetle_id, beetles.c.revision == body.revision)
            .values(**changes)
            .returning(beetles)
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _conflict("revision mismatch: the beetle was changed elsewhere; reload and retry")
    return dict(row)


@router.delete("/beetles/{beetle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_beetle(beetle_id: uuid.UUID, conn: Connection = Depends(get_conn)):
    _live_beetle(conn, beetle_id)
    conn.execute(update(beetles).where(beetles.c.id == beetle_id).values(deleted_at=func.now()))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ weights


@router.get("/beetles/{beetle_id}/weights", response_model=list[WeightOut])
def list_weights(beetle_id: uuid.UUID, conn: Connection = Depends(get_conn)):
    _live_beetle(conn, beetle_id)
    q = (
        select(weight_records)
        .where(weight_records.c.beetle_id == beetle_id, weight_records.c.deleted_at.is_(None))
        .order_by(weight_records.c.measured_at, weight_records.c.id)
    )
    return [dict(r) for r in conn.execute(q).mappings()]


@router.post("/beetles/{beetle_id}/weights", response_model=WeightOut, status_code=status.HTTP_201_CREATED)
def add_weight(beetle_id: uuid.UUID, body: WeightIn, conn: Connection = Depends(get_conn)):
    _live_beetle(conn, beetle_id)
    if body.measured_at.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "measured_at must include a time zone offset")
    if body.measured_at > datetime.now(UTC) + timedelta(days=1):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "measured_at is in the future")
    values = body.model_dump()
    values["id"] = body.id or uuid.uuid4()
    try:
        row = (
            conn.execute(insert(weight_records).values(beetle_id=beetle_id, **values).returning(weight_records))
            .mappings()
            .one()
        )
    except IntegrityError as e:
        raise _conflict("weight record id already exists") from e
    return dict(row)


@router.delete("/beetles/{beetle_id}/weights/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(beetle_id: uuid.UUID, record_id: uuid.UUID, conn: Connection = Depends(get_conn)):
    result = conn.execute(
        update(weight_records)
        .where(
            weight_records.c.id == record_id,
            weight_records.c.beetle_id == beetle_id,
            weight_records.c.deleted_at.is_(None),
        )
        .values(deleted_at=func.now())
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "weight record not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/beetles/{beetle_id}/growth-metrics", response_model=GrowthMetricsOut)
def growth_metrics(
    beetle_id: uuid.UUID,
    since_days: int | None = Query(default=None, ge=1, le=3650),
    conn: Connection = Depends(get_conn),
):
    _live_beetle(conn, beetle_id)
    q = select(weight_records).where(weight_records.c.beetle_id == beetle_id, weight_records.c.deleted_at.is_(None))
    if since_days:
        q = q.where(weight_records.c.measured_at >= datetime.now(UTC) - timedelta(days=since_days))
    points = [
        WeightPoint(id=str(r["id"]), measured_at=r["measured_at"], grams=r["weight_grams"])
        for r in conn.execute(q).mappings()
    ]
    return GrowthMetricsOut(beetle_id=beetle_id, window_days=since_days, metrics=compute_growth(points))
