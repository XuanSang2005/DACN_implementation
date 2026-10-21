CREATE TABLE schema_artifacts (
        digest TEXT PRIMARY KEY CHECK(length(digest) = 64),
        raw_schema BLOB NOT NULL
    ) STRICT;

CREATE TABLE sources (
        source_id TEXT PRIMARY KEY CHECK(length(source_id) > 0),
        raw_input BLOB NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('json_file','api','form')),
        label_json TEXT NOT NULL
    ) STRICT;

CREATE TABLE runs (
        run_id TEXT PRIMARY KEY CHECK(length(run_id) > 0),
        source_id TEXT NOT NULL UNIQUE REFERENCES sources(source_id),
        request_json TEXT NOT NULL,
        envelope_json TEXT NOT NULL,
        schema_digest TEXT REFERENCES schema_artifacts(digest),
        snapshot_id TEXT REFERENCES snapshots(snapshot_id) DEFERRABLE INITIALLY DEFERRED
    ) STRICT;

CREATE TABLE snapshots (
        snapshot_id TEXT PRIMARY KEY CHECK(length(snapshot_id) > 0),
        spec_id TEXT NOT NULL REFERENCES specs(spec_id) DEFERRABLE INITIALLY DEFERRED,
        revision INTEGER NOT NULL CHECK(revision >= 1),
        parent_snapshot_id TEXT REFERENCES snapshots(snapshot_id),
        origin_source_id TEXT NOT NULL REFERENCES sources(source_id),
        created_by_run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id),
        snapshot_json TEXT NOT NULL,
        UNIQUE(spec_id, revision), UNIQUE(snapshot_id, spec_id),
        CHECK((revision = 1 AND parent_snapshot_id IS NULL) OR
              (revision > 1 AND parent_snapshot_id IS NOT NULL))
    ) STRICT;

CREATE TABLE specs (
        spec_id TEXT PRIMARY KEY CHECK(length(spec_id) > 0),
        head_snapshot_id TEXT NOT NULL,
        FOREIGN KEY(head_snapshot_id, spec_id) REFERENCES snapshots(snapshot_id, spec_id)
            DEFERRABLE INITIALLY DEFERRED
    ) STRICT;

CREATE TRIGGER snapshot_parent BEFORE INSERT ON snapshots
        WHEN NEW.revision > 1 AND NOT EXISTS (
            SELECT 1 FROM snapshots p JOIN specs s ON s.spec_id = p.spec_id
            WHERE p.snapshot_id = NEW.parent_snapshot_id AND p.spec_id = NEW.spec_id
              AND p.revision = NEW.revision - 1 AND s.head_snapshot_id = p.snapshot_id)
        BEGIN SELECT RAISE(ABORT, 'parent must be current head of same spec'); END;

CREATE TRIGGER spec_initial_head BEFORE INSERT ON specs
        WHEN NOT EXISTS (SELECT 1 FROM snapshots WHERE snapshot_id = NEW.head_snapshot_id
            AND spec_id = NEW.spec_id AND revision = 1 AND parent_snapshot_id IS NULL)
        BEGIN SELECT RAISE(ABORT, 'initial head must be revision one'); END;

CREATE TRIGGER spec_advance BEFORE UPDATE ON specs
        WHEN NEW.spec_id != OLD.spec_id OR NOT EXISTS (
            SELECT 1 FROM snapshots n JOIN snapshots p ON p.snapshot_id = OLD.head_snapshot_id
            WHERE n.snapshot_id = NEW.head_snapshot_id AND n.spec_id = OLD.spec_id
              AND n.parent_snapshot_id = p.snapshot_id AND n.revision = p.revision + 1)
        BEGIN SELECT RAISE(ABORT, 'head must advance exactly one revision'); END;

CREATE TRIGGER spec_no_delete BEFORE DELETE ON specs
        BEGIN SELECT RAISE(ABORT, 'spec history cannot be deleted'); END;

CREATE TRIGGER schema_artifacts_no_update BEFORE UPDATE ON schema_artifacts BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER schema_artifacts_no_delete BEFORE DELETE ON schema_artifacts BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER sources_no_update BEFORE UPDATE ON sources BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER sources_no_delete BEFORE DELETE ON sources BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER runs_no_update BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER runs_no_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER snapshots_no_update BEFORE UPDATE ON snapshots BEGIN SELECT RAISE(ABORT, 'immutable record'); END;

CREATE TRIGGER snapshots_no_delete BEFORE DELETE ON snapshots BEGIN SELECT RAISE(ABORT, 'immutable record'); END;
