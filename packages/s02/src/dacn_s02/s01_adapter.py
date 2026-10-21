"""Checked, selected S01 run intake. Never initialize/submit/read private SQL."""
from dataclasses import dataclass
import hashlib
from importlib.metadata import version
from dacn_s01.repository import Repository
from dacn_s01.envelope import check_envelope
from dacn_s01.schema_resource import read_schema_bytes, SCHEMA_SHA256
from dacn_s01.revision import json_equal
from .codec_boundary import encode,decode
from .errors import S02Error, require

@dataclass(frozen=True)
class Intake:
    envelope: dict
    envelope_bytes: bytes
    run_source: bytes
    origin_source: bytes
    schema: bytes

def intake(path,run_id,expected_snapshot_id=None):
    try:
        require(version("dacn-s01")=="0.1.0a6","s01_package_baseline")
        repo=Repository(path);repo.verify();env=repo.get_run(run_id)
        if env is None: raise S02Error("SOURCE_NOT_FOUND","intake","Selected S01 run not found",details={"run_id":run_id,"reason":"Checked lookup returned no run"})
        check_envelope(env)
        eligible=(env["output_contract_version"]=="0.1.0-draft.2" and env["status"]=="validated"
                  and env["handoff"]["eligible_for_s02"] and all(v=="passed" for v in env["run"]["validation"]["checks"].values())
                  and env["run"]["input_schema_sha256"]==SCHEMA_SHA256)
        if not eligible: raise S02Error("SOURCE_NOT_ELIGIBLE","intake","Selected S01 run is not eligible",details={"run_id":run_id,"reason":"Contract/status/checks/schema eligibility"})
        snap=env["snapshot"]
        require(expected_snapshot_id is None or snap["snapshot_id"]==expected_snapshot_id,"expected_snapshot")
        require(snap["input"]["schema_version"]=="1.0.0","input_schema_version")
        require(json_equal(repo.get_snapshot(snap["snapshot_id"]),snap),"selected_snapshot_lookup")
        creator=repo.get_run(snap["created_by_run_id"])
        require(creator is not None and creator["run"]["source"]["source_id"]==snap["origin_source_id"],"origin_creator")
        raw=repo.get_source(env["run"]["source"]["source_id"]);origin=repo.get_source(snap["origin_source_id"])
        schema=read_schema_bytes();require(hashlib.sha256(schema).hexdigest()==SCHEMA_SHA256,"schema_digest")
        require(json_equal(repo.get_run(run_id),env),"s01_intake_stable")
        return Intake(env,encode(env),raw,origin,schema)
    except S02Error: raise
    except Exception as exc:
        raise S02Error("PROCESSING_FAILED","persistence","S01 checked intake failed",details={"reason":type(exc).__name__}) from exc

def verify_archive(context,records,blobs):
    """Recheck local archive values, never reopening/replacing the S01 source."""
    b=context["body"];env=decode(blobs[b["envelope_artifact_id"]]);check_envelope(env)
    require(env["status"]=="validated" and env["output_contract_version"]=="0.1.0-draft.2","archive_eligible")
    require(env["run"]["run_id"]==b["s01_run_id"] and env["snapshot"]["snapshot_id"]==b["snapshot_id"],"archive_context_binding")
    require(hashlib.sha256(blobs[b["schema_artifact_id"]]).hexdigest()==SCHEMA_SHA256==env["run"]["input_schema_sha256"],"archive_schema")
    for key in ("run_source_artifact_id","origin_source_artifact_id"):
        value=decode(blobs[b[key]])
        if type(value) is dict and "schema_version" not in value: value={**value,"schema_version":"1.0.0"}
        require(json_equal(value,env["snapshot"]["input"]),"archive_raw_snapshot")
    same=env["run"]["source"]["source_id"]==env["snapshot"]["origin_source_id"]
    require((b["run_source_artifact_id"]==b["origin_source_artifact_id"])==same,"archive_source_identity")
    return env["snapshot"]
