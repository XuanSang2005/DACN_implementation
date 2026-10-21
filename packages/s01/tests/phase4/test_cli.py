from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from dacn_s01.codec import parse_json, serialize_json
from dacn_s01.repository import Repository


def counts(runner):
    with sqlite3.connect(runner.state / "s01.sqlite3") as con:
        return {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("runs", "sources", "snapshots", "specs")}


def submit(runner, source, receipt, *routing, expected=0, **kwargs):
    return runner.at_state("submit", "--input", source, "--receipt", receipt, *routing, expected=expected, **kwargs)


def test_lifecycle_lookup_export_and_real_module_entrypoint(runner, payload):
    # This additional invocation uses literal python -m, with no harness wrapper.
    real = subprocess.run([sys.executable, "-B", "-m", "dacn_s01", "--state-dir", str(runner.state), "init"],
                          cwd=runner.cwd, env=runner.env, capture_output=True, timeout=20)
    assert real.returncode == 0 and real.stderr == b""
    assert parse_json(real.stdout)["state_dir"] == str(runner.state)
    source = runner.input(payload)
    before = source.read_bytes()
    r1 = runner.root / "attempt1.json"
    result = submit(runner, source, r1, "--mode", "create")
    assert result.stderr == b""
    a = parse_json(result.stdout)
    s1 = a["snapshot"]
    receipt = parse_json(r1.read_bytes())
    assert receipt == {"receipt_version": "1", "run_id": a["run"]["run_id"], "state_dir": str(runner.state)}
    assert a["snapshot"]["input"] == payload
    routing = ("--mode", "update", "--spec-id", s1["spec_id"], "--base-revision", "1")
    b = parse_json(submit(runner, source, runner.root / "attempt2.json", *routing).stdout)
    assert b["result_kind"] == "unchanged" and b["snapshot"] == s1
    edited = deepcopy(payload)
    edited["functional_requirements"][0]["priority"] = "should"
    edit_source = runner.input(edited, "edit.json")
    c = parse_json(submit(runner, edit_source, runner.root / "attempt3.json", *routing).stdout)
    assert c["result_kind"] == "new_revision" and c["snapshot"]["parent_snapshot_id"] == s1["snapshot_id"]
    assert c["snapshot"]["revision"] == 2
    stale = parse_json(submit(runner, edit_source, runner.root / "stale.json", *routing, expected=2).stdout)
    error = stale["run"]["validation"]["errors"][0]
    assert (error["code"], error["stage"], error["pointer"], error["details"]) == (
        "REVISION_CONFLICT", "revision", "/base_revision", {"expected_revision": 2, "provided_revision": 1})
    assert parse_json(runner.run("show-run", "--receipt", r1).stdout) == a
    assert parse_json(runner.at_state("show-run", "--run-id", b["run"]["run_id"]).stdout) == b
    assert parse_json(runner.at_state("show-snapshot", "--snapshot-id", s1["snapshot_id"]).stdout) == s1
    old_export = runner.root / "old snapshot.json"
    assert parse_json(runner.at_state("show-snapshot", "--spec-id", s1["spec_id"], "--revision", "1",
                                     "--output", old_export).stdout) == s1
    assert parse_json(old_export.read_bytes()) == s1
    listed = parse_json(runner.at_state("list-runs", "--spec-id", s1["spec_id"]).stdout)
    assert {v["run"]["run_id"] for v in listed} == {v["run"]["run_id"] for v in (a, b, c, stale)}
    assert listed == sorted(listed, key=lambda v: (v["run"]["received_at"], v["run"]["run_id"]))
    raw_export = runner.root / "original bytes.bin"
    exported = runner.at_state("show-source", "--source-id", a["run"]["source"]["source_id"], "--output", raw_export)
    assert exported.stdout == exported.stderr == b"" and raw_export.read_bytes() == before
    assert counts(runner) == dict(runs=4, sources=4, snapshots=2, specs=1)
    assert source.read_bytes() == before and source.stat().st_mode & 0o222 == 0
    print("PHASE4_EVIDENCE " + json.dumps({"case": "lifecycle", "backend": runner.backend,
        "final_counts": counts(runner), "historical_revision": 1, "head_revision": 2,
        "raw_sha256": hashlib.sha256(before).hexdigest()}))


@pytest.mark.parametrize("flags,code,pointer", [
    (["--mode", "bad"], "INVALID_REQUEST", "/mode"),
    (["--mode", "update"], "INVALID_REQUEST", "/base_revision"),
    (["--mode", "create", "--spec-id", "x"], "INVALID_REQUEST", "/spec_id"),
    (["--mode", "update", "--spec-id", "missing", "--base-revision", "1"], "SPEC_NOT_FOUND", "/spec_id"),
    (["--mode", "update", "--spec-id", "x", "--base-revision", "1.5"], "INVALID_REQUEST", "/base_revision"),
    (["--mode", "create", "--base-revision", "0"], "INVALID_REQUEST", "/base_revision"),
])
def test_request_errors_go_through_service(runner, payload, flags, code, pointer):
    runner.at_state("init")
    source = runner.input(payload)
    result = parse_json(submit(runner, source, runner.root / "r.json", *flags, expected=2).stdout)
    assert result["status"] == "rejected" and result["snapshot"] is None
    issue = result["run"]["validation"]["errors"][0]
    assert (issue["code"], issue["stage"], issue["target"], issue["pointer"]) == (code, "revision", "request", pointer)
    assert counts(runner) == dict(runs=1, sources=1, snapshots=0, specs=0)
    if code == "SPEC_NOT_FOUND":
        assert parse_json(runner.at_state("list-runs", "--spec-id", "missing").stdout) == [result]


