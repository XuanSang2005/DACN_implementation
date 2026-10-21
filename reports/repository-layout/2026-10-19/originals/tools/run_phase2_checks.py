"""Run phase-2 checks against an installed wheel, with durable command evidence.

Invoke using the pinned project Python. Does not install or modify dependencies.
Each invocation appends results, including failed commands, to the audit log.
"""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = root / "reports/s01-phase2/test-results.txt"
    if sys.version_info[:3] != (3, 13, 16):
        raise RuntimeError("Use the pinned CPython 3.13.16 environment")
    if not sys._is_gil_enabled():
        raise RuntimeError("Phase 2 requires the regular GIL build")
    commands = [[sys.executable, "-m", "pip", "check"]]
    for mode in ("c", "python"):
        commands.append([
            sys.executable, "-m", "pytest", str(root / "tests"),
            "-c", str(root / "pyproject.toml"), "-v", f"--encoder-backend={mode}",
        ])
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    failures = 0
    with tempfile.TemporaryDirectory(prefix="dacn-s01-phase2-") as cwd:
        for command in commands:
            with report.open("a", encoding="utf-8") as log:
                log.write(f"\n$ {shlex.join(command)}\ncwd={cwd}\n"
                          "PYTHONPATH unset; PYTEST_ADDOPTS unset; "
                          "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1\n")
                log.flush()
                result = subprocess.run(command, cwd=cwd, env=env,
                                        stdout=log, stderr=subprocess.STDOUT)
                log.write(f"\nexit_code={result.returncode}\n")
            print(f"{command[-1]}: exit_code={result.returncode}", flush=True)
            failures += result.returncode != 0
    return int(failures != 0)


if __name__ == "__main__":
    raise SystemExit(main())
