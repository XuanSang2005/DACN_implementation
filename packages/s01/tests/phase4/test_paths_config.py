import hashlib
import os
import sqlite3

import pytest

from dacn_s01.codec import parse_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_config_relative_paths_override_and_preservation(runner, payload):
    config_dir = runner.root / "configuration"
    config_dir.mkdir()
    dataset = config_dir / "dataset"
    dataset.mkdir()
    source = dataset / "source.json"
    from dacn_s01.codec import serialize_json
    source.write_bytes(serialize_json(payload)); source.chmod(0o400)
    config = config_dir / "s01.toml"
    config.write_text('state_dir = "from-config"\nbusy_timeout_ms = 0\ndataset_roots = ["dataset"]\n')
    config.chmod(0o400)
    before = {p: digest(p) for p in (config, source)}
    first = runner.run("--config", config, "init")
    assert parse_json(first.stdout)["state_dir"] == str(config_dir / "from-config")
    runner.run("--config", config, "--state-dir", runner.state, "init")
    result = runner.run("--config", config, "--state-dir", runner.state, "submit", "--mode", "create",
                        "--input", source, "--receipt", runner.root / "receipt")
    assert parse_json(result.stdout)["status"] == "validated"
    assert {p: digest(p) for p in before} == before
    assert list(dataset.iterdir()) == [source]


@pytest.mark.parametrize("text", ['unexpected = 1', 'busy_timeout_ms = true', 'busy_timeout_ms = -1',
    'busy_timeout_ms = 2147483648', 'dataset_roots = "wrong"', 'dataset_roots = [1]',
    'state_dir = ""', 'state_dir = 2', 'state_dir = [', 'busy_timeout_ms = 1.0', 'dataset_roots = ["absent"]'])
def test_bad_config_is_3_before_any_write(runner, text):
    config = runner.root / "bad.toml"
    config.write_text(text)
    before = config.read_bytes()
    result = runner.run("--config", config, "--state-dir", runner.state, "init", expected=3)
    assert result.stdout == b"" and not runner.state.exists()
    assert config.read_bytes() == before


def test_missing_store_or_config_does_not_initialize(runner, payload):
    assert b"No state directory" in runner.run("init", expected=3).stderr
    runner.run("--config", runner.root / "absent.toml", "init", expected=3)
    runner.at_state("show-run", "--run-id", "missing", expected=3)
    source = runner.input(payload)
    receipt = runner.root / "receipt"
    runner.at_state("submit", "--mode", "create", "--input", source, "--receipt", receipt, expected=3)
    assert not runner.state.exists() and not receipt.exists()


@pytest.mark.parametrize("kind", ["version", "structure", "foreign"])
def test_unsupported_store_not_reset(runner, kind):
    if kind != "foreign":
        runner.at_state("init")
    else:
        runner.state.mkdir()
    db = runner.state / "s01.sqlite3"
    with sqlite3.connect(db) as connection:
        if kind == "version": connection.execute("PRAGMA user_version=99")
        elif kind == "structure": connection.execute("DROP TRIGGER sources_no_update")
        else: connection.execute("CREATE TABLE private_data(value TEXT)")
    before = digest(db)
    runner.at_state("init", expected=3)
    runner.at_state("show-run", "--run-id", "anything", expected=3)
    assert digest(db) == before


@pytest.mark.parametrize("target", ["state", "receipt", "export", "symlink-parent", "db-symlink", "sidecar-symlink"])
def test_dataset_roots_guard_every_write_location(runner, payload, target):
    dataset = runner.root / "protected"
    dataset.mkdir()
    source = runner.input(payload)
    original = dataset / "original"
    original.write_bytes(b"DO NOT CHANGE"); original.chmod(0o400)
    config = runner.root / "config.toml"
    config.write_text(f'dataset_roots = ["{dataset}"]\n')
    if target == "state":
        runner.run("--config", config, "--state-dir", dataset / "state", "init", expected=3)
    else:
        runner.at_state("init")
        receipt = runner.root / "receipt"
        output = runner.root / "export"
        if target == "receipt": receipt = dataset / "receipt"
        if target == "export": output = dataset / "export"
        if target == "symlink-parent":
            alias = runner.root / "alias"
            alias.symlink_to(dataset, target_is_directory=True)
            receipt = alias / "receipt"
        if target == "db-symlink":
            (runner.state / "s01.sqlite3").unlink()
            (runner.state / "s01.sqlite3").symlink_to(original)
        if target == "sidecar-symlink":
            (runner.state / "s01.sqlite3-journal").symlink_to(original)
        result = runner.run("--config", config, "--state-dir", runner.state, "submit", "--mode", "create",
            "--input", source, "--receipt", receipt, "--output", output, expected=3)
        assert result.stdout == b"" and not receipt.exists()
    assert list(dataset.iterdir()) == [original] and original.read_bytes() == b"DO NOT CHANGE"


