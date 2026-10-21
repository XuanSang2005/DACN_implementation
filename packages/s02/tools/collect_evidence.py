"""Package entry point; shared workspace tooling, never production imports."""
import runpy
from pathlib import Path

if __name__ == "__main__":
    tooling = runpy.run_path(str(Path(__file__).resolve().parents[3] / "tools" / "collect_evidence.py"))
    raise SystemExit(tooling["main"](fixed_package="s02"))
