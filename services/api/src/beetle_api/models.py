from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BEETLE_CODE = r"^[A-Z][A-Z0-9]{1,7}-[0-9]{3,6}$"
SPECIES_CODE = r"^[A-Z][A-Z0-9]{1,7}$"

Sex = Literal["male", "female", "unknown"]
Status = Literal["active", "deceased", "transferred", "archived"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SyncFields(BaseModel):
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    revision: int


class SpeciesIn(Strict):
    id: uuid.UUID | None = None
    code: str = Field(pattern=SPECIES_CODE)
    scientific_name: str = Field(min_length=1, max_length=120)
    common_name: str | None = None
    expected_pupa_days_min: int | None = Field(default=None, gt=0, le=1000)
    expected_pupa_days_max: int | None = Field(default=None, gt=0, le=1000)


class SpeciesOut(SyncFields):
    id: uuid.UUID
    code: str
    scientific_name: str
    common_name: str | None
    is_builtin: bool
    expected_pupa_days_min: int | None
    expected_pupa_days_max: int | None


class BeetleIn(Strict):
    id: uuid.UUID | None = Field(default=None, description="Client-generated stable UUID (recommended)")
    code: str = Field(pattern=BEETLE_CODE)
    species_id: uuid.UUID
    sex: Sex = "unknown"
    status: Status = "active"
    acquired_at: datetime | None = None
    hatch_date: datetime | None = None
    estimated_hatch_date: datetime | None = None
    hatch_uncertainty_days: int | None = Field(default=None, ge=0)
    sire_id: uuid.UUID | None = Field(default=None, description="Father, if it is a beetle in the collection")
    dam_id: uuid.UUID | None = Field(default=None, description="Mother, if it is a beetle in the collection")
    sire_note: str | None = Field(default=None, max_length=200, description="Father kept elsewhere, e.g. 'WD 125 mm'")
    dam_note: str | None = Field(default=None, max_length=200, description="Mother kept elsewhere")
    notes: str | None = Field(default=None, max_length=10_000)


class BeetlePatch(Strict):
    revision: int = Field(description="Revision the client last saw; a mismatch returns 409 Conflict")
    sex: Sex | None = None
    status: Status | None = None
    acquired_at: datetime | None = None
    hatch_date: datetime | None = None
    estimated_hatch_date: datetime | None = None
    hatch_uncertainty_days: int | None = Field(default=None, ge=0)
    sire_id: uuid.UUID | None = Field(default=None, description="Father, if it is a beetle in the collection")
    dam_id: uuid.UUID | None = Field(default=None, description="Mother, if it is a beetle in the collection")
    sire_note: str | None = Field(default=None, max_length=200, description="Father kept elsewhere, e.g. 'WD 125 mm'")
    dam_note: str | None = Field(default=None, max_length=200, description="Mother kept elsewhere")
    notes: str | None = Field(default=None, max_length=10_000)


class BeetleOut(SyncFields):
    id: uuid.UUID
    code: str
    species_id: uuid.UUID
    sex: str
    status: str
    acquired_at: datetime | None
    hatch_date: datetime | None
    estimated_hatch_date: datetime | None
    hatch_uncertainty_days: int | None
    sire_id: uuid.UUID | None
    dam_id: uuid.UUID | None
    sire_note: str | None
    dam_note: str | None
    notes: str | None


class WeightIn(Strict):
    id: uuid.UUID | None = None
    measured_at: datetime
    weight_grams: float = Field(gt=0, lt=1000)
    notes: str | None = Field(default=None, max_length=4000)


class WeightOut(SyncFields):
    id: uuid.UUID
    beetle_id: uuid.UUID
    measured_at: datetime
    weight_grams: float
    notes: str | None


class GrowthMetricsOut(BaseModel):
    beetle_id: uuid.UUID
    window_days: int | None
    metrics: dict[str, Any]


class SuggestionValidationOut(BaseModel):
    valid: bool
    schema_errors: list[str]
    business_errors: list[str]
    requires_user_confirmation: Literal[True] = True


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    schema_version: int | None
