"""F1/F2 regressions with synthetic inputs/candidates, never committed runs.

Expected paths/types come from draft.2, not the external audit workspace.
"""

from copy import deepcopy

import pytest

from dacn_s01.codec import parse_json, serialize_json
from dacn_s01.envelope import EnvelopeInvariantError, check_envelope
from dacn_s01.validation import (
    ProfileValidator, _schema_errors, _schema_locations, validate_input,
)


def failure_candidate(result):
    return {
        "output_contract_version": "0.1.0-draft.2", "status": result.outcome,
        "result_kind": None, "snapshot": None,
        "handoff": {"eligible_for_s02": False, "snapshot_id": None},
        "run": {
            "run_id": "synthetic-fix-run", "validator_version": "synthetic-fix-fixture",
            "received_at": "2026-10-13T10:00:00.000Z", "completed_at": "2026-10-13T10:00:00.001Z",
            "input_schema_sha256": result.input_schema_sha256,
            "request": {"mode": "create", "spec_id": None, "base_revision": None},
            "source": {"source_id": "synthetic-fix-source", "kind": "json_file", "label": None},
            "input_version": deepcopy(result.input_version), "normalizations": deepcopy(result.normalizations),
            "validation": {"checks": deepcopy(result.checks), "errors": deepcopy(result.errors)},
        },
    }


def assert_schema_errors(result, expected):
    """Expected is an independently authored, ordered (code, pointer, details) list."""
    assert result.outcome == "rejected" and result.normalized_input is None
    assert result.checks == {"parse": "passed", "schema": "failed", "cross_field": "not_run", "revision": "not_run"}
    assert [(e["code"], e["pointer"], e["details"]) for e in result.errors] == expected
    for item in result.errors:
        assert item["stage"] == "schema" and item["target"] == "input"
        assert item["related_pointers"] == [] and item["message"]
        assert set(item) == {"code", "stage", "target", "pointer", "related_pointers", "message", "details"}
    candidate = failure_candidate(result)
    check_envelope(candidate)
    check_envelope(parse_json(serialize_json(candidate)))
    assert candidate["snapshot"] is None
    assert candidate["handoff"] == {"eligible_for_s02": False, "snapshot_id": None}


@pytest.mark.parametrize("structured,expected", [
    ({"kind": 123, "value": None}, [
        ("TYPE_MISMATCH", "/constraints/0/constraint/kind", {"expected_types": ["string"], "actual_type": "number"}),
    ]),
    ({"kind": 123}, [
        ("TYPE_MISMATCH", "/constraints/0/constraint/kind", {"expected_types": ["string"], "actual_type": "number"}),
        ("MISSING_FIELD", "/constraints/0/constraint/value", {"field": "value"}),
    ]),
    ({"kind": 123, "value": None, "extra": True}, [
        ("UNKNOWN_FIELD", "/constraints/0/constraint/extra", {"field": "extra"}),
        ("TYPE_MISMATCH", "/constraints/0/constraint/kind", {"expected_types": ["string"], "actual_type": "number"}),
    ]),
], ids=["kind-type", "type-and-required", "type-and-unknown"])
def test_f1_keeps_independent_child_errors(payload, structured, expected):
    payload["constraints"][0]["constraint"] = structured
    before = deepcopy(payload)
    raw = serialize_json(payload)
    assert_schema_errors(validate_input(raw), expected)
    assert payload == before and raw == serialize_json(before)


@pytest.mark.parametrize("kind,actual_type", [(None, "null"), (False, "boolean"), ([], "array"), ({}, "object")])
def test_f1_other_wrong_kind_types(payload, submit, kind, actual_type):
    payload["constraints"][0]["constraint"] = {"kind": kind, "value": None}
    assert_schema_errors(submit(payload), [
        ("TYPE_MISMATCH", "/constraints/0/constraint/kind", {"expected_types": ["string"], "actual_type": actual_type}),
    ])


@pytest.mark.parametrize("structured", [None, {"kind": "local", "value": None}])
def test_f1_valid_nullable_controls(payload, submit, structured):
    payload["constraints"][0]["constraint"] = structured
    result = submit(payload)
    assert result.outcome == "passed" and result.errors == []
    assert result.checks == {"parse": "passed", "schema": "passed", "cross_field": "passed", "revision": "not_run"}
    assert result.normalized_input == payload


