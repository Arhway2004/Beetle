import json
from pathlib import Path

import pytest
from beetle_shared_types import SuggestionValidationError, validate_batch, validate_suggestion

FIXTURES = Path(__file__).resolve().parents[2] / "api-contracts" / "fixtures" / "suggestions"
SCHEMAS = Path(__file__).resolve().parents[2] / "api-contracts" / "schemas"
BUNDLED = Path(__file__).resolve().parents[1] / "python" / "beetle_shared_types" / "schemas"


@pytest.mark.parametrize("path", sorted((FIXTURES / "valid").glob("*.json")), ids=lambda p: p.name)
def test_valid_fixtures(path):
    s = validate_suggestion(json.loads(path.read_text()))
    assert s.requires_user_confirmation is True


@pytest.mark.parametrize("path", sorted((FIXTURES / "invalid").glob("*.json")), ids=lambda p: p.name)
def test_invalid_fixtures(path):
    with pytest.raises(SuggestionValidationError):
        validate_suggestion(json.loads(path.read_text()))


def test_string_numbers_are_not_coerced():
    data = json.loads((FIXTURES / "valid" / "possible-prepupa.json").read_text())
    data["suggested_reminder"]["delay_days"] = "3"
    with pytest.raises(SuggestionValidationError):
        validate_suggestion(data)


def test_batch_keeps_valid_and_reports_invalid():
    ok = json.loads((FIXTURES / "valid" / "possible-prepupa.json").read_text())
    bad = json.loads((FIXTURES / "invalid" / "no-confirmation.json").read_text())
    valid, errors = validate_batch({"schema_version": "1", "suggestions": [ok, bad]})
    assert len(valid) == 1 and errors and errors[0].startswith("suggestions/1/")
    assert validate_batch({"schema_version": "2", "suggestions": [ok]})[0] == []


def test_bundled_schemas_are_in_sync_with_contracts():
    for name in ("ai-suggestion.v1.schema.json", "ai-suggestion-batch.v1.schema.json"):
        assert (BUNDLED / name).read_text() == (SCHEMAS / name).read_text(), "run packages/shared-types/generate.sh"
