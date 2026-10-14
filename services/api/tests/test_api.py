from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from beetle_api.growth import WeightPoint, compute_growth
from beetle_api.main import create_app

from .conftest import CCK, DHH, ROOT

FIXTURES = ROOT / "packages/api-contracts/fixtures"


def make_beetle(client, code="DHH-001", species_id=DHH, **kw):
    r = client.post("/api/v1/beetles", json={"id": str(uuid.uuid4()), "code": code, "species_id": species_id, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_health_reports_schema_version(client):
    assert client.get("/api/v1/health").json() == {"status": "ok", "database": True, "schema_version": 2}


def test_beetle_parents_are_validated(client):
    sire = make_beetle(client, code="DHH-001", sex="male")
    dam = make_beetle(client, code="DHH-002", sex="female")
    child = make_beetle(client, code="DHH-003", sire_id=sire["id"], dam_id=dam["id"], sire_note="WD 150 mm")
    assert (child["sire_id"], child["dam_id"], child["sire_note"]) == (sire["id"], dam["id"], "WD 150 mm")

    def post(code, **kw):
        return client.post("/api/v1/beetles", json={"code": code, "species_id": DHH, **kw}).status_code

    assert post("DHH-010", sire_id=dam["id"]) == 422  # a female cannot be the sire
    assert post("DHH-011", dam_id=sire["id"]) == 422  # a male cannot be the dam
    assert post("DHH-012", sire_id=str(uuid.uuid4())) == 422  # unknown parent

    def patch(b, **kw):
        current = client.get(f"/api/v1/beetles/{b['id']}").json()
        return client.patch(f"/api/v1/beetles/{b['id']}", json={"revision": current["revision"], **kw})

    assert patch(sire, sire_id=sire["id"]).status_code == 422  # own parent
    assert patch(sire, sire_id=child["id"]).status_code == 422  # child cannot become its parent's ancestor
    assert patch(sire, sex="female").status_code == 422  # it is the sire of DHH-003
    assert patch(dam, sex="unknown").status_code == 200
    assert patch(child, sire_id=None, sire_note=None).json()["sire_id"] is None


def test_builtin_species_are_present(client):
    codes = {s["code"]: s["id"] for s in client.get("/api/v1/species").json()}
    assert codes == {"CCK": CCK, "DHH": DHH}


def test_beetle_crud_with_tombstone_and_conflicts(client):
    b = make_beetle(client, sex="male")
    assert client.post("/api/v1/beetles", json={"code": "DHH-001", "species_id": DHH}).status_code == 409
    assert client.post("/api/v1/beetles", json={"code": "CCK-001", "species_id": DHH}).status_code == 422
    assert client.post("/api/v1/beetles", json={"code": "dhh 1", "species_id": DHH}).status_code == 422
    assert client.post("/api/v1/beetles", json={"code": "DHH-002", "species_id": DHH, "x": 1}).status_code == 422

    r = client.patch(f"/api/v1/beetles/{b['id']}", json={"revision": b["revision"], "notes": "big"})
    assert r.status_code == 200 and r.json()["revision"] == b["revision"] + 1
    stale = client.patch(f"/api/v1/beetles/{b['id']}", json={"revision": b["revision"], "notes": "stale"})
    assert stale.status_code == 409

    assert client.delete(f"/api/v1/beetles/{b['id']}").status_code == 204
    assert client.get(f"/api/v1/beetles/{b['id']}").status_code == 404
    assert client.get("/api/v1/beetles").json() == []
    deleted = client.get("/api/v1/beetles", params={"include_deleted": True}).json()
    assert deleted[0]["deleted_at"] is not None


def test_weights_append_only_and_growth_metrics(client):
    b = make_beetle(client)
    for at, g in [("2026-01-01T00:00:00Z", 10), ("2026-01-11T00:00:00Z", 15), ("2026-01-31T00:00:00Z", 25)]:
        assert (
            client.post(f"/api/v1/beetles/{b['id']}/weights", json={"measured_at": at, "weight_grams": g}).status_code
            == 201
        )
    m = client.get(f"/api/v1/beetles/{b['id']}/growth-metrics").json()["metrics"]
    assert m["change_since_previous_grams"] == 10 and m["avg_weekly_change_grams"] == pytest.approx(3.5)

    w = client.get(f"/api/v1/beetles/{b['id']}/weights").json()
    assert client.delete(f"/api/v1/beetles/{b['id']}/weights/{w[-1]['id']}").status_code == 204
    assert client.delete(f"/api/v1/beetles/{b['id']}/weights/{w[-1]['id']}").status_code == 404
    assert len(client.get(f"/api/v1/beetles/{b['id']}/weights").json()) == 2

    bad = client.post(
        f"/api/v1/beetles/{b['id']}/weights", json={"measured_at": "2026-01-01T00:00:00", "weight_grams": 5}
    )
    assert bad.status_code == 422  # naive timestamp
    assert (
        client.post(
            f"/api/v1/beetles/{b['id']}/weights", json={"measured_at": "2026-01-01T00:00:00Z", "weight_grams": 0}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "case", json.loads((FIXTURES / "growth/cases.json").read_text())["cases"], ids=lambda c: c["name"]
)
def test_growth_matches_shared_vectors(case):
    pts = [
        WeightPoint(r["id"], datetime.fromisoformat(r["measured_at"].replace("Z", "+00:00")), r["weight_grams"])
        for r in case["records"]
    ]
    got = compute_growth(pts)
    for key, expected in case["expected"].items():
        if key == "max_at" and expected is not None:
            assert datetime.fromisoformat(got[key]) == datetime.fromisoformat(expected.replace("Z", "+00:00"))
        elif isinstance(expected, float | int) and not isinstance(expected, bool):
            assert got[key] == pytest.approx(expected, abs=1e-6), key
        else:
            assert got[key] == expected, key


def test_suggestion_validation_schema_and_business_rules(client):
    b = make_beetle(client, code="CCK-001", species_id=CCK)
    w = client.post(
        f"/api/v1/beetles/{b['id']}/weights", json={"measured_at": "2026-02-01T00:00:00Z", "weight_grams": 20}
    ).json()
    other = make_beetle(client, code="CCK-002", species_id=CCK)
    w_other = client.post(
        f"/api/v1/beetles/{other['id']}/weights", json={"measured_at": "2026-02-01T00:00:00Z", "weight_grams": 20}
    ).json()

    base = json.loads((FIXTURES / "suggestions/valid/possible-prepupa.json").read_text())
    ok = client.post("/api/v1/ai/suggestions/validate", json={**base, "evidence_record_ids": [w["id"]]}).json()
    assert ok == {"valid": True, "schema_errors": [], "business_errors": [], "requires_user_confirmation": True}

    fabricated = client.post("/api/v1/ai/suggestions/validate", json=base).json()  # "OBS-012" does not exist
    assert not fabricated["valid"] and fabricated["business_errors"]

    cross = client.post("/api/v1/ai/suggestions/validate", json={**base, "evidence_record_ids": [w_other["id"]]}).json()
    assert "different beetle" in cross["business_errors"][0]

    unknown = client.post(
        "/api/v1/ai/suggestions/validate", json={**base, "beetle_id": "CCK-999", "evidence_record_ids": [w["id"]]}
    ).json()
    assert "does not exist" in unknown["business_errors"][0]

    for f in sorted((FIXTURES / "suggestions/invalid").glob("*.json")):
        r = client.post("/api/v1/ai/suggestions/validate", json=json.loads(f.read_text())).json()
        assert r["valid"] is False and r["schema_errors"], f.name


def test_routes_match_openapi_contract():
    spec = yaml.safe_load((ROOT / "packages/api-contracts/openapi/api.v1.yaml").read_text())
    methods = {"get", "post", "put", "patch", "delete"}
    contract = {(p, m) for p, ops in spec["paths"].items() for m in ops if m in methods}
    generated = create_app().openapi()["paths"]
    implemented = {(p, m) for p, ops in generated.items() for m in ops if m in methods}
    assert implemented == contract


def test_api_has_no_endpoint_that_writes_without_validation():
    # The API exposes no endpoint that turns AI output into records or reminders.
    paths = yaml.safe_load((ROOT / "packages/api-contracts/openapi/api.v1.yaml").read_text())["paths"]
    ai_paths = [p for p in paths if p.startswith("/api/v1/ai")]
    assert ai_paths == ["/api/v1/ai/suggestions/validate"]
    assert Path(ROOT / "services/api/src/beetle_api/routers/ai.py").read_text().count("insert(") == 0
