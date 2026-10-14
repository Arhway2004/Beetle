"""Table definitions mirroring database/migrations (the migrations own the schema;
the API never creates or alters tables)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Connection, Engine

metadata = MetaData()


def _sync_columns() -> list[Column]:
    return [
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
        Column("deleted_at", DateTime(timezone=True)),
        Column("revision", Integer),
        Column("change_seq", Integer),
    ]


species = Table(
    "species",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String),
    Column("scientific_name", String),
    Column("common_name", Text),
    Column("is_builtin", Boolean),
    Column("expected_pupa_days_min", Integer),
    Column("expected_pupa_days_max", Integer),
    Column("notes", Text),
    *_sync_columns(),
)

beetles = Table(
    "beetles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String),
    Column("species_id", UUID(as_uuid=True)),
    Column("sex", Text),
    Column("status", Text),
    Column("acquired_at", DateTime(timezone=True)),
    Column("hatch_date", DateTime(timezone=True)),
    Column("estimated_hatch_date", DateTime(timezone=True)),
    Column("hatch_uncertainty_days", Integer),
    Column("sensor_id", UUID(as_uuid=True)),
    Column("sire_id", UUID(as_uuid=True)),
    Column("dam_id", UUID(as_uuid=True)),
    Column("sire_note", Text),
    Column("dam_note", Text),
    Column("notes", Text),
    *_sync_columns(),
)

weight_records = Table(
    "weight_records",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("beetle_id", UUID(as_uuid=True)),
    Column("measured_at", DateTime(timezone=True)),
    Column("weight_grams", Float),
    Column("notes", Text),
    *_sync_columns(),
)

# Record tables that can be cited as evidence, keyed by their beetle column.
EVIDENCE_TABLES = {
    "weight_records": "beetle_id",
    "observation_records": "beetle_id",
    "substrate_changes": "beetle_id",
    "container_changes": "beetle_id",
    "life_stage_events": "beetle_id",
}


class Database:
    def __init__(self, url: str):
        self.engine: Engine = create_engine(url, pool_pre_ping=True, future=True)

    def connect(self) -> Iterator[Connection]:
        with self.engine.begin() as conn:
            yield conn
