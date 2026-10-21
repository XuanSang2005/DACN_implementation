"""Synthetic E2E fixtures, read-only input and isolated local stores."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dacn_s01.codec import serialize_json


@pytest.fixture
def payload():
    return {"schema_version": "1.0.0", "title": "Synthetic clinic", "context": "Test only",
        "actors": ["Reception"], "functional_requirements": [{"id": "R1", "text": " Record request ",
        "priority": None, "acceptance_criteria": ["Second", "First"]}], "non_functional_requirements": [],
        "constraints": [{"id": "C1", "text": "Local test", "priority": "must", "acceptance_criteria": [],
                         "constraint": {"kind": "test", "value": None}}],
        "design_preferences": {"metric_priorities": ["response_time_p95", "sustainable_throughput",
                                                     "cpu_utilisation", "scaling_gain"]},
        "operating_conditions": dict.fromkeys(["critical_scenarios", "expected_load", "peak_load",
                                               "data_volume", "growth", "resource_budget"])}


class Runner:
    def __init__(self, tmp_path, backend):
        self.root = tmp_path
        self.state = tmp_path / "kho local Đợt 4"
        self.cwd = tmp_path / "outside-source"
        self.cwd.mkdir()
        self.backend = backend
        self.sequence = 0
        self.evidence = []
        self.env = os.environ.copy()
        for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
            self.env.pop(name, None)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"

    def command(self, args, *, behavior=None, fd=None):
        self.sequence += 1
        evidence = self.root / f"worker-{self.sequence}.json"
        return ([sys.executable, "-B", str(Path(__file__).with_name("worker.py")), self.backend,
                 str(evidence), str(fd) if fd is not None else "-", json.dumps(behavior or {}), *map(str, args)], evidence)

    def checked_evidence(self, path):
        data = json.loads(path.read_text())
        assert "site-packages" in data["import_path"] and data["package"] == "0.1.0a6"
        assert data["counts"]["python" if self.backend == "c" else "c"] == 0
        self.evidence.append(data)

    def run(self, *args, expected=0, behavior=None):
        command, evidence = self.command(args, behavior=behavior)
        result = subprocess.run(command, cwd=self.cwd, env=self.env, capture_output=True, timeout=30)
        self.checked_evidence(evidence)
        assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
        assert b"Traceback" not in result.stderr
        return result

    def at_state(self, *args, **kwargs):
        return self.run("--state-dir", self.state, *args, **kwargs)

    def input(self, payload, name="input readonly.json"):
        path = self.root / name
        path.write_bytes(serialize_json(payload))
        path.chmod(0o400)
        return path


@pytest.fixture
def runner(tmp_path, request):
    value = Runner(tmp_path, request.config.getoption("--encoder-backend"))
    yield value
    totals = {key: sum(item["counts"][key] for item in value.evidence) for key in ("c", "python")}
    print("PHASE4_ENCODERS " + json.dumps({"backend": value.backend, "counts": totals,
                                          "processes": len(value.evidence)}))
