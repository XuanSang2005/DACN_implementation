import json
import os
import socket
import sqlite3
import subprocess
import time

import pytest

from dacn_s01.codec import parse_json


def start(runner, args, points):
    parent, child = socket.socketpair()
    parent.settimeout(15)
    command, evidence = runner.command(args, behavior={"pause": points}, fd=child.fileno())
    process = subprocess.Popen(command, cwd=runner.cwd, env=runner.env, pass_fds=(child.fileno(),),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child.close()
    return process, parent, evidence


def event(channel):
    data = b""
    while not data.endswith(b"\n"):
        part = channel.recv(4096)
        assert part, "worker exited before synchronization"
        data += part
    return {**json.loads(data), "observed_ns": time.monotonic_ns()}


def state(runner):
    with sqlite3.connect(runner.state / "s01.sqlite3") as connection:
        return {t: connection.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("runs", "sources", "snapshots", "specs")}


def args(runner, source, receipt):
    return ["--state-dir", runner.state, "submit", "--mode", "create", "--input", source, "--receipt", receipt]


def finish(runner, worker):
    process, channel, evidence = worker
    stdout, stderr = process.communicate(timeout=20)
    channel.close()
    runner.checked_evidence(evidence)
    return process.returncode, stdout, stderr


def cleanup(workers):
    for process, channel, _ in workers:
        if process.poll() is None:
            process.kill(); process.communicate(timeout=10)
        channel.close()


def test_two_real_processes_compete_for_same_receipt(runner, payload):
    runner.at_state("init")
    source = runner.input(payload)
    receipt = runner.root / "shared receipt.json"
    workers = []
    try:
        for _ in range(2): workers.append(start(runner, args(runner, source, receipt), ["before_link"]))
        events = [event(worker[1]) for worker in workers]
        assert all(e["event"] == "before_link" for e in events)
        assert not receipt.exists() and state(runner)["runs"] == 0
        for worker in workers: worker[1].sendall(b"+")
        results = [finish(runner, worker) for worker in workers]
        assert sorted(r[0] for r in results) == [0, 3]
        winner = parse_json(next(r[1] for r in results if r[0] == 0))
        loser = next(r for r in results if r[0] == 3)
        assert loser[1] == b"" and b"Traceback" not in loser[2]
        assert parse_json(receipt.read_bytes())["run_id"] == winner["run"]["run_id"]
        assert parse_json(runner.run("show-run", "--receipt", receipt).stdout) == winner
        assert state(runner) == dict(runs=1, sources=1, snapshots=1, specs=1)
        assert list(runner.root.glob(".dacn-*.tmp")) == []
        print("PHASE4_EVIDENCE " + json.dumps({"case": "receipt-contention", "backend": runner.backend,
            "kind": "two subprocesses and one filesystem destination", "events": events,
            "exit_codes": [r[0] for r in results], "final_state": state(runner)}))
    finally:
        cleanup(workers)


@pytest.mark.parametrize("point,committed", [("receipt_ready", False), ("before_commit", False), ("after_commit", True)])
def test_kill_and_recover_through_existing_receipt(runner, payload, point, committed):
    runner.at_state("init")
    source = runner.input(payload)
    receipt = runner.root / "receipt"
    worker = start(runner, args(runner, source, receipt), [point])
    try:
        arrived = event(worker[1])
        assert arrived["event"] == point and receipt.exists()
        run_id = parse_json(receipt.read_bytes())["run_id"]
        worker[0].kill()
        worker[0].communicate(timeout=15)
        assert worker[0].returncode == -9
        recovered = runner.run("show-run", "--receipt", receipt, expected=0 if committed else 4)
        if committed:
            output = parse_json(recovered.stdout)
            assert output["run"]["run_id"] == run_id and output["status"] == "validated"
        else:
            assert recovered.stdout == b"" and b"does not prove" in recovered.stderr
        assert state(runner) == dict.fromkeys(("runs", "sources", "snapshots", "specs"), int(committed))
        print("PHASE4_EVIDENCE " + json.dumps({"case": "kill-" + point, "backend": runner.backend,
            "kind": "actual SIGKILL with IPC boundary", "event": arrived, "returncode": -9,
            "run_id": run_id, "final_state": state(runner)}))
    finally:
        cleanup([worker])


@pytest.mark.parametrize("kind", ["closed-pipe", "export-collision", "real-export-permission"])
def test_delivery_failure_after_commit_keeps_record(runner, payload, kind):
    runner.at_state("init")
    source = runner.input(payload)
    receipt = runner.root / "receipt"
    command = args(runner, source, receipt)
    export_dir = runner.root / "export-dir"
    export_dir.mkdir()
    output = export_dir / "output.json"
    if kind != "closed-pipe": command += ["--output", output]
    worker = start(runner, command, ["before_output"])
    try:
        arrived = event(worker[1])
        assert arrived["event"] == "before_output" and state(runner)["runs"] == 1
        if kind == "closed-pipe":
            worker[0].stdout.close()
            worker[0].stdout = None
        elif kind == "export-collision":
            output.write_bytes(b"unrelated file won publication")
        else:
            export_dir.chmod(0o500)  # Actual filesystem EACCES, not a mock.
        worker[1].sendall(b"+")
        code, stdout, stderr = finish(runner, worker)
        assert code == 3 and b"result delivery" in stderr and b"show-run --receipt" in stderr
        assert b"Traceback" not in stderr
        if kind != "closed-pipe": assert stdout == b""
        if kind == "export-collision": assert output.read_bytes() == b"unrelated file won publication"
        result = parse_json(runner.run("show-run", "--receipt", receipt).stdout)
        assert result["status"] == "validated" and result["snapshot"]["revision"] == 1
        assert state(runner) == dict(runs=1, sources=1, snapshots=1, specs=1)
        print("PHASE4_EVIDENCE " + json.dumps({"case": kind, "backend": runner.backend,
            "kind": "actual output I/O/collision after commit", "event": arrived,
            "exit_code": code, "final_state": state(runner)}))
    finally:
        export_dir.chmod(0o700)
        cleanup([worker])
