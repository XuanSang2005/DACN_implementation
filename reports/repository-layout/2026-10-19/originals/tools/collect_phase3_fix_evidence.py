"""Verify the P3-F1 a5 artifact and preserve the audited a4 history."""

from datetime import datetime, timezone
import difflib
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sqlite3
import sys
import zipfile

import dacn_s01
import simplejson._speedups

from dacn_s01.service import validator_build
from dacn_s01.storage_schema import DB_VERSION, DDL


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports/s01-phase3/fixes-0.1.0a5"
    baseline = json.loads((reports / "baseline-verification.json").read_text())
    before = json.loads((reports / "protected-files-before.json").read_text())
    assert metadata.version("dacn-s01") == "0.1.0a5"
    assert platform.python_version() == baseline["python"]["version"] == "3.13.16"
    assert sys._is_gil_enabled()
    assert digest(Path(sys.executable)) == baseline["python"]["sha256"]
    assert sqlite3.sqlite_version == baseline["sqlite_version"]
    old_manifest = json.loads((root / "reports/s01-phase3/environment-manifest.json").read_text())
    assert digest(Path(simplejson._speedups.__file__)) == old_manifest["simplejson_c_extension"]["sha256"]
    installed = Path(dacn_s01.__file__).parent
    assert "site-packages" in installed.parts
    wheel = root / "dist/dacn_s01-0.1.0a5-py3-none-any.whl"
    old_wheel = root / "dist/dacn_s01-0.1.0a4-py3-none-any.whl"
    assert digest(old_wheel) == baseline["wheel_sha256"]
    source = root / "src/dacn_s01"
    files = {str(p.relative_to(source)) for p in source.rglob("*")
             if p.is_file() and "__pycache__" not in p.parts}
    assert files == {p.removeprefix("dacn_s01/") for p in baseline["package_files"]}
    package = {}
    with zipfile.ZipFile(wheel) as archive:
        assert files == {p.removeprefix("dacn_s01/") for p in archive.namelist()
                         if p.startswith("dacn_s01/") and not p.endswith("/")}
        assert files == {str(p.relative_to(installed)) for p in installed.rglob("*")
                         if p.is_file() and "__pycache__" not in p.parts}
        for name in sorted(files):
            values = {"source": digest(source / name), "installed": digest(installed / name),
                      "wheel": hashlib.sha256(archive.read("dacn_s01/" + name)).hexdigest()}
            assert len(set(values.values())) == 1, name
            package["dacn_s01/" + name] = values
        distribution = metadata.distribution("dacn-s01")
        for name in ("METADATA", "WHEEL"):
            assert distribution.read_text(name).encode() == archive.read("dacn_s01-0.1.0a5.dist-info/" + name)
    direct_url = json.loads(distribution.read_text("direct_url.json"))
    assert not direct_url.get("dir_info", {}).get("editable", False)
    assert direct_url["archive_info"]["hashes"]["sha256"] == digest(wheel)
    distributions = sorted([{"name": d.metadata["Name"], "version": d.version,
                             "requires_dist": d.requires or []} for d in metadata.distributions()],
                           key=lambda d: d["name"].lower())
    assert len(distributions) == len(baseline["installed_distributions"])
    for old in baseline["installed_distributions"]:
        current = next(d for d in distributions if d["name"] == old["name"])
        assert current == (dict(old, version="0.1.0a5") if old["name"] == "dacn-s01" else old)

    changed = {name for name, sha in before.items() if digest(Path(name)) != sha}
    assert changed == {str(root / "src/dacn_s01/service.py"), str(root / "pyproject.toml")}
    comparisons = {name: {"before": sha, "after": digest(Path(name)),
                          "intentional_change": name in changed} for name, sha in before.items()}
    (reports / "protected-files-verification.json").write_text(json.dumps({
        "all_protected_unchanged": True, "inventory_count": len(before),
        "unchanged_count": len(before) - len(changed), "intentional_changes": sorted(changed),
        "files": comparisons}, indent=2) + "\n")
    original_project = (root / "pyproject.toml").read_bytes().replace(b'"0.1.0a5"', b'"0.1.0a4"')
    assert hashlib.sha256(original_project).hexdigest() == before[str(root / "pyproject.toml")]
    patch = []
    with zipfile.ZipFile(old_wheel) as archive:
        for name in sorted(files):
            old, new = archive.read("dacn_s01/" + name), (source / name).read_bytes()
            if old != new:
                assert name == "service.py"
                patch.extend(difflib.unified_diff(old.decode().splitlines(keepends=True),
                    new.decode().splitlines(keepends=True), "a/src/dacn_s01/" + name, "b/src/dacn_s01/" + name))
    patch.extend(difflib.unified_diff(original_project.decode().splitlines(keepends=True),
        (root / "pyproject.toml").read_text().splitlines(keepends=True), "a/pyproject.toml", "b/pyproject.toml"))
    (reports / "production-changes.patch").write_text("".join(patch))
    assert DB_VERSION == 1
    assert "\n\n".join(sql + ";" for sql in DDL.values()) + "\n" == (root / "reports/s01-phase3/database-schema.sql").read_text()

    commands = json.loads((reports / "after-commands.json").read_text())["runs"]
    assert len(commands) == 8 and all(c["exit_code"] == 0 for c in commands)
    assert all(c["exit_code"] == 0 for c in json.loads((reports / "build-commands.json").read_text()))
    cases = json.loads((reports / "after-concurrency-fault-evidence.json").read_text())
    schedules = {"both-unchanged", "same-change", "different-changes", "unchanged-first", "changed-first"}
    for backend in ("c", "python"):
        selected = [c for c in cases if c["suite"] == f"full-{backend}"]
        assert schedules <= {c["case"] for c in selected}
        assert {"kill-before_commit", "kill-after_commit"} <= {c["case"] for c in selected}
        for case in selected:
            if case["case"] in schedules:
                events = case["events"]
                before_commit_a = next(e["time_ns"] for e in events if e["role"] == "A" and e["event"] == "before_commit")
                began_b = next(e["time_ns"] for e in events if e["role"] == "B" and e["event"] == "after_begin")
                busy_b = next(e["time_ns"] for e in events if e["event"] == "busy_observed")
                assert busy_b < before_commit_a < began_b
    project_files = [root / "pyproject.toml", root / ".python-version", *root.glob("requirements*"),
                     *root.glob("src/**/*.py"), *root.glob("tests/**/*.py"), *root.glob("tools/*.py")]
    manifest = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "P3-F1 fixed and tested; pending audit; no phase 4/S02",
        "package_version": metadata.version("dacn-s01"), "validator_version": validator_build(),
        "contract_version": "0.1.0-draft.2", "input_schema_version": "1.0.0", "database_structure_version": DB_VERSION,
        "python": baseline["python"], "platform": platform.platform(), "machine": platform.machine(),
        "sqlite_version": sqlite3.sqlite_version, "installed_distributions": distributions,
        "runtime_dependencies_unchanged": True, "installed_package_path": str(installed), "direct_url": direct_url,
        "wheel": {"path": str(wheel.relative_to(root)), "sha256": digest(wheel)},
        "baseline_wheel_preserved": {"path": str(old_wheel.relative_to(root)), "sha256": digest(old_wheel)},
        "simplejson_c_extension": {"path": simplejson._speedups.__file__, "sha256": digest(Path(simplejson._speedups.__file__))},
        "source_installed_wheel_identical": True, "package_files": package,
        "project_file_sha256": {str(p.relative_to(root)): digest(p) for p in sorted(project_files)},
        "unchanged_inventory_count": len(before) - len(changed), "intentional_changes": sorted(changed),
        "concurrency_fault_records": len(cases), "test_log": "after-test-results.txt", "commands": "after-commands.json"}
    (reports / "environment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified {len(package)} package files across source/install/wheel; runtime/dependencies unchanged.")
    print(f"Verified {len(before) - len(changed)}/{len(before)} baseline inventory files unchanged; only service.py and package version changed.")
    print(f"Verified five real process schedules and two kill boundaries per backend; {len(cases)} evidence records.")
    print(f"Wheel sha256: {digest(wheel)}")


if __name__ == "__main__":
    main()
