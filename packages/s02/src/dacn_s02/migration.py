"""Offline local DB1 -> DB2 protocol. No operational routing or repair.

The source transaction stays read-only and open through verification. This is
not a writer fence: the caller must stop old writers until manual cutover.
"""
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import os
import platform
import sqlite3
import stat
from uuid import uuid4

from . import __version__, reservation
from .codec_boundary import encode, decode
from .errors import S02Error, require
from .local_io import writable, within, check_store, read_receipt
from .migration_manifest import LAYOUTS, MUTABLE, table_digest, inventory_root, _SCHEMA
from .profiles import REGISTRY, L1, E1
from .repository import Repository, timestamp
from .storage_schema import APPLICATION_ID, DDL
from .store_profiles import check as check_profile, uuid4_id

PLAN='s02-2a-storage-plan/0.1.0-draft.2'
FIELDS={'receipt_version','migration_id','target_store_id','activation_id',
        'source_state_dir','destination_state_dir','plan_version','source_inventory_sha256'}
IDS=('migration_id','target_store_id','activation_id')

def fail(code,message,**details):
    raise S02Error(code,'persistence',message,details=details)

def rows(c):
    return {n:[tuple(r) for r in c.execute('SELECT '+','.join(cols)+' FROM '+n+' ORDER BY '+','.join(pk))]
            for n,(cols,pk) in LAYOUTS.items()}

def root(data):return inventory_root({n:table_digest(n,v) for n,v in data.items()})

def rules_hash():
    base=files('dacn_s02')
    # Actual executable Python bundle, sorted names plus content digests; no ZIP metadata.
    return sha256(b''.join(p.name.encode()+b'\0'+sha256(p.read_bytes()).digest()
                          for p in sorted(base.iterdir(),key=lambda p:p.name) if p.name.endswith('.py'))).hexdigest()

