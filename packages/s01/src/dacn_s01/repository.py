"""Explicit SQLite transactions and checked lookups; no transport or auto-reset."""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3

from .codec import JSONValue, parse_json, serialize_json
from .envelope import check_envelope
from .revision import inspect_request, json_equal
from .storage_schema import APPLICATION_ID, DB_VERSION, DDL
from .validation import validate_input


class RepositoryError(Exception):
    """Controlled storage/configuration failure, never an input rejection."""


class IntegrityError(RepositoryError):
    """Stored records contradict one another or the supported structure."""


class TransactionError(RepositoryError):
    def __init__(self, cause: Exception, uncertain: bool):
        super().__init__("Transaction outcome requires reconciliation" if uncertain else "Transaction did not commit")
        self.cause, self.uncertain = cause, uncertain


def _require(condition, message):
    if not condition:
        raise IntegrityError(message)


def _text(value):
    return serialize_json(value).decode("ascii")


def _json(value):
    return parse_json(value.encode("utf-8"))


class Repository:
    """One local file; every operation owns and closes its own connection.

    initialize() is explicit. Lookup never creates a missing DB. _hook is a
    private test seam; it is not a product option or a retry policy.
    """

    def __init__(self, path: str | Path, *, timeout: float = 5.0, _hook=None):
        self.path = Path(path).resolve()
        if timeout < 0:
            raise ValueError("Timeout must be nonnegative")
        self.timeout = timeout
        self._hook = _hook or (lambda point, connection: None)

    def _connect(self, *, create=False):
        connection = sqlite3.connect(self.path.as_uri() + ("?mode=rwc" if create else "?mode=rw"),
                                     uri=True, autocommit=True, timeout=self.timeout)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            _require(connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "Foreign keys unavailable")
            _require(connection.execute("PRAGMA synchronous").fetchone()[0] == 2, "FULL synchronization unavailable")
            return connection
        except Exception:
            connection.close()
            raise

    def _verify_structure(self, connection):
        _require(connection.execute("PRAGMA application_id").fetchone()[0] == APPLICATION_ID,
                 "Not a DACN S01 database")
        _require(connection.execute("PRAGMA user_version").fetchone()[0] == DB_VERSION,
                 "Unsupported database structure version; no reset or migration performed")
        actual = dict(connection.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        _require(actual == DDL, "Database structure differs from supported version")
        _require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "Expected DELETE journal mode")

    def initialize(self):
        """Create only an empty, unclaimed database; leave foreign/newer DBs alone."""
        connection = self._connect(create=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            app = connection.execute("PRAGMA application_id").fetchone()[0]
            objects = connection.execute("SELECT name FROM sqlite_master").fetchall()
            if version == 0 and app == 0 and not objects:
                _require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "Expected DELETE journal mode")
                for statement in DDL.values():
                    connection.execute(statement)
                connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version={DB_VERSION}")
            self._verify_structure(connection)
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        connection = None
        commit_attempted = False
        try:
            connection = self._connect()
            self._verify_structure(connection)
            self._hook("before_begin", connection)
            connection.execute("BEGIN IMMEDIATE")
            self._hook("after_begin", connection)
            yield connection
            self._hook("before_commit", connection)
            commit_attempted = True
            connection.execute("COMMIT")
            self._hook("after_commit", connection)
        except Exception as cause:
            uncertain = commit_attempted
            if connection is not None:
                try:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                        uncertain = False  # Explicit rollback acknowledged, including COMMIT BUSY.
                except Exception:
                    uncertain = True
            raise TransactionError(cause, uncertain) from cause
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def _read(self):
        connection = self._connect()
        try:
            self._verify_structure(connection)
            connection.execute("BEGIN")  # One consistent view across related records.
            yield connection
        finally:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            connection.close()

    def fresh_id(self, connection, table, column, generator):
        # Table/column are internal constants, not caller SQL or input fields.
        for _ in range(8):
            value = generator()
            _require(type(value) is str and bool(value), "ID generator returned an invalid ID")
            if connection.execute(f"SELECT 1 FROM {table} WHERE {column}=?", (value,)).fetchone() is None:
                return value
        raise IntegrityError("ID generator repeatedly collided; no history overwritten")

    def store(self, connection, raw: bytes, original_request: JSONValue, envelope: dict, schema: bytes | None):
        """Write a final candidate; caller must own the IMMEDIATE transaction."""
        _require(connection.in_transaction, "Write requires an explicit transaction")
        check_envelope(envelope)
        run, snapshot = envelope["run"], envelope["snapshot"]
        self._hook("before_insert", connection)
        digest = run["input_schema_sha256"]
        if digest is not None:
            _require(schema is not None and hashlib.sha256(schema).hexdigest() == digest, "Schema artifact mismatch")
            existing = connection.execute("SELECT raw_schema FROM schema_artifacts WHERE digest=?", (digest,)).fetchone()
            if existing is None:
                connection.execute("INSERT INTO schema_artifacts VALUES (?,?)", (digest, schema))
            else:
                _require(existing[0] == schema, "Archived schema bytes differ")
        source = run["source"]
        connection.execute("INSERT INTO sources VALUES (?,?,?,?)",
                           (source["source_id"], raw, source["kind"], _text(source["label"])))
        self._hook("after_source_insert", connection)
        connection.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (
            run["run_id"], source["source_id"], _text(original_request), _text(envelope), digest,
            snapshot["snapshot_id"] if snapshot else None))
        if snapshot is not None and envelope["result_kind"] != "unchanged":
            connection.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)", (
                snapshot["snapshot_id"], snapshot["spec_id"], int(snapshot["revision"]),
                snapshot["parent_snapshot_id"], snapshot["origin_source_id"], snapshot["created_by_run_id"], _text(snapshot)))
            self._hook("after_snapshot_insert", connection)
            if envelope["result_kind"] == "new_spec":
                connection.execute("INSERT INTO specs VALUES (?,?)", (snapshot["spec_id"], snapshot["snapshot_id"]))
            else:
                changed = connection.execute("UPDATE specs SET head_snapshot_id=? WHERE spec_id=? AND head_snapshot_id=?",
                    (snapshot["snapshot_id"], snapshot["spec_id"], snapshot["parent_snapshot_id"]))
                _require(changed.rowcount == 1, "Head changed during transaction")
        self._hook("after_records", connection)
        if snapshot is not None:
            head = connection.execute("SELECT head_snapshot_id FROM specs WHERE spec_id=?", (snapshot["spec_id"],)).fetchone()
            _require(head is not None and head[0] == snapshot["snapshot_id"], "Result must match the transaction head")
        self.checked_run(connection, run["run_id"])
        _require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "Foreign key check failed")

    def _snapshot(self, connection, snapshot_id):
        row = connection.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        _require(row is not None, "Referenced snapshot missing")
        snapshot = _json(row["snapshot_json"])
        for name in ("snapshot_id", "spec_id", "revision", "parent_snapshot_id", "origin_source_id", "created_by_run_id"):
            _require(type(snapshot) is dict and snapshot.get(name) == row[name], "Snapshot metadata mismatch")
        if row["parent_snapshot_id"] is not None:
            parent = connection.execute("SELECT spec_id, revision FROM snapshots WHERE snapshot_id=?",
                                        (row["parent_snapshot_id"],)).fetchone()
            _require(parent is not None and parent["spec_id"] == row["spec_id"]
                     and parent["revision"] + 1 == row["revision"], "Snapshot parent mismatch")
        spec = connection.execute("SELECT head_snapshot_id FROM specs WHERE spec_id=?", (row["spec_id"],)).fetchone()
        _require(spec is not None, "Snapshot specification missing")
        head = connection.execute("SELECT spec_id, revision FROM snapshots WHERE snapshot_id=?", (spec[0],)).fetchone()
        _require(head is not None and head["spec_id"] == row["spec_id"] and head["revision"] >= row["revision"], "Invalid specification head")
        creator = connection.execute("SELECT * FROM runs WHERE run_id=?", (row["created_by_run_id"],)).fetchone()
        _require(creator is not None and creator["source_id"] == row["origin_source_id"]
                 and creator["snapshot_id"] == snapshot_id, "Snapshot creator mismatch")
        created_envelope = _json(creator["envelope_json"])
        check_envelope(created_envelope)
        _require(created_envelope["result_kind"] in ("new_spec", "new_revision")
                 and json_equal(created_envelope["snapshot"], snapshot), "Creator envelope differs from snapshot")
        self._run_links(connection, creator, created_envelope)
        return snapshot

    def _run_links(self, connection, row, envelope):
        run = envelope["run"]
        _require(run["run_id"] == row["run_id"] and run["source"]["source_id"] == row["source_id"]
                 and run["input_schema_sha256"] == row["schema_digest"], "Run metadata mismatch")
        projected, _ = inspect_request(_json(row["request_json"]))
        _require(json_equal(projected, run["request"]), "Original request does not match run projection")
        source = connection.execute("SELECT * FROM sources WHERE source_id=?", (row["source_id"],)).fetchone()
        _require(source is not None and type(source["raw_input"]) is bytes, "Run source missing or not raw bytes")
        _require(source["kind"] == run["source"]["kind"] and _json(source["label_json"]) == run["source"]["label"], "Source metadata mismatch")
        if row["schema_digest"] is not None:
            artifact = connection.execute("SELECT raw_schema FROM schema_artifacts WHERE digest=?", (row["schema_digest"],)).fetchone()
            _require(artifact is not None and hashlib.sha256(artifact[0]).hexdigest() == row["schema_digest"], "Schema artifact missing or corrupt")
        snapshot = envelope["snapshot"]
        _require(row["snapshot_id"] == (snapshot["snapshot_id"] if snapshot else None), "Run snapshot link mismatch")
        if envelope["status"] == "validated":
            checked = validate_input(source["raw_input"])
            _require(checked.outcome == "passed" and json_equal(checked.normalized_input, snapshot["input"]), "Source does not produce stored snapshot")
            _require(json_equal(checked.input_version, run["input_version"])
                     and json_equal(checked.normalizations, run["normalizations"]), "Source normalization provenance differs")

    def checked_run(self, connection, run_id):
        row = connection.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        envelope = _json(row["envelope_json"])
        check_envelope(envelope)
        self._run_links(connection, row, envelope)
        if row["snapshot_id"] is not None:
            stored = self._snapshot(connection, row["snapshot_id"])
            _require(json_equal(stored, envelope["snapshot"]), "Envelope snapshot differs from persisted snapshot")
        return envelope

    def head(self, connection, spec_id):
        try:
            row = connection.execute("SELECT head_snapshot_id FROM specs WHERE spec_id=?", (spec_id,)).fetchone()
        except UnicodeEncodeError:
            return None  # Such an ID cannot exist in a SQLite TEXT key; do not trim/coerce it.
        return self._snapshot(connection, row[0]) if row else None

    def get_run(self, run_id):
        with self._read() as connection:
            return self.checked_run(connection, run_id)

    def get_request(self, run_id):
        with self._read() as connection:
            if self.checked_run(connection, run_id) is None:
                return None
            return _json(connection.execute("SELECT request_json FROM runs WHERE run_id=?", (run_id,)).fetchone()[0])

    def get_snapshot(self, snapshot_id):
        with self._read() as connection:
            if connection.execute("SELECT 1 FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone() is None:
                return None
            return self._snapshot(connection, snapshot_id)

    def get_source(self, source_id):
        with self._read() as connection:
            row = connection.execute("SELECT raw_input FROM sources WHERE source_id=?", (source_id,)).fetchone()
            if row is None:
                return None
            run = connection.execute("SELECT run_id FROM runs WHERE source_id=?", (source_id,)).fetchone()
            _require(run is not None, "Orphan source")
            self.checked_run(connection, run[0])
            return row[0]

    def get_head(self, spec_id):
        with self._read() as connection:
            return self.head(connection, spec_id)

    def verify(self):
        """Verify an existing store without initializing it or creating a run."""
        with self._read():
            pass

    def get_snapshot_revision(self, spec_id, revision):
        """Resolve exactly the requested historical revision, never the head."""
        with self._read() as connection:
            row = connection.execute("SELECT snapshot_id FROM snapshots WHERE spec_id=? AND revision=?",
                                     (spec_id, revision)).fetchone()
            return self._snapshot(connection, row[0]) if row else None

    def list_runs(self, spec_id):
        """Checked envelopes related by snapshot or representable request.

        One read transaction; order by receipt timestamp then opaque run ID,
        not a claimed commit order. No JSON SQL extraction or mutable index.
        A missing specification can still have rejected SPEC_NOT_FOUND runs.
        """
        with self._read() as connection:
            selected = []
            for row in connection.execute("SELECT run_id FROM runs ORDER BY run_id"):
                value = self.checked_run(connection, row[0])
                request, snapshot = value["run"]["request"], value["snapshot"]
                if ((request is not None and request["spec_id"] == spec_id)
                        or (snapshot is not None and snapshot["spec_id"] == spec_id)):
                    selected.append(value)
            return sorted(selected, key=lambda value: (value["run"]["received_at"], value["run"]["run_id"]))
