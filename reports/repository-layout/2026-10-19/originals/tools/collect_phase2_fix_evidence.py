"""Verify the F1/F2 installed fix without overwriting historical phase reports."""

from datetime import datetime, timezone
import difflib
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
import zipfile

import dacn_s01
import simplejson._speedups

from dacn_s01.validation import W


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports/s01-phase2/fixes-0.1.0a3"
    previous = json.loads((reports.parent / "environment-manifest.json").read_text())
    baseline = json.loads((reports / "baseline-0.1.0a2.json").read_text())
    assert metadata.version("dacn-s01") == "0.1.0a3"
    assert platform.python_version() == "3.13.16" and sys._is_gil_enabled()
    assert digest(Path(sys.executable)) == previous["python"]["executable_sha256"]
    installed = Path(dacn_s01.__file__).resolve().parent
    assert "site-packages" in installed.parts
    source = root / "src/dacn_s01"
    wheel = root / "dist/dacn_s01-0.1.0a3-py3-none-any.whl"
    old_wheel = root / "dist/dacn_s01-0.1.0a2-py3-none-any.whl"
    assert digest(old_wheel) == baseline["wheel_sha256"]
    package_files = {}
    changes = []
    patch = []

    def files_under(path):
        return {str(p.relative_to(path)) for p in path.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts}

    with zipfile.ZipFile(wheel) as archive, zipfile.ZipFile(old_wheel) as old:
        names = {n.removeprefix("dacn_s01/") for n in archive.namelist()
                 if n.startswith("dacn_s01/") and not n.endswith("/")}
        assert files_under(source) == files_under(installed) == names
        for name in sorted(names):
            package_name = "dacn_s01/" + name
            raw = (source / name).read_bytes()
            assert raw == (installed / name).read_bytes() == archive.read(package_name)
            package_files[package_name] = {
                "source_sha256": digest(source / name),
                "installed_sha256": digest(installed / name),
                "wheel_entry_sha256": hashlib.sha256(archive.read(package_name)).hexdigest(),
            }
            if digest(source / name) != baseline["package_file_sha256"][package_name]:
                changes.append("src/" + package_name)
                patch.extend(difflib.unified_diff(
                    old.read(package_name).decode().splitlines(keepends=True),
                    raw.decode().splitlines(keepends=True),
                    fromfile="0.1.0a2/src/" + package_name, tofile="0.1.0a3/src/" + package_name))
        dist = metadata.distribution("dacn-s01")
        for name in ("METADATA", "WHEEL"):
            assert dist.read_text(name).encode() == archive.read("dacn_s01-0.1.0a3.dist-info/" + name)
    assert changes == ["src/dacn_s01/envelope.py", "src/dacn_s01/validation.py"]
    direct_url = json.loads(dist.read_text("direct_url.json"))
    assert not direct_url.get("dir_info", {}).get("editable", False)
    assert direct_url["archive_info"]["hashes"]["sha256"] == digest(wheel)

    # Existing tests, tools and other tracked evidence inputs must stay intact.
    changed_existing = [name for name, sha in previous["project_file_sha256"].items()
                        if digest(root / name) != sha]
    assert set(changed_existing) == {*changes, "pyproject.toml"}
    current_project = (root / "pyproject.toml").read_text()
    old_project = current_project.replace('version = "0.1.0a3"', 'version = "0.1.0a2"')
    assert hashlib.sha256(old_project.encode()).hexdigest() == baseline["pyproject_sha256"]
    patch.extend(difflib.unified_diff(old_project.splitlines(keepends=True),
                                    current_project.splitlines(keepends=True),
                                    fromfile="0.1.0a2/pyproject.toml", tofile="0.1.0a3/pyproject.toml"))
    (reports / "production-changes.patch").write_text("".join(patch))

    before = json.loads((reports / "protected-files-before.json").read_text())
    protected = {name: {"before": sha, "after": digest(Path(name))} for name, sha in before.items()}
    assert all(record["before"] == record["after"] for record in protected.values())
    (reports / "protected-files-verification.json").write_text(json.dumps({
        "all_unchanged": True, "file_count": len(protected), "files": protected,
    }, indent=2) + "\n")

    distributions = sorted([
        {"name": d.metadata["Name"], "version": d.version, "requires_dist": d.requires or []}
        for d in metadata.distributions()
    ], key=lambda d: d["name"].lower())
    dependencies = lambda items: [d for d in items if d["name"] != "dacn-s01"]
    assert dependencies(distributions) == dependencies(previous["installed_distributions"])
    c_extension = Path(simplejson._speedups.__file__)
    assert digest(c_extension) == previous["simplejson_c_extension"]["sha256"]
    codepoints = [f"U+{ord(c):04X}" for c in sorted(W)]
    assert codepoints == previous["validation_profile"]["W_codepoints"] and len(W) == 29
    project_files = [root / "pyproject.toml", *root.glob("tests/**/*.py"), *root.glob("tools/*.py")]
    manifest = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "implemented and tested; pending audit of F1/F2 fix",
        "version": metadata.version("dacn-s01"), "baseline_version": baseline["version"],
        "contract_version": "0.1.0-draft.2", "schema_version": "1.0.0",
        "python": {"version": platform.python_version(), "sys_version": sys.version,
                   "executable": sys.executable, "executable_sha256": digest(Path(sys.executable)),
                   "gil_enabled": sys._is_gil_enabled(), "unchanged_from_baseline": True},
        "platform": platform.platform(), "machine": platform.machine(),
        "installed_package_path": str(installed), "direct_url": direct_url,
        "installed_distributions": distributions, "dependencies_unchanged": True,
        "simplejson_c_extension": {"path": str(c_extension), "sha256": digest(c_extension)},
        "wheel": {"path": str(wheel.relative_to(root)), "sha256": digest(wheel)},
        "all_source_installed_wheel_files_identical": True, "package_files": package_files,
        "changed_existing_files": sorted(changed_existing),
        "project_file_sha256": {str(p.relative_to(root)): digest(p) for p in sorted(project_files)},
        "W_codepoints": codepoints, "W_unchanged": True,
        "protected_files_count": len(protected), "protected_files_unchanged": True,
        "test_execution": {"runner": "tools/run_phase2_fix_checks.py",
                           "commands": "after-commands.json", "results": "after-test-results.txt"},
    }
    (reports / "environment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"0.1.0a3 verified: {len(package_files)} package files identical across source/install/wheel; "
          f"{len(protected)} protected files unchanged; runtime/dependencies/W unchanged")


if __name__ == "__main__":
    main()