@pytest.mark.parametrize("structured,actual_type", [(123, "number"), (True, "boolean"), ([], "array"), ("local", "string")])
def test_f1_wrong_type_at_nullable_node_is_single_parent_error(payload, submit, structured, actual_type):
    payload["constraints"][0]["constraint"] = structured
    assert_schema_errors(submit(payload), [
        ("TYPE_MISMATCH", "/constraints/0/constraint", {"expected_types": ["object", "null"], "actual_type": actual_type}),
    ])


def test_f1_other_nullable_object_with_nested_anyof(payload, submit):
    payload["functional_requirements"][0]["details"] = {"trigger": 123, "data": False, "extra": True}
    assert_schema_errors(submit(payload), [
        ("TYPE_MISMATCH", "/functional_requirements/0/details/data", {"expected_types": ["string", "null"], "actual_type": "boolean"}),
        ("UNKNOWN_FIELD", "/functional_requirements/0/details/extra", {"field": "extra"}),
        ("TYPE_MISMATCH", "/functional_requirements/0/details/trigger", {"expected_types": ["string", "null"], "actual_type": "number"}),
    ])


@pytest.mark.parametrize("null_first", [False, True])
def test_f1_structural_adapter_on_synthetic_nested_schema(null_first):
    # A unit schema, NOT a modification/extension to the input contract. This
    # proves the adapter is not hardcoded to constraint.kind or branch index 0.
    def nullable(branch):
        branches = [{"type": "null"}, branch] if null_first else [branch, {"type": "null"}]
        return {"anyOf": branches}

    schema = nullable({"type": "object", "properties": {
        "box": nullable({"type": "object", "properties": {"label": {"type": "string"}}})}})
    issues = [mapped for problem in ProfileValidator(schema).iter_errors({"box": {"label": True}})
              for mapped in _schema_errors(problem, schema, _schema_locations(schema))]
    assert [(e["code"], e["pointer"], e["details"]) for e in issues] == [
        ("TYPE_MISMATCH", "/box/label", {"expected_types": ["string"], "actual_type": "boolean"})]


@pytest.mark.parametrize("raw,code", [(b"{", "INVALID_JSON"), (b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY")])
@pytest.mark.parametrize("location", [None, "", "/invented/path"])
@pytest.mark.parametrize("roundtrip", [False, True], ids=["internal", "codec-roundtrip"])
@pytest.mark.parametrize("offset", [None, 0], ids=["no-offset", "synthetic-offset"])
def test_f2_parse_pointer_must_be_null(raw, code, location, roundtrip, offset):
    result = validate_input(raw)
    assert result.outcome == "rejected"
    assert result.checks == {"parse": "failed", "schema": "not_run", "cross_field": "not_run", "revision": "not_run"}
    assert result.errors[0]["code"] == code and result.errors[0]["pointer"] is None
    candidate = failure_candidate(result)
    item = candidate["run"]["validation"]["errors"][0]
    item["pointer"] = location
    if offset is not None:
        item["details"]["byte_offset"] = offset  # Synthetic metadata, not a measured source offset.
    if roundtrip:
        candidate = parse_json(serialize_json(candidate))
    if location is None:
        check_envelope(candidate)
        # Input rejection cannot become a system failure by flipping status.
        candidate["status"] = "failed"
        with pytest.raises(EnvelopeInvariantError):
            check_envelope(candidate)
        candidate["status"] = "rejected"
        candidate["handoff"]["eligible_for_s02"] = True
        with pytest.raises(EnvelopeInvariantError):
            check_envelope(candidate)
    else:
        with pytest.raises(EnvelopeInvariantError, match="Parse errors require a null pointer"):
            check_envelope(candidate)


def test_f2_does_not_force_null_pointer_on_other_stages():
    schema = failure_candidate(validate_input(b"[]"))
    assert schema["run"]["validation"]["errors"][0]["pointer"] == ""
    check_envelope(parse_json(serialize_json(schema)))
    system = failure_candidate(validate_input(b"1e9999999999999999999999999999999999999999"))
    assert system["status"] == "failed"
    system["run"]["validation"]["errors"][0]["pointer"] = "/codec"
    check_envelope(parse_json(serialize_json(system)))
