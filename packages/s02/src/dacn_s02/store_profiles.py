"""DB2 registry/identity checks. Never loads executable resources from a store."""
from uuid import UUID
from .codec_boundary import encode, decode
from .profiles import REGISTRY, E1
from .errors import require, S02Error
from hashlib import sha256

def digest(raw): return sha256(raw).hexdigest()
def uuid4_id(value):
    try: return type(value) is str and str(UUID(value)) == value and UUID(value).version == 4
    except (ValueError, TypeError, AttributeError): return False

def fresh_descriptor(store_id):
    return encode(dict(format='s02-fresh-store/1',store_id=store_id,db_version=2,
        write_profile_id=E1,profiles={p:dict(schema_sha256=v.schema_sha256,
            descriptor_sha256=v.descriptor_sha256) for p,v in REGISTRY.items()}))

def seed_fresh(c, store_id, activation_id, operator, activated_at):
    require(uuid4_id(store_id) and uuid4_id(activation_id),'fresh_store_ids')
    require(type(operator) is str and bool(operator.strip()),'activation_operator')
    for p in REGISTRY.values():
        c.execute('INSERT INTO schema_profiles VALUES (?,?,?,?,?)',
            (p.profile_id,p.schema_bytes,p.schema_sha256,p.descriptor_bytes,p.descriptor_sha256))
    c.execute('INSERT INTO store_metadata VALUES (1,?,?,\'fresh\',NULL,NULL,NULL)',(store_id,E1))
    c.execute('INSERT INTO store_activation VALUES (1,?,?,?,?,?,?)',
        (activation_id,store_id,E1,digest(fresh_descriptor(store_id)),operator,activated_at))

def check(c, *, path, writable=False):
    rows={r['profile_id']:r for r in c.execute('SELECT * FROM schema_profiles')}
    require(rows.keys()==REGISTRY.keys(),'store_profile_inventory')
    for pid,p in REGISTRY.items():
        require(tuple(rows[pid])==(pid,p.schema_bytes,p.schema_sha256,p.descriptor_bytes,p.descriptor_sha256),'store_packaged_profile_exact')
    rows=list(c.execute('SELECT * FROM store_metadata'))
    require(len(rows)==1 and rows[0]['slot']==1,'store_metadata_singleton')
    m=dict(rows[0]);require(uuid4_id(m['store_id']) and m['write_profile_id']==E1,'store_identity_profile')
    if m['origin_kind']=='fresh':
        require(all(m[k] is None for k in ('migration_id','migration_manifest','manifest_sha256')),'fresh_metadata')
        basis=digest(fresh_descriptor(m['store_id']));manifest=None
    else:
        require(m['origin_kind']=='migration' and uuid4_id(m['migration_id']) and type(m['migration_manifest']) is bytes,'migration_metadata')
        require(digest(m['migration_manifest'])==m['manifest_sha256'],'migration_manifest_hash')
        manifest=decode(m['migration_manifest'])
        require(type(manifest) is dict and manifest.get('format')=='s02-migration-manifest/1' and
            manifest.get('plan_version')=='s02-2a-storage-plan/0.1.0-draft.2' and
            manifest.get('source_db_version')==1 and manifest.get('target_db_version')==2 and
            manifest.get('source_application_id_hex')=='44414332','migration_manifest_version')
        require(type(manifest) is dict and manifest.get('migration_id')==m['migration_id'] and
            manifest.get('target_store_id')==m['store_id'] and manifest.get('write_profile_id')==E1 and
            uuid4_id(manifest.get('activation_id')),'migration_manifest_identity')
        from .migration_manifest import check as check_manifest
        check_manifest(c,manifest,path=path)
        basis=m['manifest_sha256']
    rows=list(c.execute('SELECT * FROM store_activation'))
    require(len(rows)<=1,'store_activation_singleton')
    if rows:
        a=dict(rows[0]);require(a['slot']==1 and uuid4_id(a['activation_id']) and
            a['store_id']==m['store_id'] and a['profile_id']==E1 and a['basis_sha256']==basis and
            bool(a['operator'].strip()) and bool(a['activated_at'].strip()),'store_activation_binding')
        if manifest is not None: require(a['activation_id']==manifest['activation_id'],'migration_activation_identity')
    elif writable:
        raise S02Error('ACTIVATION_REQUIRED','persistence','Store is verified but inactive; normal writes are disabled')
    return dict(metadata=m,activation=dict(rows[0]) if rows else None)
