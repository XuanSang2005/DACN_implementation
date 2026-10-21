"""Record F1/F2 checks on the audited build or its fix, outside the project cwd."""

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--audit-test", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports/s01-phase2/fixes-0.1.0a3"
    expected = "0.1.0a2" if args.phase == "before" else "0.1.0a3"
    assert version("dacn-s01") == expected
    assert sys.version_info[:3] == (3, 13, 16) and sys._is_gil_enabled()
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(name, None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    prefix = [sys.executable, "-B", "-m", "pytest", "-c", str(root / "pyproject.toml"),
              "-p", "no:cacheprovider", "-v", "--tb=short"]
    commands = []
    for backend in ("c", "python"):
        commands.append((f"regressions-{backend}", prefix + [
            str(root / "tests/phase2/test_audit_regressions.py"), f"--encoder-backend={backend}"]))
    if args.phase == "after":
        for backend in ("c", "python"):
            commands.append((f"full-{backend}", prefix + [str(root / "tests"), f"--encoder-backend={backend}"]))
        commands.append(("pip-check", [sys.executable, "-m", "pip", "check"]))
    # The original external suite selects both backends in its own fixture.
    # No conftests, bytecode writes or pytest cache in the read-only audit area.
    commands.append(("independent-audit", prefix + [str(args.audit_test.resolve()), "--noconftest"]))
    records = []
    with tempfile.TemporaryDirectory(prefix=f"dacn-phase2-fix-{args.phase}-") as cwd:
        for name, command in commands:
            with (reports / f"{args.phase}-test-results.txt").open("a", encoding="utf-8") as log:
                log.write(f"\n{name}; installed package={expected}\n$ {shlex.join(command)}\ncwd={cwd}\n"
                          "PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS unset; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1\n")
                log.flush()
                result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
                log.write(f"\nexit_code={result.returncode}\n")
            records.append({"name": name, "command": command, "cwd": cwd, "exit_code": result.returncode})
            print(f"{name}: exit_code={result.returncode}", flush=True)
    (reports / f"{args.phase}-commands.json").write_text(json.dumps({
        "package": expected, "runs": records,
        "env": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "unset": ["PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"]},
    }, indent=2) + "\n")
    return int(any(r["exit_code"] != 0 for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
