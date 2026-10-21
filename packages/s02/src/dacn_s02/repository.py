"""Explicit local SQLite boundaries, append-only records, two-head publication.

The batch writer is an internal code boundary, not a CLI/import endpoint.
Whole-store checked reads favor auditability over large-store throughput.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from uuid import uuid4

from .codec_boundary import encode,decode
from .errors import S02Error,require,storage_error
from .storage_schema import APPLICATION_ID,DB_VERSION,DDL
from .validation import shape,valid_id,fields,typed_links,walk_schema,SCHEMA,validate_record
from .s01_adapter import verify_archive

def digest(raw): return hashlib.sha256(raw).hexdigest()
def jtext(value): return encode(value).decode("ascii")
def timestamp(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def record(kind,identity,body,created_at=None): return dict(type=kind,id=identity,created_at=created_at or timestamp(),body=body)

class Repository:
    def __init__(self,path,*,timeout=5.0,_hook=None,_ids=None,_clock=None):
        self.path=Path(path).resolve();self.timeout=timeout
        self._hook=_hook or (lambda point,connection:None)
        self._ids=_ids or (lambda:str(uuid4()));self._clock=_clock or timestamp

    def _connect(self,create=False):
        c=sqlite3.connect(self.path.as_uri()+('?mode=rwc' if create else '?mode=rw'),uri=True,autocommit=True,timeout=self.timeout)
        c.row_factory=sqlite3.Row
        try:
            c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA synchronous=FULL')
            require(c.execute('PRAGMA foreign_keys').fetchone()[0]==1 and c.execute('PRAGMA synchronous').fetchone()[0]==2,'sqlite_configuration')
            return c
        except Exception: c.close();raise

    def _structure(self,c):
        require(c.execute('PRAGMA application_id').fetchone()[0]==APPLICATION_ID,'s02_database_identity')
        require(c.execute('PRAGMA user_version').fetchone()[0]==DB_VERSION,'unsupported_database_version')
        require(dict(c.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))==DDL,'s02_exact_ddl')
        require(c.execute('PRAGMA journal_mode').fetchone()[0]=='delete','sqlite_journal_delete')

    def initialize(self):
        c=None
        try:
            c=self._connect(True);c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT name FROM sqlite_master').fetchall() and c.execute('PRAGMA user_version').fetchone()[0]==0 and c.execute('PRAGMA application_id').fetchone()[0]==0:
                for sql in DDL.values(): c.execute(sql)
                c.execute(f'PRAGMA application_id={APPLICATION_ID}');c.execute(f'PRAGMA user_version={DB_VERSION}')
            self._structure(c);c.execute('COMMIT')
        except Exception as exc:
            if c and c.in_transaction: c.execute('ROLLBACK')
            raise storage_error('Database initialization refused or failed; no reset performed') from exc
        finally:
            if c: c.close()

    @contextmanager
    def _read(self):
        c=None
        try:
            c=self._connect();self._structure(c);c.execute('BEGIN')
            yield c
        except S02Error as exc:
            if exc.error['stage']=='persistence' or exc.error['code'] in ('ANALYSIS_STALE','REVISION_MISMATCH'): raise
            raise storage_error('Stored data or structure failed integrity checks') from exc
        except Exception as exc: raise storage_error('Checked lookup failed') from exc
        finally:
            if c:
                if c.in_transaction: c.execute('ROLLBACK')
                c.close()

    def _write(self,work,probe):
        """Reconcile an unacknowledged COMMIT using a new checked connection."""
        c=None;attempted=False;failure=None;result=None
        try:
            c=self._connect();self._structure(c);self._hook('before_begin',c)
            c.execute('BEGIN IMMEDIATE');self._hook('after_begin',c)
            self._check(c);result=work(c);self._hook('after_insert',c);self._check(c)
            self._hook('before_commit',c);attempted=True;c.execute('COMMIT');self._hook('after_commit',c)
        except Exception as exc:
            failure=exc
            if c and c.in_transaction:
                try: c.execute('ROLLBACK');attempted=False
                except Exception: attempted=True
        finally:
            if c: c.close()
        if failure:
            if attempted:
                try:
                    recovered=probe()
                    if recovered is not None: return recovered
                except Exception: pass
                raise storage_error('Commit outcome unknown; reconcile the existing command ID, do not resubmit') from failure
            if isinstance(failure,S02Error): raise failure
            raise storage_error('Transaction failed before acknowledged commit') from failure
        return result

    def allocate_id(self):
        """Before receipt/publication only; after receipt never silently replace ID."""
        with self._read() as c:
            used=set()
            for table,col in [('records','id'),('operations','command_id'),('operations','reserved_run_id'),('operation_events','event_id'),('staged_blobs','blob_id'),('sessions','session_id')]:
                used.update(r[0] for r in c.execute(f'SELECT {col} FROM {table}'))
            for _ in range(8):
                value=self._ids();require(valid_id(value),'generated_id')
                if value not in used: return value
        raise storage_error('ID generator collided eight times')

    def _links(self,c,identity,walk,prefix,*,write=False):
        expected={'record':[], 'event':[], 'stage':[]}
        for v,s,p,n in walk:
            if 'x-record' in s: expected['record'].append((identity,p,v))
            if n=='EventRef': expected['event'].append((identity,p,v['command_id'],v['event_id']))
            if n=='StageRef': expected['stage'].append((identity,p,v['command_id'],v['blob_id']))
        for kind,values in expected.items():
            table=prefix+'_links' if kind=='record' and prefix=='record' else prefix+'_'+kind+'_links'
            if write:
                for row in values: c.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in row)})',row)
            else:
                actual=[tuple(r) for r in c.execute(f'SELECT * FROM {table} WHERE owner_id=?',(identity,))]
                require(sorted(actual)==sorted(values),'materialized_typed_links')

    def _put_records(self,c,session_id,records,blobs):
        for r in records:
            shape(r);raw=encode(r);b=r['body'];i=r['id']
            c.execute('INSERT INTO records VALUES (?,?,?,?,?,?)',(i,session_id,r['type'],r['created_at'],raw.decode('ascii'),digest(raw)))
            if r['type']=='model': c.execute('INSERT INTO models VALUES (?,?,?,?,?)',(i,session_id,int(b['revision']),b['parent_model_id'],b['source_context_id']))
            if r['type']=='analysis_set': c.execute('INSERT INTO analysis_sets VALUES (?,?,?,?)',(i,b['model_id'],int(b['revision']),b['parent_set_id']))
            if r['type']=='artifact':
                require(i in blobs and type(blobs[i]) is bytes,'artifact_bytes_present')
                c.execute('INSERT INTO artifacts VALUES (?,?,?,?,?)',(i,b['producer_run_id'],b['sha256'],int(b['byte_length']),blobs[i]))
            self._links(c,i,fields(r),'record',write=True)

    def _put_stages(self,c,command_id,staged):
        for item,raw in staged:
            shape(item,'StagedBlob');require(item['command_id']==command_id,'staging_command')
            require(type(raw) is bytes and digest(raw)==item['sha256'] and len(raw)==item['byte_length'],'staged_bytes')
            c.execute('INSERT INTO staged_blobs VALUES (?,?,?,?,?,?,?)',(command_id,item['blob_id'],item['media_type'],item['purpose'],item['sha256'],int(item['byte_length']),raw))
        self._hook('after_stage',c)

    def _put_event(self,c,event):
        shape(event,'OperationEvent');raw=encode(event['payload'])
        c.execute('INSERT INTO operation_events VALUES (?,?,?,?,?,?,?)',(event['event_id'],event['command_id'],int(event['ordinal']),event['kind'],raw.decode('ascii'),digest(raw),event['payload'].get('answer_id')))
        self._links(c,event['event_id'],walk_schema(event,SCHEMA['$defs'][event['kind']+'Event']),'event',write=True)
        c.execute('UPDATE sessions SET sequence=sequence+1 WHERE session_id=(SELECT session_id FROM operations WHERE command_id=?)',(event['command_id'],))

    def _event(self,c,cmd,kind,payload,identity=None):
        ordinal=c.execute('SELECT COALESCE(MAX(ordinal),0)+1 FROM operation_events WHERE command_id=?',(cmd,)).fetchone()[0]
        return dict(event_id=identity or self._ids(),command_id=cmd,ordinal=ordinal,kind=kind,payload=payload)

    def prepare(self,operation,*,session_spec=None,staged=(),attempt_id=None,claim_from=None,reused_artifact_ids=()):
        shape(operation,'Operation');cmd=operation['command_id'];request=operation['request']
        def work(c):
            if session_spec is not None:
                require(request['kind']=='start' and operation['session_id'] is not None,'initial_session_intent')
                c.execute('INSERT INTO sessions VALUES (?,?,NULL,NULL,0)',(operation['session_id'],session_spec))
            c.execute('INSERT INTO operations VALUES (?,?,?,?,?,?)',(cmd,operation['session_id'],operation['parent_command_id'],operation['reserved_run_id'],jtext(request),digest(encode(request))))
            if request['kind']=='apply_answer':
                aid=request['answer_id']
                if c.execute("SELECT 1 FROM operation_events WHERE kind='application_applied' AND answer_id=?",(aid,)).fetchone():
                    raise S02Error('APPLICATION_CONFLICT','revision','Answer already applied',details={'answer_id':aid,'reason':'Lookup the existing application'})
                row=c.execute('SELECT active_command_id FROM application_heads WHERE answer_id=?',(aid,)).fetchone()
                if row:
                    if row[0]!=claim_from or operation['parent_command_id']!=claim_from:
                        raise S02Error('APPLICATION_CONFLICT','revision','Answer claim belongs to another command',details={'answer_id':aid,'reason':'Active claim'})
                    prior=self._command(c,claim_from)
                    require(prior['state']=='finalized' and prior['run']['body']['status']=='stale','application_successor_requires_stale')
                    c.execute('UPDATE application_heads SET active_command_id=? WHERE answer_id=? AND active_command_id=?',(cmd,aid,claim_from))
                else: c.execute('INSERT INTO application_heads VALUES (?,?)',(aid,cmd))
            self._put_stages(c,cmd,staged)
            payload=dict(stage_refs=[dict(command_id=cmd,blob_id=i['blob_id']) for i,_ in staged],attempt_id=attempt_id)
            # Optional operational pin for already committed prompt/config artifacts.
            # Omission preserves the historical T0 representation; never infer reuse at T3.
            if reused_artifact_ids: payload['reused_artifact_ids']=list(reused_artifact_ids)
            e=self._event(c,cmd,'prepared',payload)
            self._put_event(c,e);return cmd
        def probe(): return cmd if self.get_command(cmd) is not None else None
        return self._write(work,probe)

    def append_event(self,command_id,kind,payload,*,staged=()):
        identity=self.allocate_id()
        def work(c):
            require(kind not in ('finalized','application_applied','prepared'),'event_requires_atomic_boundary')
            if kind=='s01_dispatch_intent':
                self._active_claim(c,command_id,payload['answer_id'])
                lineage=self._command(c,command_id)['operation']['parent_command_id']
                while lineage:
                    old=self._command(c,lineage)
                    require(not any(e['kind']=='s01_dispatch_intent' for e in old['events']),'successor_must_not_redispatch')
                    lineage=old['operation']['parent_command_id']
            self._put_stages(c,command_id,staged);e=self._event(c,command_id,kind,payload,identity);self._put_event(c,e);return e
        def probe():
            value=self.get_command(command_id)
            return next((e for e in value['events'] if e['event_id']==identity),None) if value else None
        return self._write(work,probe)

    def _active_claim(self,c,command_id,answer_id):
        row=c.execute('SELECT active_command_id FROM application_heads WHERE answer_id=?',(answer_id,)).fetchone()
        require(row is not None and row[0]==command_id,'active_application_claim')
        require(not c.execute("SELECT 1 FROM operation_events WHERE kind='application_applied' AND answer_id=?",(answer_id,)).fetchone(),'answer_already_applied')

    def _base_error(self,c,operation):
        request=operation['request']
        if request['kind'] in ('start','recovery'): return None
        row=c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(operation['session_id'],)).fetchone()
        if row[0]!=request['base_model_id']:
            return S02Error('MODEL_CONFLICT','revision','Model head changed',details={'expected_model_id':row[0],'provided_model_id':request['base_model_id']})
        if row[1]!=request['base_analysis_set_id']:
            return S02Error('ANALYSIS_CONFLICT','revision','AnalysisSet head changed',details={'expected_analysis_set_id':row[1],'provided_analysis_set_id':request['base_analysis_set_id']})
        if row[0]:
            current=decode(c.execute('SELECT record_json FROM records WHERE id=?',(row[0],)).fetchone()[0].encode('ascii'))
            require(current['body']['source_context_id']==request['source_context_id'],'operation_base_source')
        return None

    def finalize(self,command_id,records,*,blobs=None,promotions=(),head=None,application_events=()):
        """Atomic T3; callers are code, never untrusted exports or CLI JSON."""
        blobs=blobs or {}
        # Detached exact trees: no caller mutation while constructing final outcome.
        records=decode(encode(records));promotions=decode(encode(list(promotions)))
        def work(c):
            op=self._command(c,command_id)
            if op['state']=='finalized': return op['run']
            operation=op['operation'];runid=operation['reserved_run_id']
            run=next((r for r in records if r['id']==runid and r['type']=='run'),None)
            require(run is not None and run['body']['command_id']==command_id,'final_run_identity')
            conflict=self._base_error(c,operation)
            batch=records
            final_head=head;extra_events=application_events
            if conflict:
                batch=[r for r in records if r['type'] in ('artifact','run')]
                run['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=[conflict.error])
                final_head=None;extra_events=()
            if not conflict:
                new_records={r['id']:r for r in batch}
                if final_head is None:
                    require(run['body']['result_model_id'] is None and run['body']['result_analysis_set_id'] is None,'run_without_publication')
                else:
                    require(run['body']['result_analysis_set_id']==final_head[1] and final_head[1] in new_records and new_records[final_head[1]]['type']=='analysis_set','run_published_set')
                    if run['body']['result_model_id'] is not None:
                        require(run['body']['result_model_id']==final_head[0] and final_head[0] in new_records and new_records[final_head[0]]['type']=='model','run_published_model')
                    else: require(final_head[0]==operation['request'].get('base_model_id'),'analysis_only_model_unchanged')
                current=c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(operation['session_id'],)).fetchone()
                target=final_head or tuple(current)
                known={r['id']:r for r in batch}
                def known_body(identity):
                    if identity in known:return known[identity]['body']
                    row=c.execute('SELECT record_json FROM records WHERE id=?',(identity,)).fetchone()
                    require(row is not None,'publication_reference');return decode(row[0].encode('ascii'))['body']
                for r in batch:
                    if r['type'] in ('validation','bundle','review','handoff'):
                        body=r['body'];setid=known_body(body['bundle_id'])['analysis_set_id'] if r['type']=='review' else body['analysis_set_id']
                        require((body['model_id'],setid)==tuple(target),'publication_pinned_head_pair')
            self._hook('before_finalize_insert',c)
            self._put_records(c,operation['session_id'],batch,blobs)
            for r in batch:
                if r['type']=='review':
                    b=r['body'];previous=c.execute('SELECT review_id FROM active_reviews WHERE bundle_id=?',(b['bundle_id'],)).fetchone()
                    require((previous[0] if previous else None)==b['supersedes_review_id'],'active_review_cas')
                    if previous: c.execute('UPDATE active_reviews SET review_id=? WHERE bundle_id=? AND review_id=?',(r['id'],b['bundle_id'],previous[0]))
                    else:c.execute('INSERT INTO active_reviews VALUES (?,?)',(b['bundle_id'],r['id']))
            self._hook('after_records',c)
            for promotion in promotions:
                ref=promotion['stage_ref'];require(ref['command_id']==command_id,'promotion_owner')
                c.execute('INSERT INTO promotions VALUES (?,?,?)',(command_id,ref['blob_id'],promotion['artifact_id']))
            for kind,payload,identity in extra_events:
                require(kind=='application_applied','final_application_event_kind')
                self._active_claim(c,command_id,payload['answer_id'])
                self._put_event(c,self._event(c,command_id,kind,payload,identity))
            if final_head:
                model,setid=final_head;req=operation['request']
                expected=(req.get('base_model_id'),req.get('base_analysis_set_id'))
                row=c.execute('UPDATE sessions SET head_model_id=?,head_analysis_set_id=? WHERE session_id=? AND head_model_id IS ? AND head_analysis_set_id IS ?',(model,setid,operation['session_id'],*expected))
                require(row.rowcount==1,'head_pair_cas')
            self._put_event(c,self._event(c,command_id,'finalized',dict(run_id=runid,promotions=promotions)))
            self._hook('after_finalize',c);return run
        def probe():
            cmd=self.get_command(command_id)
            return cmd['run'] if cmd and cmd['state']=='finalized' else None
        return self._write(work,probe)

    def _command(self,c,command_id):
        row=c.execute('SELECT * FROM operations WHERE command_id=?',(command_id,)).fetchone()
        if not row: return None
        op=dict(command_id=row['command_id'],session_id=row['session_id'],parent_command_id=row['parent_command_id'],reserved_run_id=row['reserved_run_id'],request=decode(row['request_json'].encode('ascii')))
        events=[dict(event_id=r['event_id'],command_id=command_id,ordinal=r['ordinal'],kind=r['kind'],payload=decode(r['payload_json'].encode('ascii'))) for r in c.execute('SELECT * FROM operation_events WHERE command_id=? ORDER BY ordinal',(command_id,))]
        stages=[{k:r[k] for k in ('command_id','blob_id','media_type','purpose','sha256','byte_length')} for r in c.execute('SELECT * FROM staged_blobs WHERE command_id=? ORDER BY blob_id',(command_id,))]
        kinds=[e['kind'] for e in events];state='finalized' if 'finalized' in kinds else 'interrupted' if 'interrupted' in kinds else 'captured' if 'response_received' in kinds else 'dispatch_unknown' if 'dispatch_intent' in kinds else 'prepared'
        run=None
        if state=='finalized':
            r=c.execute('SELECT record_json FROM records WHERE id=?',(row['reserved_run_id'],)).fetchone();require(r is not None,'finalized_run_missing');run=decode(r[0].encode('ascii'))
        return dict(operation=op,state=state,events=events,staged_blobs=stages,run=run)

    def _check(self,c):
        require(not c.execute('PRAGMA foreign_key_check').fetchall(),'foreign_key_check')
        records={};owners={};blobs={};commands={};events={};stages={}
        for row in c.execute('SELECT * FROM records'):
            raw=row['record_json'].encode('ascii');r=decode(raw);shape(r)
            require(digest(raw)==row['sha256'] and (r['id'],r['type'],r['created_at'])==(row['id'],row['type'],row['created_at']),'record_columns_hash')
            records[r['id']]=r;owners[r['id']]=row['session_id'];self._links(c,r['id'],fields(r),'record')
        for row in c.execute('SELECT * FROM artifacts'):
            r=records[row['record_id']];b=r['body'];raw=row['bytes']
            require(r['type']=='artifact' and (b['producer_run_id'],b['sha256'],b['byte_length'])==(row['producer_run_id'],row['sha256'],row['byte_length']) and digest(raw)==b['sha256'] and len(raw)==b['byte_length'],'artifact_columns_hash')
            blobs[r['id']]=raw
        require(set(blobs)=={i for i,r in records.items() if r['type']=='artifact'},'artifact_inventory')
        for row in c.execute('SELECT * FROM operations'):
            cmd=self._command(c,row['command_id']);op=cmd['operation'];shape(op,'Operation')
            require(digest(row['request_json'].encode('ascii'))==row['sha256'],'operation_hash');commands[op['command_id']]=op
            for e in cmd['events']:
                shape(e,'OperationEvent');events[(e['command_id'],e['event_id'])]=e
                self._links(c,e['event_id'],walk_schema(e,SCHEMA['$defs'][e['kind']+'Event']),'event')
        for row in c.execute('SELECT * FROM operation_events'):
            e=events[row['command_id'],row['event_id']]
            require(digest(row['payload_json'].encode('ascii'))==row['sha256'] and row['answer_id']==e['payload'].get('answer_id'),'event_columns_hash')
        for row in c.execute('SELECT * FROM staged_blobs'):
            item={k:row[k] for k in ('command_id','blob_id','media_type','purpose','sha256','byte_length')};shape(item,'StagedBlob')
            require(digest(row['bytes'])==row['sha256'] and len(row['bytes'])==row['byte_length'],'stage_hash')
            stages[row['command_id'],row['blob_id']]={**item,'bytes':row['bytes']}
        snapshots={}
        for r in records.values():
            if r['type']=='source_context':
                snap=verify_archive(r,records,blobs);snapshots[snap['snapshot_id']]=snap
        for r in records.values():
            same={i:v for i,v in records.items() if owners[i]==owners[r['id']]}
            snapshot_ids={v['body']['snapshot_id'] for v in same.values() if v['type']=='source_context'}
            same_commands={cmd:op for cmd,op in commands.items() if op['session_id']==owners[r['id']]}
            validate_record(r,same,{i:snapshots[i] for i in snapshot_ids},events=events,stages=stages,commands=same_commands)
        self._check_heads(c,records,owners,snapshots)
        from .events import validate_operations
        validate_operations(commands,events,stages,records,owners,snapshots)
        for row in c.execute('SELECT * FROM promotions'):
            stage=stages[row['command_id'],row['blob_id']];artifact=records[row['artifact_id']]['body']
            require(stage['bytes']==blobs[row['artifact_id']] and stage['purpose']==artifact['purpose'] and stage['media_type']==artifact['media_type'] and artifact['producer_run_id']==commands[row['command_id']]['reserved_run_id'],'promotion_exact_bytes')
        declared={(e['command_id'],p['stage_ref']['blob_id'],p['artifact_id']) for e in events.values() if e['kind']=='finalized' for p in e['payload']['promotions']}
        require(declared=={tuple(r) for r in c.execute('SELECT * FROM promotions')},'promotion_manifest')
        for row in c.execute('SELECT * FROM application_heads'):
            op=commands[row['active_command_id']];require(op['request'].get('answer_id')==row['answer_id'],'application_claim_identity')
        for row in c.execute('SELECT * FROM active_reviews'):
            review=records[row['review_id']]
            require(review['type']=='review' and review['body']['bundle_id']==row['bundle_id'] and records[row['bundle_id']]['type']=='bundle','active_review_binding')
        return records,blobs,commands,events,stages

    def _check_heads(self,c,records,owners,snapshots):
        modelrows={r['record_id']:r for r in c.execute('SELECT * FROM models')}
        setrows={r['record_id']:r for r in c.execute('SELECT * FROM analysis_sets')}
        require(set(modelrows)=={i for i,r in records.items() if r['type']=='model'} and set(setrows)=={i for i,r in records.items() if r['type']=='analysis_set'},'revision_index_inventory')
        for i,row in modelrows.items():
            b=records[i]['body'];require((owners[i],b['revision'],b['parent_model_id'],b['source_context_id'])==(row['session_id'],row['revision'],row['parent_id'],row['source_context_id']),'model_columns')
        for i,row in setrows.items():
            b=records[i]['body'];require((b['model_id'],b['revision'],b['parent_set_id'])==(row['model_id'],row['revision'],row['parent_set_id']),'analysis_columns')
        for s in c.execute('SELECT * FROM sessions'):
            models=[r for i,r in records.items() if owners[i]==s['session_id'] and r['type']=='model']
            if models:
                head=max(models,key=lambda r:r['body']['revision']);require(head['id']==s['head_model_id'],'model_head_latest')
                sets=[r for r in records.values() if r['type']=='analysis_set' and r['body']['model_id']==head['id']]
                require(sets and max(sets,key=lambda r:r['body']['revision'])['id']==s['head_analysis_set_id'],'analysis_head_latest')
            else: require(s['head_model_id'] is None and s['head_analysis_set_id'] is None,'empty_heads')
            for i,r in records.items():
                if owners[i]==s['session_id'] and r['type']=='source_context': require(snapshots[r['body']['snapshot_id']]['spec_id']==s['spec_id'],'session_one_spec')
            # Logical IDs can survive revisions, but never change element kind.
            kinds={}
            for m in sorted(models,key=lambda r:r['body']['revision']):
                from .validation import COLLECTIONS
                for k in COLLECTIONS:
                    for e in m['body'][k]:
                        require(e['id'] not in kinds or kinds[e['id']]==k,'logical_id_kind_stable');kinds[e['id']]=k

    def verify(self):
        with self._read() as c: self._check(c)

    def get_record(self,identity):
        with self._read() as c: return self._check(c)[0].get(identity)

    def get_blob(self,identity):
        with self._read() as c: return self._check(c)[1].get(identity)

    def get_stage(self,command_id,blob_id):
        with self._read() as c: return self._check(c)[4].get((command_id,blob_id))

    def get_command(self,command_id):
        with self._read() as c:
            self._check(c);return self._command(c,command_id)

    def heads(self,session_id):
        with self._read() as c:
            self._check(c);row=c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(session_id,)).fetchone()
            return tuple(row) if row else None

    def check_freshness(self,identity):
        with self._read() as c:
            records=self._check(c)[0];r=records.get(identity)
            if r is None: return None
            b=r['body'];row=c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=(SELECT session_id FROM records WHERE id=?)',(identity,)).fetchone()
            if b.get('model_id')!=row[0]: raise S02Error('REVISION_MISMATCH','review','Record is historical',details={'expected_model_id':row[0],'provided_model_id':b.get('model_id')})
            setid=b.get('analysis_set_id')
            if r['type']=='review': setid=records[b['bundle_id']]['body']['analysis_set_id']
            if setid!=row[1]: raise S02Error('ANALYSIS_STALE','review','AnalysisSet changed; new review required',details={'expected_analysis_set_id':row[1],'provided_analysis_set_id':setid})
            if r['type'] in ('review','handoff'):
                active=c.execute('SELECT review_id FROM active_reviews WHERE bundle_id=?',(b['bundle_id'],)).fetchone()
                reviewid=r['id'] if r['type']=='review' else b['review_id']
                require(active is not None and active[0]==reviewid and records[reviewid]['body']['decision']!='revoked','active_review_required')
            return r
