"""Validates the contracts themselves: OpenAPI documents, JSON Schemas and fixtures."""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "fixtures" / "suggestions"


def _validator() -> Draft202012Validator:
    item = json.loads((SCHEMAS / "ai-suggestion.v1.schema.json").read_text())
    registry = Registry().with_resource(item["$id"], Resource.from_contents(item))
    return Draft202012Validator(item, registry=registry)


@pytest.mark.parametrize("name", ["api.v1.yaml", "ai-gateway.v1.yaml"])
def test_openapi_documents_are_valid(name):
    spec, base_uri = read_from_filename(str(ROOT / "openapi" / name))
    validate(spec, base_uri=base_uri)


@pytest.mark.parametrize("name", ["api.v1.yaml", "ai-gateway.v1.yaml"])
def test_all_paths_are_versioned(name):
    spec = yaml.safe_load((ROOT / "openapi" / name).read_text())
    assert all(p.startswith("/api/v1/") for p in spec["paths"])


@pytest.mark.parametrize("path", sorted(SCHEMAS.glob("*.json")), ids=lambda p: p.name)
def test_json_schemas_are_valid(path):
    Draft202012Validator.check_schema(json.loads(path.read_text()))


@pytest.mark.parametrize("path", sorted((FIXTURES / "valid").glob("*.json")), ids=lambda p: p.name)
def test_valid_fixtures(path):
    assert list(_validator().iter_errors(json.loads(path.read_text()))) == []


@pytest.mark.parametrize("path", sorted((FIXTURES / "invalid").glob("*.json")), ids=lambda p: p.name)
def test_invalid_fixtures(path):
    assert list(_validator().iter_errors(json.loads(path.read_text()))) != []


def test_growth_cases_are_well_formed():
    data = json.loads((ROOT / "fixtures" / "growth" / "cases.json").read_text())
    names = [c["name"] for c in data["cases"]]
    assert len(names) == len(set(names)) and data["tolerance"] > 0
