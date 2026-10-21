import hashlib
import json
import subprocess
import sys
from importlib.resources import files

import pytest
from jsonschema import Draft202012Validator

from dacn_s01 import schema_resource
from dacn_s01.schema_resource import SCHEMA_SHA256, load_schema, read_schema_bytes


def test_packaged_artifact_digest_and_metaschema_without_network(monkeypatch):
    import socket

    def deny_network(*args, **kwargs):
        raise AssertionError("Resource checks must not access the network")

    monkeypatch.setattr(socket, "socket", deny_network)
    raw = read_schema_bytes()
    assert hashlib.sha256(raw).hexdigest() == SCHEMA_SHA256
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert type(schema["properties"]["actors"]["minItems"]) is int
    assert type(schema["$defs"]["Requirement"]["properties"]["id"]["minLength"]) is int
    assert schema["properties"]["schema_version"]["default"] == "1.0.0"
    refs = []

    def inspect(value):
        if isinstance(value, dict):
            if "$ref" in value:
                refs.append(value["$ref"])
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(schema)
    assert refs and all(ref.startswith("#/") for ref in refs)
    schema["title"] = "local mutation"
    assert load_schema()["title"] == "DACN user input v1.0.0"


@pytest.mark.parametrize("raw", [
    b'{"type":"object","type":"array"}',
    b'{"properties":{"x":{"type":"string","type":"number"}}}',
    b'{"minItems":"1"}', b'{', b'{"minItems":NaN}',
])
def test_artifact_parser_failures_are_configuration_errors(monkeypatch, raw):
    # Test double bypasses digest gate to exercise deeper artifact checks.
    monkeypatch.setattr(schema_resource, "read_schema_bytes", lambda: raw)
    with pytest.raises(schema_resource.SchemaResourceError) as caught:
        load_schema()
    assert caught.value.code == "PROCESSING_FAILED"


def test_missing_or_changed_resource_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(schema_resource, "files", lambda _: tmp_path)
    with pytest.raises(schema_resource.SchemaResourceError):
        read_schema_bytes()
    path = tmp_path / "schemas/input/1.0.0/system-input.schema.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{}')
    with pytest.raises(schema_resource.SchemaResourceError, match="digest"):
        read_schema_bytes()


def test_installed_package_from_unrelated_cwd(tmp_path):
    result = subprocess.run([
        sys.executable, "-I", "-c",
        "import hashlib,json,dacn_s01; "
        "from dacn_s01.codec import parse_json,serialize_json; "
        "from dacn_s01.schema_resource import read_schema_bytes,load_schema; "
        "assert serialize_json(parse_json(b'9007199254740993'))==b'9007199254740993'; "
        "assert load_schema()['type']=='object'; "
        "print(json.dumps({'module':dacn_s01.__file__,"
        "'digest':hashlib.sha256(read_schema_bytes()).hexdigest()}))",
    ], cwd=tmp_path, capture_output=True, text=True, check=True)
    evidence = json.loads(result.stdout)
    assert "site-packages" in evidence["module"]
    assert "/src/" not in evidence["module"]
    assert evidence["digest"] == SCHEMA_SHA256
    provenance = files("dacn_s01").joinpath("schemas/input/1.0.0/PROVENANCE.md").read_text()
    assert SCHEMA_SHA256 in provenance
    assert "0.1.0-draft.2" in provenance