@pytest.mark.parametrize("args", [[], ["no-such-command"], ["submit", "--mode", "create"],
    ["show-run"], ["show-run", "--run-id", "a", "--receipt", "b"],
    ["show-snapshot", "--spec-id", "a"], ["show-snapshot", "--snapshot-id", "a", "--revision", "1"],
    ["show-snapshot", "--spec-id", "a", "--revision", "1.5"],
    ["submit", "--mode", "update", "--base-revision", "oops", "--input", "x", "--receipt", "y"]])
def test_usage_is_64_without_intake(runner, args):
    result = runner.at_state(*args, expected=64)
    assert result.stdout == b"" and b"Usage error" in result.stderr
    assert not runner.state.exists()


@pytest.mark.parametrize("case,expected,code", [("parse", 2, "INVALID_JSON"), ("duplicate-key", 2, "DUPLICATE_JSON_KEY"),
    ("invalid-priority", 2, "INVALID_PRIORITY"), ("p3-priority", 3, "PROCESSING_FAILED"),
    ("p3-version", 3, "PROCESSING_FAILED"), ("p3-key", 3, "PROCESSING_FAILED"), ("unknown", 2, "UNKNOWN_FIELD")])
def test_invalid_input_and_p3f1_through_cli(runner, payload, case, expected, code):
    runner.at_state("init")
    if case in ("invalid-priority", "p3-priority"):
        payload["functional_requirements"][0]["priority"] = "MARKER"
    if case == "p3-version": payload["schema_version"] = "MARKER"
    if case in ("p3-key", "unknown"): payload["MARKER"] = None
    raw = serialize_json(payload)
    if case == "parse": raw = b" \n{"
    if case == "duplicate-key": raw = b'{"x":1,"x":2}'
    if case.startswith("p3-"): raw = raw.replace(b"MARKER", b"\xed\xa0\x80\xed\xb0\x80")
    source = runner.root / "readonly.json"
    source.write_bytes(raw); source.chmod(0o400)
    receipt = runner.root / "receipt.json"
    result = parse_json(submit(runner, source, receipt, "--mode", "create", expected=expected).stdout)
    assert result["status"] == ("failed" if expected == 3 else "rejected")
    assert result["handoff"] == {"eligible_for_s02": False, "snapshot_id": None}
    assert result["snapshot"] is None
    assert [e["code"] for e in result["run"]["validation"]["errors"]] == [code]
    assert parse_json(runner.run("show-run", "--receipt", receipt).stdout) == result  # lookup exits 0 even failed
    export = runner.root / "source.bin"
    runner.at_state("show-source", "--source-id", result["run"]["source"]["source_id"], "--output", export)
    assert export.read_bytes() == source.read_bytes() == raw


def test_exact_numbers_legacy_utf16_source_and_export(runner, payload):
    runner.at_state("init")
    del payload["schema_version"]
    value = {"large": Decimal("9" * 5001), "fraction": Decimal("0.123456789012345678901234567890123456789"),
             "minus_zero": Decimal("-0.00"), "unknown": None, "bool": True, "text": " e\u0301 "}
    payload["constraints"][0]["constraint"]["value"] = value
    raw = (" \n" + serialize_json(payload).decode() + "\n").encode("utf-16")
    source = runner.root / "legacy.json"
    source.write_bytes(raw); source.chmod(0o400)
    output = runner.root / "result.json"
    result = submit(runner, source, runner.root / "receipt", "--mode", "create", "--output", output)
    assert result.stdout == output.read_bytes()
    envelope = parse_json(result.stdout)
    stored = envelope["snapshot"]["input"]["constraints"][0]["constraint"]["value"]
    for key in ("large", "fraction", "minus_zero"):
        assert stored[key].as_tuple() == value[key].as_tuple()
    assert stored == value and envelope["run"]["input_version"] == {"origin": "legacy_default", "resolved": "1.0.0"}
    assert envelope["snapshot"]["input"]["schema_version"] == "1.0.0"
    assert Repository(runner.state / "s01.sqlite3").get_source(envelope["run"]["source"]["source_id"]) == raw


@pytest.mark.parametrize("command", [["show-run", "--run-id", "missing"],
    ["show-snapshot", "--snapshot-id", "missing"], ["show-snapshot", "--spec-id", "missing", "--revision", "1"],
    ["show-snapshot", "--spec-id", "missing", "--revision", "1e50"]])
