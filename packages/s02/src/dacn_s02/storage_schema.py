"""Exact structure 2; structure 1 remains a read-only compatibility format."""
from .storage_schema_l1 import APPLICATION_ID, DDL as DDL1, FK
DB_VERSION = 2
DDL = dict(DDL1)
for name in ('records', 'operations'):
    DDL[name] = DDL[name].replace('sha256 TEXT NOT NULL',
        f'sha256 TEXT NOT NULL, profile_id TEXT NOT NULL REFERENCES schema_profiles(profile_id) {FK}')
def table(name, columns):
    DDL[name] = f'CREATE TABLE {name} ({columns}) STRICT'
table('schema_profiles', 'profile_id TEXT PRIMARY KEY NOT NULL, schema_bytes BLOB NOT NULL, schema_sha256 TEXT NOT NULL, descriptor_bytes BLOB NOT NULL, descriptor_sha256 TEXT NOT NULL')
table('store_metadata', f"slot INTEGER PRIMARY KEY CHECK(slot=1), store_id TEXT NOT NULL UNIQUE, write_profile_id TEXT NOT NULL REFERENCES schema_profiles(profile_id) {FK}, origin_kind TEXT NOT NULL CHECK(origin_kind IN ('fresh','migration')), migration_id TEXT UNIQUE, migration_manifest BLOB, manifest_sha256 TEXT, CHECK((origin_kind='fresh' AND migration_id IS NULL AND migration_manifest IS NULL AND manifest_sha256 IS NULL) OR (origin_kind='migration' AND migration_id IS NOT NULL AND migration_manifest IS NOT NULL AND manifest_sha256 IS NOT NULL))")
table('store_activation', f'slot INTEGER PRIMARY KEY CHECK(slot=1) REFERENCES store_metadata(slot) {FK}, activation_id TEXT NOT NULL UNIQUE, store_id TEXT NOT NULL REFERENCES store_metadata(store_id) {FK}, profile_id TEXT NOT NULL REFERENCES schema_profiles(profile_id) {FK}, basis_sha256 TEXT NOT NULL, operator TEXT NOT NULL, activated_at TEXT NOT NULL')
for name in ('schema_profiles','store_metadata','store_activation'):
    for action in ('UPDATE','DELETE'):
        DDL[f'immutable_{name}_{action.lower()}'] = f"CREATE TRIGGER immutable_{name}_{action.lower()} BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT,'immutable history'); END"
