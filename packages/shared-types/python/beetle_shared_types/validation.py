"""Strict validation of AI care suggestions against the bundled JSON Schema."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .ai_suggestion_v1 import AiCareSuggestion

_SUGGESTION = "ai-suggestion.v1.schema.json"
_BATCH = "ai-suggestion-batch.v1.schema.json"


class SuggestionValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _load(name: str) -> dict[str, Any]:
    return json.loads(resources.files(__package__).joinpath("schemas", name).read_text(encoding="utf-8"))


@lru_cache
def _validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    suggestion, batch = _load(_SUGGESTION), _load(_BATCH)
    registry = Registry().with_resources(
        [(s["$id"], Resource.from_contents(s)) for s in (suggestion, batch)]
        + [(_SUGGESTION, Resource.from_contents(suggestion))]
    )
    return Draft202012Validator(suggestion, registry=registry), Draft202012Validator(batch, registry=registry)


def _errors(validator: Draft202012Validator, data: Any) -> list[str]:
    return sorted(
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in validator.iter_errors(data)
    )


def validate_suggestion(data: Any) -> AiCareSuggestion:
    """Validates one suggestion; raises SuggestionValidationError."""
    errors = _errors(_validators()[0], data)
    if errors:
        raise SuggestionValidationError(errors)
    return AiCareSuggestion.model_validate(data)


def validate_batch(data: Any) -> tuple[list[AiCareSuggestion], list[str]]:
    """Validates ``{"schema_version": "1", "suggestions": [...]}``.

    Envelope errors reject everything. Otherwise each item is validated on its
    own: valid items are returned and invalid ones reported, never repaired.
    """
    if not isinstance(data, dict) or set(data) != {"schema_version", "suggestions"}:
        return [], ["<root>: expected exactly {schema_version, suggestions}"]
    if data["schema_version"] != "1" or not isinstance(data["suggestions"], list):
        return [], ["<root>: unsupported schema_version or suggestions is not an array"]
    if len(data["suggestions"]) > 10:
        return [], ["suggestions: too many items"]
    valid: list[AiCareSuggestion] = []
    errors: list[str] = []
    for i, item in enumerate(data["suggestions"]):
        try:
            valid.append(validate_suggestion(item))
        except SuggestionValidationError as e:
            errors += [f"suggestions/{i}/{msg}" for msg in e.errors]
    return valid, errors