@pytest.mark.parametrize("alias", ["same-input", "hardlink-input", "symlink-input", "config", "receipt-output", "state-output", "dangling"])
def test_artifact_alias_and_no_clobber(runner, payload, alias):
    runner.at_state("init")
    source = runner.input(payload)
    config = runner.root / "config.toml"
    config.write_text("busy_timeout_ms = 0\n")
    receipt = runner.root / "receipt"
    output = runner.root / "output"
    if alias == "same-input": output = source
    if alias == "hardlink-input": os.link(source, output)
    if alias == "symlink-input": output.symlink_to(source)
    if alias == "config": output = config
    if alias == "receipt-output": output = receipt
    if alias == "state-output": output = runner.state / "other"
    if alias == "dangling": output.symlink_to(runner.root / "missing")
    before = (source.read_bytes(), config.read_bytes())
    runner.run("--config", config, "--state-dir", runner.state, "submit", "--mode", "create", "--input", source,
               "--receipt", receipt, "--output", output, expected=3)
    assert (source.read_bytes(), config.read_bytes()) == before
    assert not receipt.exists()
    with sqlite3.connect(runner.state / "s01.sqlite3") as con:
        assert con.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


@pytest.mark.parametrize("suffix", ["", "-journal", "-wal", "-shm"])
def test_db_hardlink_to_unknown_source_refused_even_without_dataset_config(runner, suffix):
    runner.state.mkdir()
    source = runner.root / "source"
    source.write_bytes(b"readonly original"); source.chmod(0o400)
    os.link(source, runner.state / ("s01.sqlite3" + suffix))
    runner.at_state("init", expected=3)
    assert source.read_bytes() == b"readonly original"


def test_symlink_state_and_receipt_lookup_resolve_consistently(runner, payload):
    runner.at_state("init")
    alias = runner.root / "state alias"
    alias.symlink_to(runner.state, target_is_directory=True)
    receipt = runner.root / "receipt"
    source = runner.input(payload)
    output = runner.run("--state-dir", alias, "submit", "--mode", "create", "--input", source, "--receipt", receipt)
    assert parse_json(receipt.read_bytes())["state_dir"] == str(runner.state)
    assert runner.run("--state-dir", alias, "show-run", "--receipt", receipt).stdout == output.stdout


@pytest.mark.parametrize("behavior,receipt_exists", [({"fsync_fail": 1}, False), ({"link_fail": True}, False), ({"fsync_fail": 2}, True)])
def test_receipt_flush_and_publish_failure_never_submit(runner, payload, behavior, receipt_exists):
    runner.at_state("init")
    source = runner.input(payload)
    receipt = runner.root / "receipt"
    result = runner.at_state("submit", "--mode", "create", "--input", source, "--receipt", receipt,
                             behavior=behavior, expected=3)
    assert result.stdout == b"" and b"no S01 submit started" in result.stderr
    assert receipt.exists() is receipt_exists
    assert list(runner.root.glob(".dacn-*.tmp")) == []
    with sqlite3.connect(runner.state / "s01.sqlite3") as con:
        assert con.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    if receipt_exists:
        runner.run("show-run", "--receipt", receipt, expected=4)
    import json
    print("PHASE4_EVIDENCE " + json.dumps({"case": "receipt-fault", "backend": runner.backend,
        "fault_injection": behavior, "receipt_exists": receipt_exists, "runs": 0}))


def test_real_receipt_permission_failure_has_no_commit(runner, payload):
    runner.at_state("init")
    source = runner.input(payload)
    directory = runner.root / "readonly-dir"
    directory.mkdir(mode=0o500)
    try:
        result = runner.at_state("submit", "--mode", "create", "--input", source, "--receipt", directory / "receipt", expected=3)
        assert result.stdout == b"" and list(directory.iterdir()) == []
        with sqlite3.connect(runner.state / "s01.sqlite3") as con:
            assert con.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    finally:
        directory.chmod(0o700)


