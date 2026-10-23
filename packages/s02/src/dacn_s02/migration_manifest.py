"""Checked-read manifest inventory only. No copy, activation or source connection."""
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files
from pathlib import PurePosixPath
import json
from .codec_boundary import decode
from .errors import require
from .profiles import L1
from .validation import Validator

SCHEMA_SHA256 = '7c4681cdde91c237b15300d0de5f1909c9c5ae5105d90b0890aeb89b9c6ae889'
_raw=files('dacn_s02').joinpath('schemas/storage/migration-manifest.json').read_bytes()
require(sha256(_raw).hexdigest()==SCHEMA_SHA256,'packaged_manifest_schema_hash')
_SCHEMA=json.loads(_raw)
MUTABLE=('sessions','application_heads','active_reviews')
LAYOUTS={name:([v['const'] for v in spec['properties']['columns']['prefixItems']],
               [v['const'] for v in spec['properties']['primary_key']['prefixItems']])
         for name,spec in _SCHEMA['properties']['tables']['properties'].items()}
ALGORITHM='s02-db1-inventory/1'

def cell(value):
    if value is None:tag,payload=b'N',b''
    elif type(value) is bytes:tag,payload=b'B',value
    elif type(value) is str:tag,payload=b'T',value.encode('utf-8')
    else:
        require(type(value) is int or type(value) is Decimal and value.is_finite() and value==value.to_integral_value(),'inventory_cell_type')
        tag,payload=b'I',str(int(value)).encode('ascii')
    return tag+len(payload).to_bytes(8,'big')+payload

def table_digest(name,rows):
    columns,pk=LAYOUTS[name];indices=[columns.index(k) for k in pk]
    ordered=sorted(rows,key=lambda row:tuple(row[i].encode('utf-8') for i in indices))
    require(len({tuple(row[i] for i in indices) for row in ordered})==len(ordered),'inventory_unique_pk')
    framed=[name,len(columns),*columns,len(pk),*pk,len(ordered)]
    for row in ordered:
        require(len(row)==len(columns),'inventory_column_count')
        for column,value in zip(columns,row):
            if column in ('record_json','request_json','payload_json'):
                require(type(value) is str and value.isascii(),'inventory_json_ascii')
        framed.append(sha256(b''.join(cell(v) for v in row)).digest())
    return sha256(b''.join(cell(v) for v in framed)).hexdigest()

def inventory_root(hashes):
    require(set(hashes)==set(LAYOUTS),'inventory_table_set')
    framed=[ALGORITHM,len(hashes)]
    for name in sorted(hashes):framed.extend((name,bytes.fromhex(hashes[name])))
    return sha256(b''.join(cell(v) for v in framed)).hexdigest()

def _projection(c,name):
    # Names/columns come exclusively from the pinned packaged schema.
    columns,pk=LAYOUTS[name]
    if name=='records':where='profile_id=?'
    elif name=='operations':where='profile_id=?'
    elif name in ('models','analysis_sets','artifacts'):where='record_id IN (SELECT id FROM records WHERE profile_id=?)'
    elif name in ('staged_blobs','operation_events','promotions'):where='command_id IN (SELECT command_id FROM operations WHERE profile_id=?)'
    elif name.startswith('record'):where='owner_id IN (SELECT id FROM records WHERE profile_id=?)'
    else:where='owner_id IN (SELECT event_id FROM operation_events WHERE command_id IN (SELECT command_id FROM operations WHERE profile_id=?))'
    return [tuple(r) for r in c.execute('SELECT '+','.join(columns)+' FROM '+name+' WHERE '+where,(L1,))]

def _ancestor(identity,current,parent,lookup):
    seen=set()
    while current is not None and current!=identity:
        require(current not in seen and current in lookup,'manifest_baseline_lineage')
        seen.add(current);current=lookup[current][parent]
    require(current==identity,'manifest_baseline_lineage')

