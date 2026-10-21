"""S02-only structure 1. Exact DDL is checked on every connection."""
APPLICATION_ID = 0x44414332
DB_VERSION = 1
DDL = {}
def table(name, columns): DDL[name]=f"CREATE TABLE {name} ({columns}) STRICT"
FK="DEFERRABLE INITIALLY DEFERRED"
table("sessions",f"session_id TEXT PRIMARY KEY, spec_id TEXT NOT NULL, head_model_id TEXT, head_analysis_set_id TEXT, sequence INTEGER NOT NULL CHECK(sequence>=0), CHECK((head_model_id IS NULL)=(head_analysis_set_id IS NULL)), FOREIGN KEY(head_model_id,session_id) REFERENCES models(record_id,session_id) {FK}, FOREIGN KEY(head_analysis_set_id,head_model_id) REFERENCES analysis_sets(record_id,model_id) {FK}")
table("records",f"id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id), type TEXT NOT NULL, created_at TEXT NOT NULL, record_json TEXT NOT NULL, sha256 TEXT NOT NULL, UNIQUE(id,session_id)")
table("models",f"record_id TEXT PRIMARY KEY REFERENCES records(id) {FK}, session_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0), parent_id TEXT, source_context_id TEXT NOT NULL REFERENCES records(id) {FK}, UNIQUE(session_id,revision), UNIQUE(record_id,session_id), FOREIGN KEY(record_id,session_id) REFERENCES records(id,session_id) {FK}, FOREIGN KEY(parent_id,session_id) REFERENCES models(record_id,session_id) {FK}")
table("analysis_sets",f"record_id TEXT PRIMARY KEY REFERENCES records(id) {FK}, model_id TEXT NOT NULL REFERENCES models(record_id) {FK}, revision INTEGER NOT NULL CHECK(revision>0), parent_set_id TEXT, UNIQUE(model_id,revision), UNIQUE(record_id,model_id), FOREIGN KEY(parent_set_id,model_id) REFERENCES analysis_sets(record_id,model_id) {FK}")
table("artifacts",f"record_id TEXT PRIMARY KEY REFERENCES records(id) {FK}, producer_run_id TEXT REFERENCES records(id) {FK}, sha256 TEXT NOT NULL, byte_length INTEGER NOT NULL CHECK(byte_length>=0), bytes BLOB NOT NULL CHECK(length(bytes)=byte_length)")
table("operations",f"command_id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(session_id) {FK}, parent_command_id TEXT REFERENCES operations(command_id), reserved_run_id TEXT NOT NULL UNIQUE, request_json TEXT NOT NULL, sha256 TEXT NOT NULL")
table("staged_blobs",f"command_id TEXT NOT NULL REFERENCES operations(command_id), blob_id TEXT NOT NULL UNIQUE, media_type TEXT NOT NULL, purpose TEXT NOT NULL, sha256 TEXT NOT NULL, byte_length INTEGER NOT NULL CHECK(byte_length>=0), bytes BLOB NOT NULL CHECK(length(bytes)=byte_length), PRIMARY KEY(command_id,blob_id)")
table("operation_events",f"event_id TEXT PRIMARY KEY, command_id TEXT NOT NULL REFERENCES operations(command_id), ordinal INTEGER NOT NULL CHECK(ordinal>0), kind TEXT NOT NULL, payload_json TEXT NOT NULL, sha256 TEXT NOT NULL, answer_id TEXT REFERENCES records(id) {FK}, UNIQUE(command_id,ordinal), UNIQUE(command_id,event_id)")
DDL["one_finalized"]="CREATE UNIQUE INDEX one_finalized ON operation_events(command_id) WHERE kind='finalized'"
DDL["one_applied"]="CREATE UNIQUE INDEX one_applied ON operation_events(answer_id) WHERE kind='application_applied'"
table("promotions",f"command_id TEXT NOT NULL, blob_id TEXT NOT NULL, artifact_id TEXT NOT NULL UNIQUE REFERENCES artifacts(record_id) {FK}, PRIMARY KEY(command_id,blob_id), FOREIGN KEY(command_id,blob_id) REFERENCES staged_blobs(command_id,blob_id) {FK}")
table("application_heads",f"answer_id TEXT PRIMARY KEY REFERENCES records(id) {FK}, active_command_id TEXT NOT NULL UNIQUE REFERENCES operations(command_id)")
table("active_reviews",f"bundle_id TEXT PRIMARY KEY REFERENCES records(id) {FK}, review_id TEXT NOT NULL UNIQUE REFERENCES records(id) {FK}")
table("record_links",f"owner_id TEXT NOT NULL REFERENCES records(id) {FK}, role TEXT NOT NULL, target_id TEXT NOT NULL REFERENCES records(id) {FK}, PRIMARY KEY(owner_id,role)")
table("record_event_links",f"owner_id TEXT NOT NULL REFERENCES records(id) {FK}, role TEXT NOT NULL, command_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,event_id) REFERENCES operation_events(command_id,event_id) {FK}")
table("record_stage_links",f"owner_id TEXT NOT NULL REFERENCES records(id) {FK}, role TEXT NOT NULL, command_id TEXT NOT NULL, blob_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,blob_id) REFERENCES staged_blobs(command_id,blob_id) {FK}")
table("event_record_links",f"owner_id TEXT NOT NULL REFERENCES operation_events(event_id) {FK}, role TEXT NOT NULL, target_id TEXT NOT NULL REFERENCES records(id) {FK}, PRIMARY KEY(owner_id,role)")
table("event_event_links",f"owner_id TEXT NOT NULL REFERENCES operation_events(event_id) {FK}, role TEXT NOT NULL, command_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,event_id) REFERENCES operation_events(command_id,event_id) {FK}")
table("event_stage_links",f"owner_id TEXT NOT NULL REFERENCES operation_events(event_id) {FK}, role TEXT NOT NULL, command_id TEXT NOT NULL, blob_id TEXT NOT NULL, PRIMARY KEY(owner_id,role), FOREIGN KEY(command_id,blob_id) REFERENCES staged_blobs(command_id,blob_id) {FK}")
for name in list(DDL):
    if not DDL[name].startswith("CREATE TABLE") or name in ("sessions","application_heads","active_reviews"): continue
    for action in ("UPDATE","DELETE"):
        trigger=f"immutable_{name}_{action.lower()}"
        DDL[trigger]=f"CREATE TRIGGER {trigger} BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT,'immutable history'); END"
DDL["session_identity"]="CREATE TRIGGER session_identity BEFORE UPDATE ON sessions WHEN NEW.session_id != OLD.session_id OR NEW.spec_id != OLD.spec_id OR NEW.sequence < OLD.sequence BEGIN SELECT RAISE(ABORT,'immutable session identity'); END"
DDL["session_no_delete"]="CREATE TRIGGER session_no_delete BEFORE DELETE ON sessions BEGIN SELECT RAISE(ABORT,'immutable session'); END"
