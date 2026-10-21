"""Verify the phase-4 delivery against the start-of-task audited a5 baseline."""

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
    reports = root / "reports/s01-phase4"
    baseline = json.loads((reports / "baseline-verification.json").read_text())
    previous = json.loads((root / "reports/s01-phase3/fixes-0.1.0a5/environment-manifest.json").read_text())
    assert metadata.version("dacn-s01") == "0.1.0a6"
    assert platform.python_version() == baseline["python"]["version"] == "3.13.16"
    assert sys._is_gil_enabled() and digest(Path(sys.executable)) == baseline["python"]["sha256"]
    assert sqlite3.sqlite_version == baseline["sqlite_version"]
    assert digest(Path(simplejson._speedups.__file__)) == previous["simplejson_c_extension"]["sha256"]
    installed = Path(dacn_s01.__file__).parent
    assert "site-packages" in installed.parts
    wheel = root / "dist/dacn_s01-0.1.0a6-py3-none-any.whl"
    old_wheel = root / "dist/dacn_s01-0.1.0a5-py3-none-any.whl"
    assert digest(old_wheel) == baseline["wheel_sha256"]
    source = root / "src/dacn_s01"
    files = {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    new_files = {"__main__.py", "cli.py", "local_io.py"}
    assert files == {name.removeprefix("dacn_s01/") for name in baseline["package_files"]} | new_files
    package = {}
    with zipfile.ZipFile(wheel) as archive:
        assert files == {name.removeprefix("dacn_s01/") for name in archive.namelist()
                         if name.startswith("dacn_s01/") and not name.endswith("/")}
        assert files == {str(p.relative_to(installed)) for p in installed.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        for name in sorted(files):
            values = {"source": digest(source / name), "installed": digest(installed / name),
                      "wheel": hashlib.sha256(archive.read("dacn_s01/" + name)).hexdigest()}
            assert len(set(values.values())) == 1, name
            package["dacn_s01/" + name] = values
        distribution = metadata.distribution("dacn-s01")
        for name in ("METADATA", "WHEEL"):
            assert distribution.read_text(name).encode() == archive.read("dacn_s01-0.1.0a6.dist-info/" + name)
    direct_url = json.loads(distribution.read_text("direct_url.json"))
    assert not direct_url.get("dir_info", {}).get("editable", False)
    assert direct_url["archive_info"]["hashes"]["sha256"] == digest(wheel)
    distributions = sorted([{"name": d.metadata["Name"], "version": d.version, "requires_dist": d.requires or []}
                            for d in metadata.distributions()], key=lambda d: d["name"].lower())
    assert len(distributions) == len(baseline["installed_distributions"])
    for old in baseline["installed_distributions"]:
        current = next(d for d in distributions if d["name"] == old["name"])
        assert current == (dict(old, version="0.1.0a6") if old["name"] == "dacn-s01" else old)
    before = json.loads((reports / "protected-files-before.json").read_text())
    changed = {name for name, sha in before.items() if digest(Path(name)) != sha}
    assert changed == {str(root / "src/dacn_s01/repository.py"), str(root / "pyproject.toml")}
    (reports / "protected-files-verification.json").write_text(json.dumps({
        "all_protected_unchanged": True, "inventory_count": len(before), "unchanged_count": len(before) - len(changed),
        "intentional_changes": sorted(changed), "files": {name: {"before": sha, "after": digest(Path(name)),
        "intentional_change": name in changed} for name, sha in before.items()}}, indent=2) + "\n")
    original_project = (root / "pyproject.toml").read_bytes().replace(b'"0.1.0a6"', b'"0.1.0a5"')
    assert hashlib.sha256(original_project).hexdigest() == before[str(root / "pyproject.toml")]
    patch = []
    with zipfile.ZipFile(old_wheel) as archive:
        for name in sorted(files):
            old = b"" if name in new_files else archive.read("dacn_s01/" + name)
            new = (source / name).read_bytes()
            if old != new:
                assert name in new_files | {"repository.py"}
                patch.extend(difflib.unified_diff(old.decode().splitlines(keepends=True), new.decode().splitlines(keepends=True),
                             "/dev/null" if name in new_files else "a/src/dacn_s01/" + name, "b/src/dacn_s01/" + name))
    patch.extend(difflib.unified_diff(original_project.decode().splitlines(keepends=True),
        (root / "pyproject.toml").read_text().splitlines(keepends=True), "a/pyproject.toml", "b/pyproject.toml"))
    (reports / "production-changes.patch").write_text("".join(patch))
    assert DB_VERSION == 1
    assert "\n\n".join(sql + ";" for sql in DDL.values()) + "\n" == (root / "reports/s01-phase3/database-schema.sql").read_text()
    commands = json.loads((reports / "final-commands.json").read_text())
    assert len(commands) == 6 and all(c["exit_code"] == 0 for c in commands)
    development = json.loads((reports / "development-commands.json").read_text())
    assert {c["name"] for c in development} >= {"build", "install"}
    assert all(c["exit_code"] == 0 for c in development)
    assert json.loads((reports / "prior-audit-probes-command.json").read_text())["exit_code"] == 0
    evidence = json.loads((reports / "final-evidence.json").read_text())
    totals = {}
    for backend in ("c", "python"):
        selected = [e for e in evidence if e["suite"] == "suite-" + backend]
        old_cases = [e for e in selected if e["marker"] == "PHASE3_EVIDENCE"]
        names = {e["case"] for e in old_cases}
        schedules = {"both-unchanged", "same-change", "different-changes", "unchanged-first", "changed-first"}
        assert schedules | {"kill-before_commit", "kill-after_commit"} <= names
        for item in old_cases:
            if item["case"] in schedules:
                events = item["events"]
                busy = next(e["time_ns"] for e in events if e["event"] == "busy_observed")
                before_commit = next(e["time_ns"] for e in events if e["role"] == "A" and e["event"] == "before_commit")
                after_begin = next(e["time_ns"] for e in events if e["role"] == "B" and e["event"] == "after_begin")
                assert busy < before_commit < after_begin
        new_cases = [e for e in selected if e["marker"] == "PHASE4_EVIDENCE"]
        assert {"lifecycle", "receipt-contention", "kill-receipt_ready", "kill-before_commit", "kill-after_commit",
                "closed-pipe", "export-collision", "real-export-permission", "receipt-fault"} <= {e["case"] for e in new_cases}
        aliases = [e for e in new_cases if e["case"] == "dataset-ancestor-identity"]
        assert len(aliases) == 3 and all(e["actual_case_alias"] and e["dataset_unchanged"] for e in aliases)
        worker_records = [e for e in selected if e["marker"] == "PHASE4_ENCODERS"]
        totals[backend] = {"processes": sum(e["processes"] for e in worker_records),
                           "counts": {key: sum(e["counts"][key] for e in worker_records) for key in ("c", "python")}}
        assert totals[backend]["counts"][backend] > 0
        assert totals[backend]["counts"]["python" if backend == "c" else "c"] == 0
    project_files = [root / "pyproject.toml", root / ".python-version", *root.glob("requirements*"),
                     *root.glob("src/**/*.py"), *root.glob("tests/**/*.py"), *root.glob("tools/*.py"),
                     root / "docs/S01_LOCAL_GUIDE.md", root / "docs/examples/s01-local/synthetic-clinic.input.json"]
    walkthrough = json.loads((reports / "local-walkthrough.json").read_text())
    assert walkthrough["validator_version"] == validator_build()
    assert len(walkthrough["commands"]) == 11 and all(walkthrough["checks"].values())
    manifest = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "phase 4 implemented/tested; awaiting complete S01 audit; not accepted; no S02",
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
        "worker_encoder_totals": totals, "evidence_records": len(evidence),
        "test_log": "final-results.txt", "commands": "final-commands.json"}
    (reports / "environment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified {len(package)} package files across source/install/wheel; runtime/dependencies unchanged.")
    print(f"Verified {len(before) - len(changed)}/{len(before)} baseline inventory files unchanged; only repository lookup additions and package version changed.")
    print(f"Verified real process schedules/receipt contention/kill/output recovery on both backends; {len(evidence)} evidence records.")
    print("Completed instrumented CLI subprocess totals: " + json.dumps(totals))
    print(f"Wheel sha256: {digest(wheel)}")


if __name__ == "__main__":
    main()
