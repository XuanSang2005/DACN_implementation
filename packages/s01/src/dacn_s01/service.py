"""S01 orchestration through durable results; no CLI, receipt, API or S02."""

from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from importlib import metadata, resources
import sqlite3
import sys
from uuid import uuid4

from .codec import CodecError, parse_json, serialize_json
from .envelope import EnvelopeInvariantError, check_envelope
from .errors import error, ordered_errors
from .repository import Repository, RepositoryError, TransactionError
from .revision import decide_revision, inspect_request
from .schema_resource import PROFILE_VERSION, read_schema_bytes
from .validation import InputValidation, validate_input


class RunIDAlreadyUsed(RepositoryError):
    """A supplied/issued correlation ID must never overwrite an existing run."""


@lru_cache(maxsize=1)
def validator_build():
    """Identify code/profile and actual dependency versions; manifest has full artifacts."""
    digest = hashlib.sha256()
    package = resources.files("dacn_s01")
    for item in sorted(package.iterdir(), key=lambda p: p.name):
        if item.name.endswith(".py"):
            digest.update(item.name.encode() + b"\0" + item.read_bytes() + b"\0")
    for name in ("dacn-s01", "jsonschema", "simplejson", "attrs", "jsonschema-specifications", "referencing", "rpds-py"):
        digest.update(f"{name}={metadata.version(name)}\0".encode())
    digest.update(f"{sys.version}\0{sqlite3.sqlite_version}\0{PROFILE_VERSION}".encode())
    return f"dacn-s01/{metadata.version('dacn-s01')}+sha256:{digest.hexdigest()}"


