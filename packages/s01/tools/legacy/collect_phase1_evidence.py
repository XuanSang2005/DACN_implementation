"""Measure the installed phase-1 build and read-only source schema."""

import argparse
import ast
from datetime import datetime, timezone
import decimal
import hashlib
from importlib import metadata, resources
import json
from pathlib import Path
import platform
import sqlite3
import sys
import sysconfig
import zipfile

import dacn_s01
import simplejson._speedups

from dacn_s01.schema_resource import SCHEMA_SHA256, load_schema, read_schema_bytes


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-source", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports/s01-phase1"

    def write(name, data):
        (reports / name).write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n")

    installed = Path(dacn_s01.__file__).parent
    assert "site-packages" in str(installed), "Measure an installed wheel, not src/"
    wheel = root / "dist/dacn_s01-0.1.0a1-py3-none-any.whl"
    artifact_name = "dacn_s01/schemas/input/1.0.0/system-input.schema.json"
    source = args.schema_source.read_bytes()
    packaged = read_schema_bytes()
    schema = load_schema()  # Actual duplicate-key and metaschema checks.
    with zipfile.ZipFile(wheel) as archive:
        wheel_schema = archive.read(artifact_name)
        for path in (root / "src/dacn_s01").rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                relative = path.relative_to(root / "src")
                assert archive.read(str(relative)) == path.read_bytes()
                assert (installed.parent / relative).read_bytes() == path.read_bytes()
    assert source == packaged == wheel_schema
    write("schema-resource-verification.json", {
        "source_path": str(args.schema_source.resolve()),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "installed_resource_sha256": hashlib.sha256(packaged).hexdigest(),
        "wheel_resource_sha256": hashlib.sha256(wheel_schema).hexdigest(),
        "baseline_sha256": SCHEMA_SHA256,
        "byte_identical": True,
        "read_via_importlib_resources": True,
        "installed_package_path": str(installed),
        "duplicate_key_check": "passed: object_pairs_hook before dict construction",
        "metaschema_check": "passed: Draft202012Validator.check_schema",
        "integer_keyword_example": {
            "pointer": "/properties/actors/minItems",
            "type": type(schema["properties"]["actors"]["minItems"]).__name__,
            "value": schema["properties"]["actors"]["minItems"],
        },
        "all_source_package_files_match_installed_wheel": True,
        "requirements_validation_run": False,
        "profile_adapter_implemented": False,
    })
    before = json.loads((reports / "protected-files-before.json").read_text())
    protected = {}
    for name, sha in before.items():
        path = Path(name) if Path(name).is_absolute() else root / name
        protected[name] = {"before": sha, "after": digest(path)}
        assert protected[name]["after"] == sha, f"Protected file changed: {name}"
    write("protected-files-verification.json", {"all_unchanged": True, "files": protected})

    tree = ast.parse((installed / "codec.py").read_text())
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == "dumps")
    encoder_options = {keyword.arg: ast.literal_eval(keyword.value) for keyword in call.keywords}
    file_set = [*root.glob("requirements*"), root / "pyproject.toml", root / ".python-version",
                *root.glob("src/**/*.py"), *root.glob("tests/*.py"), *root.glob("tools/*.py"),
                *root.glob("src/**/*.json"), *root.glob("src/**/*.md"), wheel]
    wheels = sorted((root / ".tools/wheelhouse").glob("*.whl"))
    distributions = sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower())
    write("environment-manifest.json", {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "S01 phase 1; implementation pending audit",
        "python": {
            "version": platform.python_version(), "sys_version": sys.version,
            "implementation": platform.python_implementation(),
            "executable": sys.executable, "base_prefix": sys.base_prefix,
            "build": platform.python_build(), "compiler": platform.python_compiler(),
            "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
            "soabi": sysconfig.get_config_var("SOABI"),
            "py_gil_disabled": sysconfig.get_config_var("Py_GIL_DISABLED"),
            "gil_enabled": sys._is_gil_enabled(),
            "executable_sha256": digest(Path(sys.executable)),
            "distribution": json.loads((reports / "python-distribution.json").read_text()),
        },
        "platform": {"platform": platform.platform(), "machine": platform.machine(),
                     "mac_ver": platform.mac_ver()},
        "sqlite_linked_version": sqlite3.sqlite_version,
        "database_created": False,
        "runtime_limits": {"int_max_str_digits": sys.get_int_max_str_digits(),
                           "recursion_limit": sys.getrecursionlimit(),
                           "decimal_MAX_EMAX": decimal.MAX_EMAX,
                           "decimal_MIN_ETINY": decimal.MIN_ETINY,
                           "libmpdec_version": decimal.__libmpdec_version__},
        "direct_runtime_dependencies": {"jsonschema": "4.26.0", "simplejson": "4.2.0"},
        "test_dependency": {"pytest": "9.1.1"},
        "build": {"backend": "setuptools.build_meta", "setuptools": "80.9.0",
                  "wheel": "0.45.1", "isolation": False},
        "bootstrap_resolver": json.loads((reports / "bootstrap-uv.json").read_text()),
        "installed_distributions": [
            {"name": d.metadata["Name"], "version": d.version, "requires_dist": d.requires or []}
            for d in distributions
        ],
        "selected_dependency_wheels": [{"file": p.name, "sha256": digest(p)} for p in wheels],
        "simplejson_c_extension": {"path": simplejson._speedups.__file__,
                                   "sha256": digest(Path(simplejson._speedups.__file__))},
        "codec": {
            "parse": {"library": "stdlib json", "input": "bytes", "strict": True,
                      "parse_int": "Decimal from token", "parse_float": "Decimal from token",
                      "object_pairs_hook": "reject duplicate decoded keys", "parse_constant": "reject"},
            "serialize_options_from_installed_source": encoder_options,
            "output_encoding": "ASCII JSON bytes; subset of UTF-8",
        },
        "test_execution": {"runner": "tools/run_phase1_checks.py", "backends": ["c", "python"],
                           "cwd": "separate temporary directory", "plugin_autoload": False,
                           "results": "test-results.txt"},
        "project_file_sha256": {str(p.relative_to(root)): digest(p) for p in sorted(set(file_set))},
        "lock_scope": "CPython 3.13.16 regular GIL, macOS arm64; other platforms not certified",
    })
    print("Measured environment, schema byte identity, wheel/source identity and protected files: passed")


if __name__ == "__main__":
    main()