@pytest.mark.parametrize("fsync_call,export_exists", [(3, False), (4, True)])
def test_export_fsync_failure_preserves_committed_run(runner, payload, fsync_call, export_exists):
    runner.at_state("init")
    source = runner.input(payload)
    receipt, export = runner.root / "receipt", runner.root / "export"
    result = runner.at_state("submit", "--mode", "create", "--input", source, "--receipt", receipt,
        "--output", export, behavior={"fsync_fail": fsync_call}, expected=3)
    assert result.stdout == b"" and b"result delivery" in result.stderr
    assert export.exists() is export_exists
    recovered = runner.run("show-run", "--receipt", receipt)
    assert parse_json(recovered.stdout)["status"] == "validated"
    if export_exists: assert export.read_bytes() == recovered.stdout
    with sqlite3.connect(runner.state / "s01.sqlite3") as con:
        assert con.execute("SELECT count(*) FROM runs").fetchone()[0] == 1
    assert list(runner.root.glob(".dacn-*.tmp")) == []


def test_config_zero_timeout_with_real_writer_lock(runner, payload):
    import subprocess
    runner.at_state("init")
    source = runner.input(payload)
    config = runner.root / "timeout.toml"
    config.write_text("busy_timeout_ms = 0\n")
    receipt = runner.root / "receipt"
    command, evidence = runner.command(["--config", config, "--state-dir", runner.state, "submit", "--mode", "create",
        "--input", source, "--receipt", receipt])
    connection = sqlite3.connect(runner.state / "s01.sqlite3", autocommit=True)
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = subprocess.run(command, cwd=runner.cwd, env=runner.env, capture_output=True, timeout=5)
        assert result.returncode == 3
        value = parse_json(result.stdout)
        assert value["status"] == "failed"
        assert [e["code"] for e in value["run"]["validation"]["errors"]] == ["PERSISTENCE_FAILED"]
        assert receipt.exists()
    finally:
        connection.execute("ROLLBACK")
        connection.close()
    runner.checked_evidence(evidence)
    runner.run("show-run", "--receipt", receipt, expected=4)


@pytest.mark.parametrize("destination", ["state", "receipt", "export"])
def test_existing_dataset_ancestor_identity_blocks_case_alias(runner, payload, destination):
    # The delivery platform is case-insensitive macOS. On a case-sensitive
    # filesystem use an explicit directory alias to retain the identity test.
    dataset = runner.root / "ProtectedCase"
    dataset.mkdir()
    alias = dataset.with_name("protectedcase")
    case_alias = alias.exists()
    if not case_alias:
        alias.symlink_to(dataset, target_is_directory=True)
    assert alias.samefile(dataset)
    config = runner.root / "roots.toml"
    config.write_text('dataset_roots = ["ProtectedCase"]\n')
    if destination == "state":
        runner.run("--config", config, "--state-dir", alias / "state", "init", expected=3)
    else:
        runner.at_state("init")
        source = runner.input(payload)
        receipt = alias / "receipt" if destination == "receipt" else runner.root / "receipt"
        output = alias / "export" if destination == "export" else runner.root / "export"
        runner.run("--config", config, "--state-dir", runner.state, "submit", "--mode", "create", "--input", source,
                   "--receipt", receipt, "--output", output, expected=3)
        assert not receipt.exists() and not output.exists()
    assert list(dataset.iterdir()) == []
    import json
    print("PHASE4_EVIDENCE " + json.dumps({"case": "dataset-ancestor-identity", "backend": runner.backend,
        "destination": destination, "actual_case_alias": case_alias, "dataset_unchanged": True}))


def test_same_store_case_alias_agrees_with_receipt_and_blocks_export_inside_state(runner, payload):
    runner.at_state("init")
    alias = runner.state.with_name(runner.state.name.swapcase())
    if not alias.exists():
        alias.symlink_to(runner.state, target_is_directory=True)
    source = runner.input(payload)
    receipt = runner.root / "receipt"
    result = runner.at_state("submit", "--mode", "create", "--input", source, "--receipt", receipt)
    assert runner.run("--state-dir", alias, "show-run", "--receipt", receipt).stdout == result.stdout
    runner.at_state("show-run", "--receipt", receipt, "--output", alias / "export", expected=3)
    assert not (runner.state / "export").exists()
