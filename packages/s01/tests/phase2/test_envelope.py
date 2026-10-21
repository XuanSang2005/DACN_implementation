"""Synthetic candidate envelopes. No fixture represents a real committed run."""

import copy
from decimal import Decimal

import pytest

from dacn_s01.codec import parse_json, serialize_json
from dacn_s01.envelope import EnvelopeInvariantError, check_envelope
from dacn_s01.errors import error, ordered_errors, pointer
from dacn_s01.schema_resource import SCHEMA_SHA256


@pytest.fixture
def candidate(payload):
    return {
        "output_contract_version": "0.1.0-draft.2", "status": "validated", "result_kind": "new_spec",
        "run": {"run_id": "synthetic-run", "received_at": "2026-10-13T10:00:00.000Z",
                "completed_at": "2026-10-13T10:00:01.001Z", "validator_version": "synthetic-test-only",
                "input_schema_sha256": SCHEMA_SHA256,
                "request": {"mode": "create", "spec_id": None, "base_revision": None},
                "source": {"source_id": "synthetic-source", "kind": "json_file", "label": None},
                "input_version": {"origin": "explicit", "resolved": "1.0.0"}, "normalizations": [],
                "validation": {"checks": {"parse": "passed", "schema": "passed", "cross_field": "passed", "revision": "passed"}, "errors": []}},
        "snapshot": {"spec_id": "synthetic-spec", "revision": 1, "snapshot_id": "synthetic-snapshot",
                     "parent_snapshot_id": None, "created_by_run_id": "synthetic-run", "origin_source_id": "synthetic-source", "input": payload},
        "handoff": {"eligible_for_s02": True, "snapshot_id": "synthetic-snapshot"},
    }


def failure(candidate, result):
    candidate.update(status=result.outcome, result_kind=None, snapshot=None,
                     handoff={"eligible_for_s02": False, "snapshot_id": None})
    candidate["run"].update(input_version=result.input_version, normalizations=result.normalizations,
                            input_schema_sha256=result.input_schema_sha256,
                            validation={"checks": result.checks, "errors": result.errors})
    return candidate


@pytest.mark.parametrize("kind", ["new_spec", "new_revision", "unchanged"])
def test_synthetic_candidates_and_codec_roundtrip(candidate, kind):
    if kind != "new_spec":
        candidate["result_kind"] = kind
        candidate["run"]["request"] = {"mode": "update", "spec_id": "synthetic-spec", "base_revision": 1}
        if kind == "new_revision":
            candidate["snapshot"]["revision"] = 2
            candidate["snapshot"]["parent_snapshot_id"] = "earlier-snapshot"
        else:
            candidate["snapshot"]["created_by_run_id"] = "earlier-run"
            candidate["snapshot"]["origin_source_id"] = "earlier-source"
    saved = copy.deepcopy(candidate)
    assert check_envelope(candidate) is None
    assert check_envelope(parse_json(serialize_json(candidate))) is None
    assert candidate == saved


@pytest.mark.parametrize("phase", ["parse", "schema", "cross_field", "system"])
def test_real_input_errors_can_populate_failure_candidate(candidate, payload, submit, phase):
    from dacn_s01.validation import validate_input
    if phase == "parse":
        result = validate_input(b'{"x":1,"x":2}')
    elif phase == "system":
        result = validate_input(b'1e9999999999999999999999999999999')
    else:
        if phase == "schema":
            del payload["title"]
        else:
            payload["constraints"][0]["id"] = "R"
        result = submit(payload)
    envelope = failure(candidate, result)
    assert check_envelope(envelope) is None
    envelope["handoff"]["eligible_for_s02"] = True
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(envelope)


def test_legacy_failure_preserves_normalization_and_no_snapshot(candidate, payload, submit):
    del payload["schema_version"], payload["actors"]
    result = submit(payload)
    envelope = failure(candidate, result)
    check_envelope(envelope)
    assert envelope["snapshot"] is None and len(envelope["run"]["normalizations"]) == 1


@pytest.mark.parametrize("code,details", [("PROCESSING_FAILED", {"reason": "Synthetic tool fault"}),
                                        ("PERSISTENCE_FAILED", {"reason": "Synthetic persistence fault; no DB used"})])
def test_system_failure_after_all_checks_passed(candidate, code, details):
    candidate.update(status="failed", result_kind=None, snapshot=None,
                     handoff={"eligible_for_s02": False, "snapshot_id": None})
    candidate["run"]["validation"]["errors"] = [error(code, "system", None, "Synthetic fault", details, target="system")]
    check_envelope(candidate)
    candidate["status"] = "rejected"
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


