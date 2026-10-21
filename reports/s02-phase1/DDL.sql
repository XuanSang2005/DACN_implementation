-- S02 structure 1; generated from the installed wheel, not executed against S01.
CREATE TABLE sessions (session_id TEXT PRIMARY KEY, spec_id TEXT NOT NULL, head_model_id TEXT, head_analysis_set_id TEXT, sequence INTEGER NOT NULL CHECK(sequence>=0), CHECK((head_model_id IS NULL)=(head_analysis_set_id IS NULL)), FOREIGN KEY(head_model_id,session_id) REFERENCES models(record_id,session_id) DEFERRABLE INITIALLY DEFERRED, FOREIGN KEY(head_analysis_set_id,head_model_id) REFERENCES analysis_sets(record_id,model_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE records (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id), type TEXT NOT NULL, created_at TEXT NOT NULL, record_json TEXT NOT NULL, sha256 TEXT NOT NULL, UNIQUE(id,session_id)) STRICT;

CREATE TABLE models (record_id TEXT PRIMARY KEY REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, session_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0), parent_id TEXT, source_context_id TEXT NOT NULL REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, UNIQUE(session_id,revision), UNIQUE(record_id,session_id), FOREIGN KEY(record_id,session_id) REFERENCES records(id,session_id) DEFERRABLE INITIALLY DEFERRED, FOREIGN KEY(parent_id,session_id) REFERENCES models(record_id,session_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE analysis_sets (record_id TEXT PRIMARY KEY REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, model_id TEXT NOT NULL REFERENCES models(record_id) DEFERRABLE INITIALLY DEFERRED, revision INTEGER NOT NULL CHECK(revision>0), parent_set_id TEXT, UNIQUE(model_id,revision), UNIQUE(record_id,model_id), FOREIGN KEY(parent_set_id,model_id) REFERENCES analysis_sets(record_id,model_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE artifacts (record_id TEXT PRIMARY KEY REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, producer_run_id TEXT REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, sha256 TEXT NOT NULL, byte_length INTEGER NOT NULL CHECK(byte_length>=0), bytes BLOB NOT NULL CHECK(length(bytes)=byte_length)) STRICT;

CREATE TABLE operations (command_id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(session_id) DEFERRABLE INITIALLY DEFERRED, parent_command_id TEXT REFERENCES operations(command_id), reserved_run_id TEXT NOT NULL UNIQUE, request_json TEXT NOT NULL, sha256 TEXT NOT NULL) STRICT;

CREATE TABLE staged_blobs (command_id TEXT NOT NULL REFERENCES operations(command_id), blob_id TEXT NOT NULL UNIQUE, media_type TEXT NOT NULL, purpose TEXT NOT NULL, sha256 TEXT NOT NULL, byte_length INTEGER NOT NULL CHECK(byte_length>=0), bytes BLOB NOT NULL CHECK(length(bytes)=byte_length), PRIMARY KEY(command_id,blob_id)) STRICT;

CREATE TABLE operation_events (event_id TEXT PRIMARY KEY, command_id TEXT NOT NULL REFERENCES operations(command_id), ordinal INTEGER NOT NULL CHECK(ordinal>0), kind TEXT NOT NULL, payload_json TEXT NOT NULL, sha256 TEXT NOT NULL, answer_id TEXT REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, UNIQUE(command_id,ordinal), UNIQUE(command_id,event_id)) STRICT;

CREATE UNIQUE INDEX one_finalized ON operation_events(command_id) WHERE kind='finalized';

CREATE UNIQUE INDEX one_applied ON operation_events(answer_id) WHERE kind='application_applied';

CREATE TABLE promotions (command_id TEXT NOT NULL, blob_id TEXT NOT NULL, artifact_id TEXT NOT NULL UNIQUE REFERENCES artifacts(record_id) DEFERRABLE INITIALLY DEFERRED, PRIMARY KEY(command_id,blob_id), FOREIGN KEY(command_id,blob_id) REFERENCES staged_blobs(command_id,blob_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE application_heads (answer_id TEXT PRIMARY KEY REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, active_command_id TEXT NOT NULL UNIQUE REFERENCES operations(command_id)) STRICT;

CREATE TABLE active_reviews (bundle_id TEXT PRIMARY KEY REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, review_id TEXT NOT NULL UNIQUE REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE record_links (owner_id TEXT NOT NULL REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, role TEXT NOT NULL, target_id TEXT NOT NULL REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, PRIMARY KEY(owner_id,role)) STRICT;

CREATE TABLE record_event_links (owner_id TEXT NOT NULL REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, role TEXT NOT NULL, command_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,event_id) REFERENCES operation_events(command_id,event_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE record_stage_links (owner_id TEXT NOT NULL REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, role TEXT NOT NULL, command_id TEXT NOT NULL, blob_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,blob_id) REFERENCES staged_blobs(command_id,blob_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE event_record_links (owner_id TEXT NOT NULL REFERENCES operation_events(event_id) DEFERRABLE INITIALLY DEFERRED, role TEXT NOT NULL, target_id TEXT NOT NULL REFERENCES records(id) DEFERRABLE INITIALLY DEFERRED, PRIMARY KEY(owner_id,role)) STRICT;

CREATE TABLE event_event_links (owner_id TEXT NOT NULL REFERENCES operation_events(event_id) DEFERRABLE INITIALLY DEFERRED, role TEXT NOT NULL, command_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,event_id) REFERENCES operation_events(command_id,event_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TABLE event_stage_links (owner_id TEXT NOT NULL REFERENCES operation_events(event_id) DEFERRABLE INITIALLY DEFERRED, role TEXT NOT NULL, command_id TEXT NOT NULL, blob_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,blob_id) REFERENCES staged_blobs(command_id,blob_id) DEFERRABLE INITIALLY DEFERRED) STRICT;

CREATE TRIGGER immutable_records_update BEFORE UPDATE ON records BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_records_delete BEFORE DELETE ON records BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_models_update BEFORE UPDATE ON models BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_models_delete BEFORE DELETE ON models BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_analysis_sets_update BEFORE UPDATE ON analysis_sets BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_analysis_sets_delete BEFORE DELETE ON analysis_sets BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_artifacts_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_artifacts_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_operations_update BEFORE UPDATE ON operations BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_operations_delete BEFORE DELETE ON operations BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_staged_blobs_update BEFORE UPDATE ON staged_blobs BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_staged_blobs_delete BEFORE DELETE ON staged_blobs BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_operation_events_update BEFORE UPDATE ON operation_events BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_operation_events_delete BEFORE DELETE ON operation_events BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_promotions_update BEFORE UPDATE ON promotions BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_promotions_delete BEFORE DELETE ON promotions BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_record_links_update BEFORE UPDATE ON record_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_record_links_delete BEFORE DELETE ON record_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_record_event_links_update BEFORE UPDATE ON record_event_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_record_event_links_delete BEFORE DELETE ON record_event_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_record_stage_links_update BEFORE UPDATE ON record_stage_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_record_stage_links_delete BEFORE DELETE ON record_stage_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_event_record_links_update BEFORE UPDATE ON event_record_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_event_record_links_delete BEFORE DELETE ON event_record_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_event_event_links_update BEFORE UPDATE ON event_event_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_event_event_links_delete BEFORE DELETE ON event_event_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_event_stage_links_update BEFORE UPDATE ON event_stage_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER immutable_event_stage_links_delete BEFORE DELETE ON event_stage_links BEGIN SELECT RAISE(ABORT,'immutable history'); END;

CREATE TRIGGER session_identity BEFORE UPDATE ON sessions WHEN NEW.session_id != OLD.session_id OR NEW.spec_id != OLD.spec_id OR NEW.sequence < OLD.sequence BEGIN SELECT RAISE(ABORT,'immutable session identity'); END;

CREATE TRIGGER session_no_delete BEFORE DELETE ON sessions BEGIN SELECT RAISE(ABORT,'immutable session'); END;
