"""P3-F1: synthetic byte-level inputs, real temporary SQLite, literal oracles.

No surrogate repair is permitted. The original bytes and the safe failure
envelope are different artifacts; neither substitutes for the other.
"""

from copy import deepcopy
from decimal import Decimal
import sqlite3

import pytest

from dacn_s01.codec import ProcessingError, parse_json, serialize_json
from dacn_s01.envelope import check_envelope
from dacn_s01.repository import Repository
from dacn_s01.service import Service

CREATE = {"mode": "create", "spec_id": None, "base_revision": None}
PAIR = "\ud800\udc00"
PAIR_BYTES = b"\xed\xa0\x80\xed\xb0\x80"
LOCATIONS = ("priority", "schema_version", "unknown_key")


def at_location(payload, location, text):
    data = deepcopy(payload)
    if location == "priority":
        data["functional_requirements"][0]["priority"] = text
    elif location == "unknown_key":
        data[text] = None
    else:
        data[location] = text
    return data


def literal_pair_raw(payload, location):
    encoded = serialize_json(at_location(payload, location, "PAIR_MARKER"))
    assert encoded.count(b"PAIR_MARKER") == 1
    return b" \n" + encoded.replace(b"PAIR_MARKER", PAIR_BYTES) + b"\n "


def rows(repository):
    # Independent SQL oracle, not repository decision or comparator functions.
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        return {table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("sources", "runs", "snapshots", "specs", "schema_artifacts")}


def assert_failed(output, codes):
    assert output["status"] == "failed"
    assert output["snapshot"] is None and output["result_kind"] is None
    assert output["handoff"] == {"eligible_for_s02": False, "snapshot_id": None}
    assert [e["code"] for e in output["run"]["validation"]["errors"]] == codes
    for issue in output["run"]["validation"]["errors"]:
        if issue["stage"] == "system":
            assert issue["target"] == "system" and issue["pointer"] is None
            assert issue["related_pointers"] == []
            assert set(issue["details"]) == {"reason"}
    assert parse_json(serialize_json(output)) == output
    check_envelope(output)


def assert_archived(repository, output, raw, context):
    reopened = Repository(repository.path)
    assert reopened.get_run(output["run"]["run_id"]) == output
    assert reopened.get_request(output["run"]["run_id"]) == context
    assert reopened.get_source(output["run"]["source"]["source_id"]) == raw
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute("SELECT typeof(raw_input), raw_input FROM sources WHERE source_id=?",
                                  (output["run"]["source"]["source_id"],)).fetchone() == ("blob", raw)
    # Repeated lookup must keep timestamps/build/source and must not create runs.
    before = rows(repository)
    assert reopened.get_run(output["run"]["run_id"]) == output
    assert rows(repository) == before


@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.parametrize("mode", ["create", "update", "invalid_request"])
def test_unencodable_diagnostic_archives_controlled_failure(payload, repository, location, mode):
    head = None
    context = CREATE
    if mode == "update":
        head = Service(repository).submit(serialize_json(payload), CREATE)["snapshot"]
        context = {"mode": "update", "spec_id": head["spec_id"], "base_revision": 1}
    elif mode == "invalid_request":
        context = {"bad": Decimal("12345678901234567890.12345678901234567890")}
    raw = literal_pair_raw(payload, location)
    assert parse_json(raw) == at_location(payload, location, PAIR)
    # Existing codec safeguard remains the authority: two code points must not
    # silently become the single U+10000 scalar when re-encoded as ASCII JSON.
    with pytest.raises(ProcessingError):
        serialize_json(parse_json(raw))
    output = Service(repository).submit(raw, context, run_id="failure-known-in-advance")
    assert_failed(output, ["PROCESSING_FAILED"])
    assert output["run"]["validation"]["checks"] == {
        "parse": "passed", "schema": "failed", "cross_field": "not_run", "revision": "not_run"}
    assert output["run"]["request"] == (None if mode == "invalid_request" else context)
    assert output["run"]["normalizations"] == []
    assert_archived(repository, output, raw, context)
    assert rows(repository) == {"sources": 1 + bool(head), "runs": 1 + bool(head),
                               "snapshots": int(bool(head)), "specs": int(bool(head)),
                               "schema_artifacts": int(bool(head) or location != "schema_version")}
    if head:
        assert Repository(repository.path).get_head(head["spec_id"]) == head
        assert Repository(repository.path).get_snapshot(head["snapshot_id"]) == head