def _timestamp(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Clock must return an aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Service:
    def __init__(self, repository: Repository, *, _clock=None, _ids=None):
        self.repository = repository
        self._clock = _clock or (lambda: datetime.now(timezone.utc))
        self._ids = _ids or (lambda kind: str(uuid4()))

    def allocate_run_id(self):
        """No database write: phase 4 may publish a receipt before submit().

        Not an idempotency key, reservation or receipt implementation. Caller must
        preserve this ID and must not submit it again to recover a lost response.
        """
        value = self._ids("run")
        if type(value) is not str or not value:
            raise ValueError("Run ID generator must return a nonempty string")
        return value

    def submit(self, raw: bytes, request, *, run_id=None, source_kind="json_file", source_label=None):
        """Synchronous bytes intake. Returns a contract envelope; no automatic resubmit.

        raw and request must be exact codec-supported values. Original request
        JSON is captured before checks; illegal JSON shapes remain auditable.
        A failed response does not promise its correlation ID was persisted.
        """
        if type(raw) is not bytes:
            raise TypeError("Raw input must be immutable bytes")
        if source_kind not in ("json_file", "api", "form") or (source_label is not None and type(source_label) is not str):
            raise ValueError("Invalid source metadata supplied by adapter")
        run_id = self.allocate_run_id() if run_id is None else run_id
        if type(run_id) is not str or not run_id:
            raise ValueError("Run ID must be a nonempty string")
        received = _timestamp(self._clock())
        result = InputValidation()
        original = projected = None
        source = {"source_id": str(uuid4()), "kind": source_kind, "label": source_label}
        schema = None

        def envelope(kind=None, snapshot=None):
            issues = ordered_errors(result.errors)
            status = "failed" if any(e["stage"] == "system" for e in issues) else "rejected" if issues else "validated"
            return {"output_contract_version": PROFILE_VERSION, "status": status,
                    "result_kind": kind if status == "validated" else None,
                    "run": {"run_id": run_id, "received_at": received,
                            "completed_at": max(received, _timestamp(self._clock())),
                            "validator_version": validator_build(), "input_schema_sha256": result.input_schema_sha256,
                            "request": deepcopy(projected), "source": dict(source),
                            "input_version": deepcopy(result.input_version), "normalizations": deepcopy(result.normalizations),
                            "validation": {"checks": dict(result.checks), "errors": issues}},
                    "snapshot": snapshot if status == "validated" else None,
                    "handoff": {"eligible_for_s02": status == "validated",
                                "snapshot_id": snapshot["snapshot_id"] if status == "validated" else None}}

        def failure(code, reason):
            safe_errors = []
            diagnostics_unrepresentable = False
            for issue in result.errors:
                try:
                    serialize_json(issue)
                except CodecError:
                    diagnostics_unrepresentable = True
                else:
                    safe_errors.append(issue)
            if diagnostics_unrepresentable:
                # Never repair source Unicode or repeat the diagnostic that
                # made the candidate unencodable. The raw BLOB remains intact;
                # representable diagnostics retain their original values.
                safe_errors.append(error("PROCESSING_FAILED", "system", None,
                    "S01 could not represent validation diagnostics exactly",
                    {"reason": "One or more diagnostics could not be represented exactly; original input was not altered"},
                    target="system"))
            result.errors = ordered_errors([*safe_errors,
                error(code, "system", None, "S01 could not complete reliably", {"reason": reason}, target="system")])
            value = envelope()
            check_envelope(value)
            return value

        try:
            original = parse_json(serialize_json(request))  # Copy without coercion/float/defaults.
            projected, request_errors = inspect_request(original)
            result = validate_input(raw)
            if result.input_schema_sha256 is not None:
                schema = read_schema_bytes()
        except (CodecError, EnvelopeInvariantError, ValueError, TypeError) as exc:
            # An unsupported internal request cannot be faithfully archived as JSON.
            # Do not invent a replacement request or claim an audit record exists.
            return failure("PROCESSING_FAILED", "Intake context or schema could not be represented exactly; run not recorded")

        try:
            with self.repository.transaction() as connection:
                if connection.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():
                    raise RunIDAlreadyUsed("Run ID already used; use lookup, not resubmission")
                source["source_id"] = self.repository.fresh_id(connection, "sources", "source_id", lambda: self._ids("source"))
                kind = snapshot = None
                if result.outcome == "passed":
                    if request_errors:
                        result.checks["revision"] = "failed"
                        result.errors = request_errors
                    else:
                        head = self.repository.head(connection, projected["spec_id"]) if projected["mode"] == "update" else None
                        decision = decide_revision(projected, result.normalized_input, head)
                        result.errors = list(decision.errors)
                        result.checks["revision"] = "failed" if result.errors else "passed"
                        kind = decision.result_kind
                        if kind == "unchanged":
                            snapshot = head
                        elif kind is not None:
                            spec_id = head["spec_id"] if head else self.repository.fresh_id(
                                connection, "specs", "spec_id", lambda: self._ids("spec"))
                            snapshot = {"spec_id": spec_id, "revision": int(head["revision"]) + 1 if head else 1,
                                "snapshot_id": self.repository.fresh_id(connection, "snapshots", "snapshot_id", lambda: self._ids("snapshot")),
                                "parent_snapshot_id": head["snapshot_id"] if head else None,
                                "created_by_run_id": run_id, "origin_source_id": source["source_id"],
                                "input": result.normalized_input}
                candidate = envelope(kind, snapshot)
                self.repository._hook("after_decision", connection)
                self.repository.store(connection, raw, original, candidate, schema)
        except TransactionError as exc:
            if exc.uncertain:
                try:
                    committed = self.repository.get_run(run_id)  # New connection, original transaction closed.
                    if committed is not None and committed["run"]["source"]["source_id"] == source["source_id"]:
                        return committed
                except Exception:
                    pass
                return failure("PERSISTENCE_FAILED", "Commit outcome is unresolved; reconcile this run ID before any new submission")
            if isinstance(exc.cause, RunIDAlreadyUsed):
                return failure("PERSISTENCE_FAILED", "Run ID already used; existing record unchanged, this attempt not recorded")
            code = "PROCESSING_FAILED" if isinstance(exc.cause, (CodecError, EnvelopeInvariantError)) else "PERSISTENCE_FAILED"
            failed = failure(code, "Transaction did not commit; failed audit record may be unavailable")
            # One attempt to archive the failure, never repeat the business submit.
            try:
                with self.repository.transaction() as connection:
                    self.repository.store(connection, raw, original, failed, schema)
                saved = self.repository.get_run(run_id)
                return saved if saved is not None else failed
            except TransactionError as recovery:
                if recovery.uncertain:
                    try:
                        saved = self.repository.get_run(run_id)
                        if saved is not None and saved["run"]["source"]["source_id"] == source["source_id"]:
                            return saved
                    except Exception:
                        pass
                return failed
            except Exception:
                return failed
        try:
            committed = self.repository.get_run(run_id)
            if committed is None:
                raise RepositoryError("Committed run cannot be located")
            return committed
        except Exception:
            # Commit was acknowledged. Never overwrite its run with a failure.
            return failure("PERSISTENCE_FAILED", "Commit acknowledged but stored result could not be verified; reconcile by run ID")