class Migration:
    def __init__(self,settings,source_state_dir,*,reviews=None,_hook=None):
        self.settings=settings
        self.source=self._path(source_state_dir)
        self.destination=self._path(settings.state)
        if within(self.source,self.destination) or within(self.destination,self.source):
            fail('MIGRATION_PATH_INVALID','Source and destination must be disjoint')
        for p in (self.source,self.destination):check_store(replace(settings,state=p))
        reservation.check_paths(settings,self.destination,self.source)
        self.source_repo=Repository(self.source/'s02.sqlite3',timeout=settings.timeout/1000)
        self.target=Repository(self.destination/'s02.sqlite3',timeout=settings.timeout/1000,reviews=reviews)
        self.hook=_hook or (lambda point,connection:None)

    def _path(self,value):
        p=Path(value).absolute()
        # Reject aliases at every supplied component; callers can pass resolved /private/tmp.
        if any(q.is_symlink() for q in (p,*p.parents)):
            fail('MIGRATION_PATH_INVALID','Symbolic path components are not allowed')
        return writable(self.settings,p)

    def _receipt_path(self,value):
        p=self._path(value)
        if not p.parent.is_dir() or within(p,self.source) or within(p,self.destination):
            fail('MIGRATION_RECEIPT_INVALID','Receipt must be outside both stores with an existing parent')
        if os.path.lexists(p):
            s=p.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:
                fail('MIGRATION_RECEIPT_INVALID','Receipt must be a regular unaliased file')
        return p

    def _read_receipt(self,path):
        try:
            p=self._receipt_path(path);raw=p.read_bytes();r=decode(raw)
            ok=(type(r) is dict and set(r)==FIELDS and r['receipt_version']=='s02-migration/1'
                and r['plan_version']==PLAN and all(uuid4_id(r[k]) for k in IDS)
                and r['source_state_dir']==str(self.source) and r['destination_state_dir']==str(self.destination)
                and type(r['source_inventory_sha256']) is str and len(r['source_inventory_sha256'])==64
                and all(x in '0123456789abcdef' for x in r['source_inventory_sha256']))
            if not ok:raise ValueError('receipt shape/binding')
            return r,raw
        except Exception as exc:
            if isinstance(exc,S02Error) and exc.error['code']=='MIGRATION_RECEIPT_INVALID':raise
            raise S02Error('MIGRATION_RECEIPT_INVALID','persistence','Missing or invalid migration receipt') from exc

    def _durable(self,path,r,*,create):
        p=self._receipt_path(path);raw=encode(r)+b'\n'
        directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        temp='.migration-'+str(uuid4())+'.tmp' if create else None;made=False
        try:
            if create:
                fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory);made=True
                with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                self.hook('receipt_before_publish',None)
                os.link(temp,p.name,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False)
                os.unlink(temp,dir_fd=directory);made=False
            else:
                fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
                try:os.fsync(fd)
                finally:os.close(fd)
            self.hook('receipt_before_dir_sync',None);os.fsync(directory)
            checked,actual=self._read_receipt(p)
            if checked!=r or (create and actual!=raw):fail('MIGRATION_RECEIPT_INVALID','Receipt readback differs')
            self.hook('receipt_durable',None)
        except Exception as exc:
            raise S02Error('MIGRATION_RECEIPT_INVALID','persistence','Receipt durability not acknowledged; resume with the same receipt') from exc
        finally:
            if made:os.unlink(temp,dir_fd=directory)
            os.close(directory)

    def _manifest(self,r,data):
        props=_SCHEMA['properties'];m={k:v['const'] for k,v in props.items() if 'const' in v}
        m.update({k:v for k,v in r.items() if k!='receipt_version'})
        m.update(profiles={pid:dict(schema_sha256=p.schema_sha256,descriptor_sha256=p.descriptor_sha256,
                    rules_id=p.descriptor['rules_id'],contract_version=p.descriptor['contract_version']) for pid,p in REGISTRY.items()},
            tool=dict(distribution='dacn-s02',version=__version__,python_version=platform.python_version(),
                      sqlite_version=sqlite3.sqlite_version,rules_bundle_sha256=rules_hash()),
            tables={n:dict(columns=LAYOUTS[n][0],primary_key=LAYOUTS[n][1],row_count=len(v),
                           source_sha256=table_digest(n,v),copied_legacy_sha256=table_digest(n,v)) for n,v in data.items()},
            mutable_baseline={n:[dict(zip(LAYOUTS[n][0],r)) for r in data[n]] for n in MUTABLE},
            exclusions=[v['const'] for v in props['exclusions']['prefixItems']])
        return m

    def _seed(self,c,data,manifest,*,hooks=False):
        for sql in DDL.values():c.execute(sql)
        c.execute(f'PRAGMA application_id={APPLICATION_ID}');c.execute('PRAGMA user_version=2')
        for p in REGISTRY.values():c.execute('INSERT INTO schema_profiles VALUES (?,?,?,?,?)',
            (p.profile_id,p.schema_bytes,p.schema_sha256,p.descriptor_bytes,p.descriptor_sha256))
        raw=encode(manifest)
        c.execute("INSERT INTO store_metadata VALUES (1,?,?,'migration',?,?,?)",
            (manifest['target_store_id'],E1,manifest['migration_id'],raw,sha256(raw).hexdigest()))
        for n,values in data.items():
            if n=='operations':
                # parent_command_id has an immediate FK in the pinned DDL.
                # Inventory remains PK-sorted; insertion follows checked ancestry.
                pending={r[0]:r for r in values};inserted=set();ordered=[]
                while pending:
                    ready=sorted(i for i,r in pending.items() if r[2] is None or r[2] in inserted)
                    require(bool(ready),'migration_operation_copy_order')
                    for identity in ready:
                        ordered.append(pending.pop(identity));inserted.add(identity)
                values=ordered
            if hooks:self.hook('before_copy_'+n,c)
            cols=LAYOUTS[n][0];owned=n in ('records','operations');names=cols+(['profile_id'] if owned else [])
            c.executemany('INSERT INTO '+n+' ('+','.join(names)+') VALUES ('+','.join('?' for _ in names)+')',
                          [(*r,L1) if owned else r for r in values])
            if hooks:self.hook('after_copy_'+n,c)
        require(rows(c)==data,'migration_raw_old_columns_equal')
        self.target._check_db2(c)
        require(c.execute('PRAGMA integrity_check').fetchall()[0][0]=='ok','migration_target_integrity')

    @contextmanager
    def _source(self,offline):
        if offline is not True:fail('OFFLINE_CONFIRMATION_REQUIRED','Stop and keep all old writers stopped; explicit confirmation required')
        c=None;source_ready=False
        try:
            check_store(replace(self.settings,state=self.source))
            c=self.source_repo._connect()  # URI mode=ro from the very first open, including resume.
            c.execute('BEGIN');c.execute('SELECT count(*) FROM sqlite_master').fetchone()
            if self.source_repo._structure(c)!=1:fail('MIGRATION_SOURCE_INVALID','Migration requires structure 1')
            require([tuple(r) for r in c.execute('PRAGMA integrity_check')]==[('ok',)],'migration_source_integrity')
            records,blobs,commands,events,stages=self.source_repo._check_legacy(c)
            # Observation may live on a finalized successor. Match the exact
            # dispatch reference across checked lineage, never just an event kind.
            observed={(e['payload']['dispatch_event']['command_id'],e['payload']['dispatch_event']['event_id'])
                      for e in events.values() if e['kind']=='s01_result_observed' and e['payload']['lookup_status']!='unknown'}
            for cmd in commands:
                state=self.source_repo._command(c,cmd)
                if state['state']!='finalized':fail('MIGRATION_INELIGIBLE','Unfinalized operation',command_id=cmd)
                kinds={e['kind'] for e in state['events']}
                unresolved=('dispatch_intent' in kinds and 'response_received' not in kinds or
                            any((cmd,e['event_id']) not in observed for e in state['events'] if e['kind']=='s01_dispatch_intent'))
                if unresolved or any(a['status']=='unknown_outcome' for a in state['run']['body']['attempts']):
                    fail('MIGRATION_INELIGIBLE','Unresolved dispatch or outcome',command_id=cmd)
            data=rows(c);self.hook('source_locked',c)
            # Check DB2's stricter whole-store invariants before any target/receipt effects.
            probe=dict(receipt_version='s02-migration/1',plan_version=PLAN,source_state_dir=str(self.source),
                destination_state_dir=str(self.destination),source_inventory_sha256=root(data),
                **{k:'00000000-0000-4000-8000-000000000001' for k in IDS})
            memory=sqlite3.connect(':memory:',autocommit=True);memory.row_factory=sqlite3.Row
            try:
                memory.execute('PRAGMA foreign_keys=ON');memory.execute('BEGIN')
                self._seed(memory,data,self._manifest(probe,data))
            finally:memory.close()
            source_ready=True
            yield data
        except sqlite3.Error as exc:
            code=getattr(exc,'sqlite_errorcode',None)
            if not source_ready and code==getattr(sqlite3,'SQLITE_READONLY_ROLLBACK',776):
                raise S02Error('SOURCE_RECOVERY_REQUIRED','persistence','Source needs recovery by its owner; not modified',
                    details=dict(source_path=str(self.source_repo.path),stage='source_preflight',sqlite_errorcode=code,sqlite_errorname=getattr(exc,'sqlite_errorname',None))) from exc
            raise S02Error('PERSISTENCE_FAILED','persistence','SQLite operation failed',details=dict(sqlite_errorcode=code,sqlite_errorname=getattr(exc,'sqlite_errorname',None))) from exc
        finally:
            if c:
                if c.in_transaction:c.execute('ROLLBACK')
                c.close()

    def _identity(self,data):
        return dict(receipt_version='s02-migration/1',plan_version=PLAN,source_state_dir=str(self.source),
            destination_state_dir=str(self.destination),source_inventory_sha256=root(data),**{k:str(uuid4()) for k in IDS})

    def inspect(self,*,offline=False):
        with self._source(offline) as data:
            return dict(status='eligible',source_inventory_sha256=root(data),table_counts={n:len(v) for n,v in data.items()},
                        offline_writer_fence=False)

    def _binding(self,r,data):
        if r['source_inventory_sha256']!=root(data):fail('MIGRATION_IDENTITY_CONFLICT','Source inventory changed since receipt')

    def _target_checked(self,c,r,data):
        self.target._check(c);info=check_profile(c,path=self.target.path)
        m=info['metadata']
        if m['origin_kind']!='migration':fail('MIGRATION_IDENTITY_CONFLICT','Destination is not this migration')
        manifest=decode(m['migration_manifest'])
        if any(manifest.get(k)!=r[k] for k in FIELDS-{'receipt_version'}):
            fail('MIGRATION_IDENTITY_CONFLICT','Receipt and manifest identity differ')
        if info['activation'] is None:require(rows(c)==data,'migration_inactive_exact_inventory')
        require([tuple(x) for x in c.execute('PRAGMA integrity_check')]==[('ok',)],'migration_target_integrity')
        return dict(status='active' if info['activation'] else 'committed_inactive',
                    migration_id=r['migration_id'],target_store_id=r['target_store_id'],activation_id=r['activation_id'],
                    manifest_sha256=m['manifest_sha256'],activation=info['activation'],
                    rollback_eligible=rows(c)==data)

    def _reconcile(self,r,data):
        check_store(replace(self.settings,state=self.destination))
        if reservation.reserved(self.destination):
            if decode(reservation.read(self.destination))!=r:
                fail('MIGRATION_IDENTITY_CONFLICT','Reservation does not match the durable receipt')
        if not self.destination.exists():
            return dict(status='partial' if reservation.reserved(self.destination) else 'missing',**{k:r[k] for k in IDS})
        if not self.target.path.exists():return dict(status='partial',**{k:r[k] for k in IDS})
        c=self.target._connect()
        try:
            c.execute('BEGIN')
            if c.execute('PRAGMA user_version').fetchone()[0]==0:
                return dict(status='partial',**{k:r[k] for k in IDS})
            return self._target_checked(c,r,data)
        finally:c.close()

    def reconcile(self,receipt,*,offline=False):
        r,_=self._read_receipt(receipt)
        with self._source(offline) as data:
            self._binding(r,data);return self._reconcile(r,data)

    def copy(self,receipt,*,offline=False,resume=False):
        # Recheck on reused Migration instances and resume, before receipt effects.
        reservation.check_paths(self.settings,self.destination,self.source)
        # Invalid existing receipt fails before source work or any destination effects.
        r=self._read_receipt(receipt)[0] if resume else None
        p=self._receipt_path(receipt)
        if not resume and os.path.lexists(p):fail('MIGRATION_RECEIPT_INVALID','Receipt exists; use explicit resume')
        with self._source(offline) as data:
            if r is None:r=self._identity(data)
            self._binding(r,data);self._durable(p,r,create=not resume)
            with reservation.guard(self.destination,self.target.timeout) as directory:
                reservation.check_paths(self.settings,self.destination,self.source)
                if self.destination.exists() or reservation.reserved(self.destination):
                    result=self._reconcile(r,data)
                    if result['status']=='partial':fail('MIGRATION_PARTIAL','Partial destination requires explicit operator disposition; no reset')
                    return result
                self.hook('before_reserve',None)
                reservation.publish(self.destination,encode(r)+b'\n',directory,self.hook,
                                    settings=self.settings,source=self.source)
                self.destination.mkdir()  # marker is durable before the exclusive leaf
                self.hook('destination_created',None)
                os.fsync(directory)
                self.hook('after_reserve',None)
                fd=os.open(self.target.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd)
                c=None
                try:
                    c=self.target._connect(write=True);c.execute('BEGIN IMMEDIATE')
                    self._seed(c,data,self._manifest(r,data),hooks=True)
                    self.target._structure(c)
                    self.hook('before_copy_commit',c);c.execute('COMMIT');self.hook('after_copy_commit',c)
                except Exception as exc:
                    if c and c.in_transaction:c.execute('ROLLBACK')
                    raise S02Error('MIGRATION_COPY_UNACKNOWLEDGED','persistence','Copy not acknowledged; reconcile the same receipt, never reset') from exc
                finally:
                    if c:c.close()
                return self._reconcile(r,data)  # fresh existing-only checked connection, source still locked

    def activate(self,receipt,*,offline=False,confirm=False,operator=None):
        if confirm is not True or type(operator) is not str or not operator.strip():
            fail('ACTIVATION_CONFIRMATION_REQUIRED','Explicit activation confirmation and operator required')
        r,_=self._read_receipt(receipt)
        with self._source(offline) as data:
            self._binding(r,data);before=self._reconcile(r,data)
            if before['status'] not in ('active','committed_inactive'):fail('MIGRATION_PARTIAL','No committed target to activate')
            c=None
            try:
                c=self.target._connect(write=True);self.hook('before_activation_begin',c);c.execute('BEGIN IMMEDIATE')
                checked=self._target_checked(c,r,data)
                if checked['activation'] is None:
                    c.execute('INSERT INTO store_activation VALUES (1,?,?,?,?,?,?)',
                        (r['activation_id'],r['target_store_id'],E1,checked['manifest_sha256'],operator,timestamp()))
                self._target_checked(c,r,data);self.hook('before_activation_commit',c)
                c.execute('COMMIT');self.hook('after_activation_commit',c)
            except Exception as exc:
                if c and c.in_transaction:c.execute('ROLLBACK')
                if isinstance(exc,S02Error):raise
                raise S02Error('MIGRATION_ACTIVATION_UNACKNOWLEDGED','persistence','Activation not acknowledged; reconcile same receipt',
                    details=dict(sqlite_errorcode=getattr(exc,'sqlite_errorcode',None))) from exc
            finally:
                if c:c.close()
            return self._reconcile(r,data)

    def lookup_migrated(self,old_receipt,migration_receipt,*,offline=False):
        r,_=self._read_receipt(migration_receipt)
        old=read_receipt(replace(self.settings,state=self.source),old_receipt)
        if old['receipt_version']!='s02/1':fail('MIGRATION_RECEIPT_INVALID','lookup-migrated requires original s02/1 receipt')
        with self._source(offline) as data:
            self._binding(r,data)
            with self.target._read() as c:
                info=self._target_checked(c,r,data)
                if info['status']!='active':fail('ACTIVATION_REQUIRED','Explicit activation required')
                if old['command_id'] not in {v[0] for v in data['operations']}:
                    fail('MIGRATION_IDENTITY_CONFLICT','Command is not in copied source inventory')
                require(c.execute('SELECT profile_id FROM operations WHERE command_id=?',(old['command_id'],)).fetchone()[0]==L1,'migration_lookup_owner')
                return dict(profile_id=L1,**self.target._command(c,old['command_id']))
