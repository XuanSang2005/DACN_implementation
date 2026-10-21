"""Build/install and record real installed-package phase-4 verification."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--audit-test", type=Path, action="append", default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports/s01-phase4"
    tag = "development" if args.development else "final"
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(name, None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    records, evidence = [], []
    with tempfile.TemporaryDirectory(prefix="dacn-phase4-checks-") as cwd:
        commands = []
        if args.build:
            commands.extend([
                ("build", [sys.executable, "-B", "-m", "pip", "wheel", "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir", "dist", "."], str(root)),
                ("install", [sys.executable, "-B", "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", "dist/dacn_s01-0.1.0a6-py3-none-any.whl"], str(root))])
        prefix = [sys.executable, "-B", "-m", "pytest", "-c", str(root / "pyproject.toml"), "-s", "-v", "--tb=short", "-p", "no:cacheprovider"]
        commands.extend((f"suite-{backend}", prefix + [str(root / ("tests/phase4" if args.development else "tests")), f"--encoder-backend={backend}"], cwd)
                        for backend in ("c", "python"))
        commands.append(("pip-check", [sys.executable, "-B", "-m", "pip", "check"], cwd))
        commands.extend((f"audit-{i}", prefix + [str(path.resolve()), "--noconftest"], cwd)
                        for i, path in enumerate(args.audit_test))
        for name, command, working in commands:
            with (reports / f"{tag}-results.txt").open("a") as log:
                log.write(f"\n{name}\n$ {shlex.join(command)}\ncwd={working}\nPYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS unset; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTHONDONTWRITEBYTECODE=1\n")
                log.flush()
                result = subprocess.run(command, cwd=working, env=env, capture_output=True, text=True)
                log.write(result.stdout + result.stderr + f"\nexit_code={result.returncode}\n")
            records.append({"name": name, "command": command, "cwd": working, "exit_code": result.returncode})
            for line in result.stdout.splitlines():
                for marker in ("PHASE3_EVIDENCE ", "PHASE4_EVIDENCE ", "PHASE4_ENCODERS "):
                    if marker in line:
                        item, _ = json.JSONDecoder().raw_decode(line.split(marker, 1)[1])
                        evidence.append({"suite": name, "marker": marker.strip(), **item})
            print(f"{name}: exit_code={result.returncode}", flush=True)
            if name in ("build", "install") and result.returncode:
                break
    (reports / f"{tag}-commands.json").write_text(json.dumps(records, indent=2) + "\n")
    (reports / f"{tag}-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return int(any(r["exit_code"] for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
