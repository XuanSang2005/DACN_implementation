"""Package entry point; shared workspace tooling, never production imports."""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    if "--package" in sys.argv:
        raise SystemExit("Package is fixed by this entry point")
    sys.argv[1:1] = ["--package", "s02"]
    runpy.run_path(str(Path(__file__).resolve().parents[3] / "tools" / "run_checks.py"), run_name="__main__")