def check(c,manifest,*,path):
    require(not list(Validator(_SCHEMA).iter_errors(manifest)),'migration_manifest_schema')
    for field in ('source_state_dir','destination_state_dir'):
        value=manifest[field];p=PurePosixPath(value)
        require(p.is_absolute() and str(p)==value and '..' not in p.parts and '\x00' not in value and not value.startswith('//'),'migration_manifest_path')
    require(manifest['source_state_dir']!=manifest['destination_state_dir'] and
            manifest['destination_state_dir']==str(path.parent),'migration_manifest_destination')
    require(bool(manifest['tool']['version'].strip()) and bool(manifest['tool']['python_version'].strip()) and
            bool(manifest['tool']['sqlite_version'].strip()),'migration_manifest_tool')
    hashes={};baseline={}
    for name in LAYOUTS:
        entry=manifest['tables'][name];columns,pk=LAYOUTS[name]
        if name in MUTABLE:
            rows=[tuple(r[col] for col in columns) for r in manifest['mutable_baseline'][name]]
            baseline[name]=manifest['mutable_baseline'][name]
        else:rows=_projection(c,name)
        actual=table_digest(name,rows)
        require(len(rows)==entry['row_count'] and actual==entry['source_sha256']==entry['copied_legacy_sha256'],'migration_legacy_inventory')
        hashes[name]=actual
    require(inventory_root(hashes)==manifest['source_inventory_sha256'],'migration_inventory_root')
    sessions={r['session_id']:dict(r) for r in c.execute('SELECT * FROM sessions')}
    oldsessions={r['session_id']:r for r in baseline['sessions']}
    owners={r[0] for r in c.execute('SELECT session_id FROM records WHERE profile_id=? UNION SELECT session_id FROM operations WHERE profile_id=? AND session_id IS NOT NULL',(L1,L1))}
    require(owners<=oldsessions.keys(),'migration_baseline_sessions')
    models={r['record_id']:dict(r) for r in c.execute('SELECT * FROM models')}
    sets={r['record_id']:dict(r) for r in c.execute('SELECT * FROM analysis_sets')}
    l1models={r[0] for r in c.execute("SELECT id FROM records WHERE profile_id=? AND type='model'",(L1,))}
    l1sets={r[0] for r in c.execute("SELECT id FROM records WHERE profile_id=? AND type='analysis_set'",(L1,))}
    for sid,old in oldsessions.items():
        require(sid in sessions,'migration_session_identity');now=sessions[sid]
        require(now['spec_id']==old['spec_id'] and now['sequence']>=old['sequence'],'migration_session_identity')
        previous=[models[i] for i in l1models if models[i]['session_id']==sid]
        if not previous:require(old['head_model_id'] is None and old['head_analysis_set_id'] is None,'migration_baseline_heads')
        else:
            head=max(previous,key=lambda r:r['revision']);choices=[sets[i] for i in l1sets if sets[i]['model_id']==head['record_id']]
            require(choices and old['head_model_id']==head['record_id'] and old['head_analysis_set_id']==max(choices,key=lambda r:r['revision'])['record_id'],'migration_baseline_heads')
            _ancestor(old['head_model_id'],now['head_model_id'],'parent_id',models)
            current_sets=[v for v in sets.values() if v['model_id']==old['head_model_id']]
            _ancestor(old['head_analysis_set_id'],max(current_sets,key=lambda r:r['revision'])['record_id'],'parent_set_id',sets)
    commands={r['command_id']:dict(parent_command_id=r['parent_command_id'],request=decode(r['request_json'].encode('ascii')),profile_id=r['profile_id']) for r in c.execute('SELECT * FROM operations')}
    claims={r['answer_id']:r['active_command_id'] for r in c.execute('SELECT * FROM application_heads')}
    oldclaims={r['answer_id']:r['active_command_id'] for r in baseline['application_heads']}
    legacyapps={i:o for i,o in commands.items() if o['profile_id']==L1 and o['request']['kind']=='apply_answer'}
    require(oldclaims.keys()=={o['request']['answer_id'] for o in legacyapps.values()},'migration_baseline_claims')
    for aid,cmd in oldclaims.items():
        ids={i for i,o in legacyapps.items() if o['request']['answer_id']==aid}
        require(ids-{commands[i]['parent_command_id'] for i in ids}=={cmd} and aid in claims,'migration_baseline_claims')
        _ancestor(cmd,claims[aid],'parent_command_id',commands)
    reviews={r['id']:decode(r['record_json'].encode('ascii'))['body'] for r in c.execute("SELECT * FROM records WHERE type='review'")}
    l1reviews={r[0] for r in c.execute("SELECT id FROM records WHERE type='review' AND profile_id=?",(L1,))}
    active={r['bundle_id']:r['review_id'] for r in c.execute('SELECT * FROM active_reviews')}
    oldreviews={r['bundle_id']:r['review_id'] for r in baseline['active_reviews']}
    require(oldreviews.keys()=={reviews[i]['bundle_id'] for i in l1reviews},'migration_baseline_reviews')
    for bundle,rid in oldreviews.items():
        ids={i for i in l1reviews if reviews[i]['bundle_id']==bundle}
        require(ids-{reviews[i]['supersedes_review_id'] for i in ids}=={rid} and bundle in active,'migration_baseline_reviews')
        _ancestor(rid,active[bundle],'supersedes_review_id',reviews)
