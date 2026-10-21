"""Read and check the packaged schema artifact, NOT a requirements instance."""

import hashlib
import json
from decimal import Decimal
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .codec import CodecError, ProcessingError, _reject_constant, _unique_object

INPUT_VERSION = "1.0.0"
PROFILE_VERSION = "0.1.0-draft.2"
SCHEMA_SHA256 = "0a7cda79ac2d949579c0a2279df3d60c18b8f0cd6335e28fac6d51d46248613d"


class SchemaResourceError(ProcessingError):
    """Packaged artifact/configuration failure, never an input rejection."""


def read_schema_bytes() -> bytes:
    """Resolve only local package data and verify the baseline byte digest."""
    try:
        raw = files("dacn_s01").joinpath(
            "schemas", "input", INPUT_VERSION, "system-input.schema.json"
        ).read_bytes()
    except OSError as exc:
        raise SchemaResourceError("Cannot read packaged input schema") from exc
    if hashlib.sha256(raw).hexdigest() != SCHEMA_SHA256:
        raise SchemaResourceError("Packaged input schema digest differs from baseline")
    return raw


def load_schema() -> dict[str, Any]:
    """Check duplicates and Draft 2020-12 metaschema; retain integer keywords.

    This returns a fresh schema tree. It does not apply the draft.2 W profile,
    run instance validation or authorize handoff to S02.
    """
    try:
        schema = json.loads(
            read_schema_bytes(), object_pairs_hook=_unique_object,
            parse_int=int, parse_float=Decimal, parse_constant=_reject_constant,
        )
        Draft202012Validator.check_schema(schema)
    except (CodecError, ValueError, SchemaError) as exc:
        raise SchemaResourceError("Packaged schema artifact failed integrity/metaschema checks") from exc
    return schema
