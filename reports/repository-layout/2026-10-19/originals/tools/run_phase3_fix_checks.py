"""Record P3-F1 checks on installed a4/a5 outside the project working directory."""

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--audit-test", type=Path, action="append", default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports/s01-phase3/fixes-0.1.0a5"
    expected = "0.1.0a4" if args.phase == "before" else "0.1.0a5"
    assert version("dacn-s01") == expected
    assert sys.version_info[:3] == (3, 13, 16) and sys._is_gil_enabled()
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(name, None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    prefix = [sys.executable, "-B", "-m", "pytest", "-c", str(root / "pyproject.toml"),
              "-p", "no:cacheprovider", "-s", "-v", "--tb=short"]
    commands = [(f"regressions-{backend}", prefix + [
        str(root / "tests/phase3/test_failure_diagnostics.py"), f"--encoder-backend={backend}"])
        for backend in ("c", "python")]
    if args.phase == "after":
        commands += [(f"full-{backend}", prefix + [str(root / "tests"), f"--encoder-backend={backend}"])
                     for backend in ("c", "python")]
        commands.append(("pip-check", [sys.executable, "-B", "-m", "pip", "check"]))
    commands += [(f"audit-{i}", prefix + [str(path.resolve()), "--noconftest"])
                 for i, path in enumerate(args.audit_test)]
    records, evidence = [], []
    with tempfile.TemporaryDirectory(prefix=f"dacn-phase3-fix-{args.phase}-") as cwd:
        for name, command in commands:
            with (reports / f"{args.phase}-test-results.txt").open("a") as log:
                log.write(f"\n{name}; installed package={expected}\n$ {shlex.join(command)}\ncwd={cwd}\n"
                          "PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS unset; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTHONDONTWRITEBYTECODE=1\n")
                log.flush()
                result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
                log.write(result.stdout + result.stderr + f"\nexit_code={result.returncode}\n")
            records.append({"name": name, "command": command, "cwd": cwd, "exit_code": result.returncode})
            for line in result.stdout.splitlines():
                if "PHASE3_EVIDENCE " in line:
                    item, _ = json.JSONDecoder().raw_decode(line.split("PHASE3_EVIDENCE ", 1)[1])
                    evidence.append({"suite": name, **item})
            print(f"{name}: exit_code={result.returncode}", flush=True)
    (reports / f"{args.phase}-commands.json").write_text(json.dumps({
        "package": expected, "runs": records,
        "env": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "unset": ["PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"]}}, indent=2) + "\n")
    if evidence:
        (reports / f"{args.phase}-concurrency-fault-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return int(any(r["exit_code"] != 0 for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