@pytest.mark.parametrize("location", ["priority", "unknown_key"])
def test_representable_errors_survive_beside_unencodable_diagnostic(payload, repository, location):
    del payload["context"]
    raw = literal_pair_raw(payload, location)
    output = Service(repository).submit(raw, CREATE)
    assert_failed(output, ["MISSING_FIELD", "PROCESSING_FAILED"])
    issue = output["run"]["validation"]["errors"][0]
    assert {k: issue[k] for k in ("stage", "target", "pointer", "related_pointers", "details")} == {
        "stage": "schema", "target": "input", "pointer": "/context",
        "related_pointers": [], "details": {"field": "context"}}
    assert_archived(repository, output, raw, CREATE)


@pytest.mark.parametrize("location,code", [
    ("priority", "INVALID_PRIORITY"), ("schema_version", "UNSUPPORTED_SCHEMA_VERSION"),
    ("unknown_key", "UNKNOWN_FIELD")])
@pytest.mark.parametrize("text", ["urgent", "\U00010000", "\ud800", "\ud800x\udc00"],
                         ids=["ordinary", "astral", "lone-surrogate", "separated-surrogates"])
def test_representable_diagnostics_remain_exact_rejections(payload, repository, location, code, text):
    raw = serialize_json(at_location(payload, location, text))
    output = Service(repository).submit(raw, CREATE)
    assert output["status"] == "rejected"
    assert output["snapshot"] is None and output["handoff"]["eligible_for_s02"] is False
    errors = output["run"]["validation"]["errors"]
    assert [e["code"] for e in errors] == [code]
    assert errors[0]["details"]["field" if location == "unknown_key" else "actual"] == text
    if location == "unknown_key":
        assert errors[0]["pointer"] == "/" + text
    check_envelope(parse_json(serialize_json(output)))
    assert_archived(repository, output, raw, CREATE)


@pytest.mark.parametrize("wire", ["literal-pair", "escaped-pair", "astral-utf8"])
def test_title_controls_do_not_change_codec_policy(payload, repository, wire):
    raw = literal_pair_raw(payload, "title")
    if wire == "escaped-pair":
        raw = raw.replace(PAIR_BYTES, b"\\ud800\\udc00")
    elif wire == "astral-utf8":
        raw = raw.replace(PAIR_BYTES, b"\xf0\x90\x80\x80")
    output = Service(repository).submit(raw, CREATE)
    if wire == "literal-pair":
        assert_failed(output, ["PROCESSING_FAILED"])
    else:
        assert output["status"] == "validated"
        assert output["snapshot"]["input"]["title"] == "\U00010000"
    assert_archived(repository, output, raw, CREATE)


@pytest.mark.parametrize("point", ["before_begin", "after_source_insert", "after_commit"])
def test_safe_failure_under_archive_faults(payload, repository, point):
    events = []

    def hook(actual, connection):
        if actual == point:
            events.append(actual)
            raise OSError("synthetic archive fault")

    raw = literal_pair_raw(payload, "priority")
    faulty = Repository(repository.path, _hook=hook)
    output = Service(faulty).submit(raw, CREATE, run_id="failure-with-archive-fault")
    # Before BEGIN fails independently of serialization; retain both causes.
    expected = ["PERSISTENCE_FAILED", "PROCESSING_FAILED"] if point == "before_begin" else ["PROCESSING_FAILED"]
    assert_failed(output, expected)
    assert events == [point] * (2 if point == "before_begin" else 1)
    if point == "after_commit":
        # Lost acknowledgement: reconcile the committed failed run on a fresh
        # connection. This is fault injection, not a process crash/power loss.
        assert_archived(repository, output, raw, CREATE)
        assert rows(repository) == dict(sources=1, runs=1, snapshots=0, specs=0, schema_artifacts=1)
    else:
        assert Repository(repository.path).get_run("failure-with-archive-fault") is None
        assert rows(repository) == dict(sources=0, runs=0, snapshots=0, specs=0, schema_artifacts=0)