def test_lookup_not_found(runner, command):
    runner.at_state("init")
    result = runner.at_state(*command, expected=4)
    assert result.stdout == b"" and b"does not prove" in result.stderr
    assert counts(runner)["runs"] == 0


def test_receipt_missing_run_conflict_and_no_overwrite(runner, payload):
    runner.at_state("init")
    source = runner.input(payload)
    receipt = runner.root / "receipt"
    result = submit(runner, source, receipt, "--mode", "create")
    original = receipt.read_bytes()
    again = submit(runner, source, receipt, "--mode", "create", expected=3)
    assert again.stdout == b"" and b"show-run --receipt" in again.stderr
    assert receipt.read_bytes() == original and counts(runner)["runs"] == 1
    other = runner.root / "other"
    conflict = runner.run("--state-dir", other, "show-run", "--receipt", receipt, expected=3)
    assert b"conflicts" in conflict.stderr and not other.exists()
    export = runner.root / "export"
    export.write_bytes(b"user-owned")
    runner.at_state("show-run", "--run-id", parse_json(result.stdout)["run"]["run_id"], "--output", export, expected=3)
    assert export.read_bytes() == b"user-owned"
    missing = parse_json(original); missing["run_id"] = "not-recorded"
    receipt2 = runner.root / "missing-receipt"
    receipt2.write_bytes(serialize_json(missing))
    assert b"does not prove" in runner.run("show-run", "--receipt", receipt2, expected=4).stderr


@pytest.mark.parametrize("raw", [b"{", b'{"run_id":"a","run_id":"b"}', b'[]',
    b'{"receipt_version":"2","run_id":"a","state_dir":"/tmp"}',
    b'{"receipt_version":"1","run_id":"a","state_dir":"relative"}',
    b'{"receipt_version":"1","run_id":null,"state_dir":"/tmp"}'])
def test_invalid_receipts_are_operational_errors(runner, raw):
    receipt = runner.root / "bad-receipt"
    receipt.write_bytes(raw)
    result = runner.run("show-run", "--receipt", receipt, expected=3)
    assert result.stdout == b"" and receipt.read_bytes() == raw


def test_show_source_missing_does_not_create_export(runner):
    runner.at_state("init")
    output = runner.root / "missing-source"
    result = runner.at_state("show-source", "--source-id", "absent", "--output", output, expected=4)
    assert result.stdout == b"" and not output.exists()


@pytest.mark.parametrize("legacy", [False, True])
def test_crossfield_unicode_failure_through_cli_preserves_safe_error(runner, payload, legacy):
    runner.at_state("init")
    if legacy: del payload["schema_version"]
    payload["functional_requirements"][0]["id"] = " MARKER"
    payload["functional_requirements"].append({"id": " R2", "text": "Test", "priority": None, "acceptance_criteria": []})
    raw = serialize_json(payload).replace(b"MARKER", b"\xed\xa0\x80\xed\xb0\x80")
    source = runner.root / "crossfield"
    source.write_bytes(raw); source.chmod(0o400)
    receipt = runner.root / "receipt"
    result = parse_json(submit(runner, source, receipt, "--mode", "create", expected=3).stdout)
    assert result["run"]["validation"]["checks"] == dict(parse="passed", schema="passed", cross_field="failed", revision="not_run")
    assert [e["code"] for e in result["run"]["validation"]["errors"]] == ["ID_SURROUNDING_WHITESPACE", "PROCESSING_FAILED"]
    assert result["run"]["validation"]["errors"][0]["details"] == {"actual": " R2"}
    assert result["run"]["input_version"]["origin"] == ("legacy_default" if legacy else "explicit")
    assert parse_json(runner.run("show-run", "--receipt", receipt).stdout) == result
    export = runner.root / "raw"
    runner.at_state("show-source", "--source-id", result["run"]["source"]["source_id"], "--output", export)
    assert export.read_bytes() == raw


@pytest.mark.parametrize("location", ["spec-id", "input-path"])
def test_cli_refuses_unrepresentable_operational_metadata_before_receipt(runner, payload, location):
    runner.at_state("init")
    source = runner.input(payload)
    bad_name = os.fsdecode(b"\xff")  # Real POSIX argv/filename surrogateescape, not requirements text.
    flags = ["--mode", "create"]
    argument_source = source
    if location == "spec-id":
        flags += ["--spec-id", bad_name]
    else:
        # macOS rejects creation of this filename. Exercise the invalid argv
        # directly: metadata must be rejected before attempting to open it.
        argument_source = runner.root / bad_name
    before = source.read_bytes()
    receipt = runner.root / "receipt"
    result = submit(runner, argument_source, receipt, *flags, expected=3)
    assert result.stdout == b"" and not receipt.exists()
    if location == "input-path":
        assert b"Argument cannot be represented exactly" in result.stderr
    assert source.read_bytes() == before and counts(runner)["runs"] == 0
