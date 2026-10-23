"""Explicit E1 fixtures for DB2. Synthetic sources only; no runtime conversion."""
from helpers import Foundation as LegacyFoundation,model,aset,run,issue as legacy_issue

def issue(*args,**kwargs):
    q=legacy_issue(*args,**kwargs)
    q['body'].update(resolution_carry=None,resolution_replacement=None)
    return q

class Foundation(LegacyFoundation):
    def initial(self,with_issue=False):
        op=self.operation();self.repo.prepare(op);m=model(self.context,self.snapshot,op['reserved_run_id'])
        q=issue(m) if with_issue else None;a=aset(m,issues=[q['id']] if q else [])
        rr=run(op,self.context,self.config,model_id=m['id'],set_id=a['id'])
        self.repo.finalize(op['command_id'],[m,a,rr]+([q] if q else []),head=(m['id'],a['id']))
        return m,a


def synthetic_manifest(repo,original=None):
    """Full manifest test fixture; independent struct framing, never a migration tool."""
    import hashlib,json,sqlite3,struct
    from uuid import uuid4
    from importlib.resources import files
    from dacn_s02.storage_schema import DDL1
    from dacn_s02.profiles import REGISTRY,E1
    schema=json.loads(files('dacn_s02').joinpath('schemas/storage/migration-manifest.json').read_bytes())
    def frame(v):
        if v is None:t,p=b'N',b''
        elif isinstance(v,bytes):t,p=b'B',v
        elif isinstance(v,str):t,p=b'T',v.encode()
        else:t,p=b'I',str(v).encode('ascii')
        return t+struct.pack('>Q',len(p))+p
    def digest(vs):return hashlib.sha256(b''.join(frame(v) for v in vs)).hexdigest()
    table_specs=schema['properties']['tables']['properties'];tables={};mutable={};root=['s02-db1-inventory/1',len(table_specs)]
    with sqlite3.connect(repo.path) as c:
        for name,spec in sorted(table_specs.items()):
            cols=[x['const'] for x in spec['properties']['columns']['prefixItems']];pk=[x['const'] for x in spec['properties']['primary_key']['prefixItems']]
            rows=original[name] if original is not None else c.execute('SELECT '+','.join(cols)+' FROM '+name).fetchall()
            rows=sorted(rows,key=lambda r:tuple(r[cols.index(k)].encode() for k in pk))
            rowhashes=[bytes.fromhex(digest(row)) for row in rows]
            h=digest([name,len(cols),*cols,len(pk),*pk,len(rows),*rowhashes])
            tables[name]=dict(columns=cols,primary_key=pk,row_count=len(rows),source_sha256=h,copied_legacy_sha256=h)
            root.extend((name,bytes.fromhex(h)))
            if name in ('sessions','application_heads','active_reviews'):mutable[name]=[dict(zip(cols,row)) for row in rows]
    info=repo.store_info();m=info['metadata'];a=info['activation']
    props=schema['properties'];manifest={k:v['const'] for k,v in props.items() if 'const' in v}
    manifest.update(migration_id=str(uuid4()),target_store_id=m['store_id'],activation_id=a['activation_id'],
        source_state_dir=str(repo.path.parent/'synthetic-source'),destination_state_dir=str(repo.path.parent),source_inventory_sha256=digest(root),
        profiles={pid:dict(schema_sha256=p.schema_sha256,descriptor_sha256=p.descriptor_sha256,rules_id=p.descriptor['rules_id'],contract_version=p.descriptor['contract_version']) for pid,p in REGISTRY.items()},
        tool=dict(distribution='dacn-s02',version='SYNTHETIC-FIXTURE',python_version='SYNTHETIC',sqlite_version=sqlite3.sqlite_version,rules_bundle_sha256='0'*64),
        tables=tables,mutable_baseline=mutable,exclusions=[x['const'] for x in props['exclusions']['prefixItems']])
    return manifest


def install_manifest_fixture(repo,manifest):
    """Direct synthetic SQL fault/seed; no production migration API exists."""
    import sqlite3,hashlib
    from dacn_s02.codec_boundary import encode
    from dacn_s02.storage_schema import DDL
    raw=encode(manifest);h=hashlib.sha256(raw).hexdigest()
    with sqlite3.connect(repo.path) as c:
        for name in ('store_metadata','store_activation'):c.execute('DROP TRIGGER immutable_'+name+'_update')
        c.execute("UPDATE store_metadata SET origin_kind='migration',migration_id=?,migration_manifest=?,manifest_sha256=?",(manifest['migration_id'],raw,h))
        c.execute('UPDATE store_activation SET basis_sha256=?',(h,))
        for name in ('store_metadata','store_activation'):c.execute(DDL['immutable_'+name+'_update'])