@pytest.mark.parametrize("changes", [
    {"status": "rejected"}, {"status": "failed"}, {"status": "pending"},
    {"output_contract_version": "0.1.0-draft.1"}, {"result_kind": "unchanged"},
    {"snapshot": None}, {"extra": "no new fields"},
    {"handoff": {"eligible_for_s02": 1, "snapshot_id": "synthetic-snapshot"}},
    {"handoff": {"eligible_for_s02": True, "snapshot_id": "wrong"}},
    {"handoff": {"eligible_for_s02": False, "snapshot_id": None}},
])
def test_envelope_mutations_rejected(candidate, changes):
    candidate.update(changes)
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


@pytest.mark.parametrize("field,bad", [("request", None), ("input_schema_sha256", "0" * 64),
    ("validator_version", ""), ("run_id", 42), ("completed_at", "2026-10-13T09:59:00.000Z"),
    ("received_at", "2026-13-13T10:00:00.000Z"), ("received_at", "2026-10-13T10:00:00Z"),
    ("normalizations", [{"operation": "trim"}]), ("input_version", {"origin": "unresolved", "resolved": None}),
    ("source", {"source_id": "src", "kind": "guess", "label": None})])
def test_run_mutations_rejected(candidate, field, bad):
    candidate["run"][field] = bad
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


@pytest.mark.parametrize("field,bad", [("revision", True), ("revision", Decimal("1.5")), ("revision", 0),
    ("revision", "1"), ("revision", 2), ("parent_snapshot_id", "self"),
    ("created_by_run_id", "different"), ("origin_source_id", "different"), ("spec_id", "")])
def test_snapshot_mutations_rejected(candidate, field, bad):
    candidate["snapshot"][field] = bad
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


def test_snapshot_input_cannot_rely_on_legacy_default_or_bad_requirements(candidate):
    del candidate["snapshot"]["input"]["schema_version"]
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)
    candidate["snapshot"]["input"]["schema_version"] = "1.0.0"
    candidate["snapshot"]["input"]["actors"] = []
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


@pytest.mark.parametrize("checks", [
    {"parse": "passed", "schema": "passed", "cross_field": "passed", "revision": "not_run"},
    {"parse": "failed", "schema": "passed", "cross_field": "passed", "revision": "passed"},
    {"parse": "not_run", "schema": "passed", "cross_field": "passed", "revision": "passed"},
])
def test_no_validated_before_revision_check(candidate, checks):
    candidate["run"]["validation"]["checks"] = checks
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


@pytest.mark.parametrize("change", ["sort", "duplicate", "target", "stage", "details", "related", "extra", "pointer"])
def test_error_invariants(candidate, payload, submit, change):
    del payload["title"], payload["context"]
    envelope = failure(candidate, submit(payload))
    check_envelope(envelope)
    errors = envelope["run"]["validation"]["errors"]
    if change == "sort": errors.reverse()
    elif change == "duplicate": errors.append(copy.deepcopy(errors[-1]))
    elif change == "target": errors[0]["target"] = "request"
    elif change == "stage": errors[0]["stage"] = "cross_field"
    elif change == "details": errors[0]["details"] = {"actual": None}
    elif change == "related": errors[0]["related_pointers"] = ["/z", "/a"]
    elif change == "extra": errors[0]["blocking"] = True
    elif change == "pointer": errors[0]["pointer"] = "/bad~2escape"
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(envelope)


@pytest.mark.parametrize("field", ["base_revision", "spec_id"])
def test_routing_checked_for_validated_candidate(candidate, field):
    candidate["run"]["request"][field] = 1 if field == "base_revision" else "spec"
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


def test_stale_base_and_unchanged_provenance_invariants(candidate):
    candidate["result_kind"] = "unchanged"
    candidate["run"]["request"] = {"mode": "update", "spec_id": "synthetic-spec", "base_revision": 1}
    # Cannot replace reused snapshot origin with current run/source.
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)
    candidate["snapshot"].update(created_by_run_id="old-run", origin_source_id="old-source")
    check_envelope(candidate)
    candidate["run"]["request"]["base_revision"] = 2
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)


def test_contract_pointer_and_error_sort_oracle():
    assert pointer(()) == ""
    assert pointer(("a~/b", 0, "")) == "/a~0~1b/0/"
    a = error("MISSING_FIELD", "schema", "/b", "Missing", {"field": "b"})
    b = error("INVALID_JSON", "parse", None, "Parse", {"reason": "syntax"})
    c = error("MISSING_FIELD", "schema", "/a", "Missing", {"field": "a"})
    assert ordered_errors([a, c, b, a]) == [b, c, a]


def test_no_business_review_fields(candidate):
    candidate["snapshot"]["business_confirmed"] = True
    with pytest.raises(EnvelopeInvariantError):
        check_envelope(candidate)
