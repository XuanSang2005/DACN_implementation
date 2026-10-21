import sqlite3

import pytest

from dacn_s01.codec import parse_json, serialize_json
from dacn_s01.repository import IntegrityError, Repository
from dacn_s01.service import Service


def test_new_lookup_consistency_guards(runner, payload):
    runner.at_state("init")
    repo = Repository(runner.state / "s01.sqlite3")
    original = Service(repo).submit(serialize_json(payload), {"mode": "create", "spec_id": None, "base_revision": None})
    snapshot = original["snapshot"]
    assert repo.get_snapshot_revision(snapshot["spec_id"], 1) == snapshot
    assert repo.list_runs(snapshot["spec_id"]) == [original]
    assert repo.get_snapshot_revision(snapshot["spec_id"], 2) is None
    assert repo.list_runs("absent") == []
    # Corrupt data in a synthetic DB while restoring the exact trigger DDL.
    # Read-side guards must reject it; do not manufacture a head-based fallback.
    with sqlite3.connect(repo.path) as con:
        trigger = con.execute("SELECT sql FROM sqlite_master WHERE name='runs_no_update'").fetchone()[0]
        con.execute("DROP TRIGGER runs_no_update")
        edited = parse_json(serialize_json(original))
        edited["run"]["source"]["label"] = "corrupted"
        con.execute("UPDATE runs SET envelope_json=?", (serialize_json(edited).decode(),))
        con.execute(trigger)
    with pytest.raises(IntegrityError): repo.get_snapshot_revision(snapshot["spec_id"], 1)
    with pytest.raises(IntegrityError): repo.list_runs(snapshot["spec_id"])
    runner.at_state("show-snapshot", "--spec-id", snapshot["spec_id"], "--revision", "1", expected=3)
    runner.at_state("list-runs", "--spec-id", snapshot["spec_id"], expected=3)
