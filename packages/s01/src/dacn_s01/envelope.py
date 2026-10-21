"""Local structural/invariant checks for draft.2 envelopes.

This is NOT a commit receipt or an S02 consumer. It cannot prove a snapshot or
source exists, authenticate the producer, or authorize handoff. Persistence and
trusted lookup are phase 3. No successful envelope is built/emitted here.
"""

from datetime import datetime
import re

from .codec import CodecError, JSONValue, serialize_json
from .errors import STAGES, ordered_errors
from .schema_resource import INPUT_VERSION, PROFILE_VERSION, SCHEMA_SHA256
from .validation import METRICS, NORMALIZATION, is_integer, validate_input


class EnvelopeInvariantError(ValueError):
    """An envelope contradicts the output contract; never an input rejection."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise EnvelopeInvariantError(reason)


def _keys(value, names, label):
    _require(type(value) is dict and set(value) == set(names), f"{label}: incorrect fields")


def _text(value):
    return type(value) is str and len(value) > 0


def _positive_integer(value):
    return is_integer(value) and value >= 1


def _pointer(value):
    return type(value) is str and (value == "" or value.startswith("/")) and re.search(r"~(?![01])", value) is None


def _timestamp(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z", value) is not None,
             "Timestamp must be UTC with millisecond precision")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise EnvelopeInvariantError("Invalid timestamp date/time") from exc


def _request(value):
    """Representability only; routing legality is checked on validated output."""
    if value is None:
        return
    _keys(value, ("mode", "spec_id", "base_revision"), "run.request")
    _require(value["mode"] in ("create", "update"), "Unknown request mode")
    _require(value["spec_id"] is None or _text(value["spec_id"]), "Invalid request spec ID")
    _require(value["base_revision"] is None or _positive_integer(value["base_revision"]), "Invalid request base revision")


_ERROR_STAGES = {
    "INVALID_JSON": "parse", "DUPLICATE_JSON_KEY": "parse",
    **dict.fromkeys(("MISSING_FIELD", "TYPE_MISMATCH", "EMPTY_OR_WHITESPACE",
                     "INVALID_SCHEMA_VERSION", "UNSUPPORTED_SCHEMA_VERSION", "DUPLICATE_ACTOR",
                     "DUPLICATE_METRIC", "METRIC_COUNT", "INVALID_METRIC", "INVALID_PRIORITY",
                     "UNKNOWN_FIELD", "SCHEMA_VIOLATION"), "schema"),
    "ID_SURROUNDING_WHITESPACE": "cross_field", "DUPLICATE_REQUIREMENT_ID": "cross_field",
    **dict.fromkeys(("INVALID_REQUEST", "SPEC_NOT_FOUND", "REVISION_CONFLICT"), "revision"),
    "PROCESSING_FAILED": "system", "PERSISTENCE_FAILED": "system",
}


def _details(item):
    code, data = item["code"], item["details"]
    _require(type(data) is dict, "Error details must be an object")
    if code in ("INVALID_JSON", "DUPLICATE_JSON_KEY", "PROCESSING_FAILED", "PERSISTENCE_FAILED"):
        allowed = {"reason", "byte_offset"} if item["stage"] == "parse" else {"reason"}
        _require("reason" in data and set(data) <= allowed and _text(data["reason"]), "Error reason is required")
        if "byte_offset" in data:
            _require(is_integer(data["byte_offset"]) and data["byte_offset"] >= 0, "Invalid byte offset")
    elif code in ("MISSING_FIELD", "UNKNOWN_FIELD"):
        _keys(data, ("field",), "error.details")
        _require(type(data["field"]) is str, "Invalid field name")
    elif code == "TYPE_MISMATCH":
        _keys(data, ("expected_types", "actual_type"), "error.details")
        types = {"null", "boolean", "number", "integer", "string", "array", "object"}
        _require(type(data["expected_types"]) is list and bool(data["expected_types"])
                 and all(type(t) is str and t in types for t in data["expected_types"]), "Invalid expected types")
        _require(type(data["actual_type"]) is str and data["actual_type"] in types, "Invalid actual type")
    elif code in ("EMPTY_OR_WHITESPACE", "ID_SURROUNDING_WHITESPACE"):
        _keys(data, ("actual",), "error.details")
        _require(type(data["actual"]) is str, "Actual string is required")
    elif code in ("INVALID_SCHEMA_VERSION", "UNSUPPORTED_SCHEMA_VERSION"):
        _keys(data, ("actual", "supported"), "error.details")
        _require(data["supported"] == [INPUT_VERSION], "Incorrect supported versions")
    elif code in ("DUPLICATE_REQUIREMENT_ID", "DUPLICATE_ACTOR", "DUPLICATE_METRIC", "SPEC_NOT_FOUND"):
        name = {"DUPLICATE_REQUIREMENT_ID": "requirement_id", "SPEC_NOT_FOUND": "spec_id"}.get(code, "value")
        _keys(data, (name,), "error.details")
        _require(type(data[name]) is str, "Duplicate/lookup detail must be a string")
    elif code == "METRIC_COUNT":
        _keys(data, ("expected", "actual"), "error.details")
        _require(is_integer(data["expected"]) and data["expected"] == 4
                 and is_integer(data["actual"]) and data["actual"] >= 0, "Invalid metric count")
    elif code in ("INVALID_METRIC", "INVALID_PRIORITY"):
        _keys(data, ("actual", "allowed"), "error.details")
        allowed = [list(METRICS)] if code == "INVALID_METRIC" else [["must"], ["must", "should", "could", None]]
        _require(data["allowed"] in allowed, "Incorrect allowed values")
    elif code == "SCHEMA_VIOLATION":
        _keys(data, ("keyword", "schema_pointer"), "error.details")
        _require(_text(data["keyword"]) and _pointer(data["schema_pointer"]), "Invalid schema location")
    elif code == "INVALID_REQUEST":
        _require({"field", "reason"} <= set(data) <= {"field", "reason", "actual"}, "Invalid request details")
        _require(type(data["field"]) is str and _text(data["reason"]), "Invalid request reason")
    elif code == "REVISION_CONFLICT":
        _keys(data, ("expected_revision", "provided_revision"), "error.details")
        _require(all(_positive_integer(value) for value in data.values()), "Invalid conflict revisions")


def _validation(value):
    _keys(value, ("checks", "errors"), "run.validation")
    checks, errors = value["checks"], value["errors"]
    _keys(checks, STAGES[:-1], "checks")
    stopped = False
    for stage in STAGES[:-1]:
        check = checks[stage]
        _require(check in ("passed", "failed", "not_run"), "Unknown check result")
        _require(not stopped or check == "not_run", "Dependent check ran after a failed/not_run prerequisite")
        stopped = stopped or check != "passed"
    _require(type(errors) is list, "Errors must be an array")
    for item in errors:
        _keys(item, ("code", "stage", "target", "pointer", "related_pointers", "message", "details"), "Error")
        code = item["code"]
        _require(type(code) is str and code in _ERROR_STAGES, "Unknown error code")
        stage = _ERROR_STAGES[code]
        _require(item["stage"] == stage, "Incorrect error stage")
        target = "system" if stage == "system" else "request" if stage == "revision" else "input"
        _require(item["target"] == target, "Incorrect error target")
        _require(item["pointer"] is None or _pointer(item["pointer"]), "Malformed JSON Pointer")
        if stage == "parse":
            _require(item["pointer"] is None, "Parse errors require a null pointer")
        elif stage != "system":
            _require(item["pointer"] is not None, "Structural errors require a pointer")
        _require(type(item["related_pointers"]) is list and all(_pointer(p) for p in item["related_pointers"]), "Invalid related pointers")
        _require(item["related_pointers"] == sorted(set(item["related_pointers"])), "Related pointers must be sorted and unique")
        _require(_text(item["message"]), "Error message is required")
        _details(item)
        if stage != "system":
            _require(checks[stage] == "failed", "Error does not match failed check")
        if code in ("DUPLICATE_REQUIREMENT_ID", "DUPLICATE_ACTOR", "DUPLICATE_METRIC"):
            _require(len(item["related_pointers"]) == 1 and item["pointer"] not in item["related_pointers"], "Duplicate must reference its first occurrence")
    _require(errors == ordered_errors(errors), "Errors must be sorted and deduplicated")
    return checks, errors


def check_envelope(value: JSONValue) -> None:
    """Raise EnvelopeInvariantError on shape/invariant failure.

    Successful return checks a candidate's content, NOT persisted existence or
    trusted provenance. Reads the packaged schema, but performs no repository or
    transport I/O. Future service must check persistence/provenance separately.
    """
    try:
        serialize_json(value)  # Reject unsafe internal types/representations first.
        _check(value)
    except EnvelopeInvariantError:
        raise
    except (CodecError, KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise EnvelopeInvariantError("Envelope is not a supported, consistent JSON value") from exc


def _check(value):
    _keys(value, ("output_contract_version", "status", "result_kind", "run", "snapshot", "handoff"), "Envelope")
    _require(value["output_contract_version"] == PROFILE_VERSION, "Unsupported output contract")
    _require(value["status"] in ("validated", "rejected", "failed"), "Unknown status")
    run = value["run"]
    _keys(run, ("run_id", "received_at", "completed_at", "validator_version", "input_schema_sha256",
                "request", "source", "input_version", "normalizations", "validation"), "run")
    _require(_text(run["run_id"]) and _text(run["validator_version"]), "Run and validator identifiers required")
    _require(_timestamp(run["completed_at"]) >= _timestamp(run["received_at"]), "Run completes before receipt")
    sha = run["input_schema_sha256"]
    _require(sha is None or (type(sha) is str and re.fullmatch("[0-9a-f]{64}", sha) is not None), "Invalid schema digest")
    _request(run["request"])
    source = run["source"]
    _keys(source, ("source_id", "kind", "label"), "run.source")
    _require(_text(source["source_id"]) and source["kind"] in ("json_file", "api", "form"), "Invalid source")
    _require(source["label"] is None or type(source["label"]) is str, "Invalid source label")
    version = run["input_version"]
    _keys(version, ("origin", "resolved"), "input_version")
    _require(version["origin"] in ("explicit", "legacy_default", "unresolved"), "Invalid version origin")
    expected_version = None if version["origin"] == "unresolved" else INPUT_VERSION
    _require(version["resolved"] == expected_version, "Incorrect version resolution")
    _require(run["normalizations"] == ([NORMALIZATION] if version["origin"] == "legacy_default" else []), "Unauthorized/missing normalization")
    checks, errors = _validation(run["validation"])
    if checks["parse"] != "passed":
        _require(version["origin"] == "unresolved", "Unparsed input cannot have a resolved version")
    if checks["schema"] == "passed":
        _require(version["resolved"] == INPUT_VERSION and sha == SCHEMA_SHA256, "Schema passed without supported version/artifact")
    _keys(value["handoff"], ("eligible_for_s02", "snapshot_id"), "handoff")
    handoff = value["handoff"]
    _require(type(handoff["eligible_for_s02"]) is bool, "Handoff eligibility must be boolean")
    if value["status"] != "validated":
        _require(bool(errors), "Failure requires errors")
        _require(value["snapshot"] is None and value["result_kind"] is None, "Failure must not expose any snapshot/result")
        _require(handoff["eligible_for_s02"] is False and handoff["snapshot_id"] is None, "Failure cannot hand off")
        has_system = any(item["stage"] == "system" for item in errors)
        _require(has_system == (value["status"] == "failed"), "Rejected/failed classification contradicts errors")
        return
    _require(not errors and all(c == "passed" for c in checks.values()), "Validated requires all checks passed with no errors")
    request = run["request"]
    _require(request is not None, "Validated requires a request")
    snapshot = value["snapshot"]
    _keys(snapshot, ("spec_id", "revision", "snapshot_id", "parent_snapshot_id", "created_by_run_id", "origin_source_id", "input"), "snapshot")
    for name in ("spec_id", "snapshot_id", "created_by_run_id", "origin_source_id"):
        _require(_text(snapshot[name]), f"Invalid snapshot {name}")
    revision = snapshot["revision"]
    _require(_positive_integer(revision), "Invalid snapshot revision")
    parent = snapshot["parent_snapshot_id"]
    _require(parent is None if revision == 1 else _text(parent), "Parent does not match revision")
    _require(parent != snapshot["snapshot_id"], "Snapshot cannot parent itself")
    _require(handoff["eligible_for_s02"] is True and handoff["snapshot_id"] == snapshot["snapshot_id"], "Handoff does not match snapshot")
    payload = snapshot["input"]
    _require(type(payload) is dict and payload.get("schema_version") == INPUT_VERSION, "Snapshot must contain explicit input version")
    _require(validate_input(serialize_json(payload)).outcome == "passed", "Snapshot input violates the input contract")
    kind = value["result_kind"]
    _require(kind in ("new_spec", "new_revision", "unchanged"), "Unknown validated result kind")
    if kind == "new_spec":
        _require(request == {"mode": "create", "spec_id": None, "base_revision": None}
                 and revision == 1, "new_spec requires create and revision 1")
    else:
        _require(request["mode"] == "update" and request["spec_id"] == snapshot["spec_id"]
                 and _positive_integer(request["base_revision"]), "Update routing does not match snapshot")
        expected = int(request["base_revision"]) + (1 if kind == "new_revision" else 0)
        _require(revision == expected, "Snapshot revision does not match request/result")
    if kind == "unchanged":
        _require(snapshot["created_by_run_id"] != run["run_id"] and snapshot["origin_source_id"] != source["source_id"], "Unchanged must retain earlier run/source provenance")
    else:
        _require(snapshot["created_by_run_id"] == run["run_id"] and snapshot["origin_source_id"] == source["source_id"], "New snapshot provenance must match current run/source")
