from copy import deepcopy
from decimal import Decimal
import hashlib
import sqlite3
import pytest
from dacn_s01.repository import Repository as S01Repository
from dacn_s01.service import Service as S01Service
from dacn_s01.codec import serialize_json,parse_json
from dacn_s02.repository import Repository,record
from dacn_s02.service import Service,staged,artifact
from dacn_s02.errors import S02Error
from dacn_s02.validation import shape
from helpers import model,aset,issue,run,allscope,source,evidence

def test_unchanged_intake_selected_history_and_raw(foundation):
    f=foundation;old=f.s01env;spec=old['snapshot']['spec_id'];request=dict(mode='update',spec_id=spec,base_revision=1)
    original=source();raw=b' \n'+serialize_json(original)+b'\n';same=S01Service(f.s01).submit(raw,request)
    assert same['result_kind']=='unchanged'
    original['functional_requirements'][0]['priority']='should';changed=S01Service(f.s01).submit(serialize_json(original),request)
    assert changed['snapshot']['revision']==2
    before=hashlib.sha256(f.s01.path.read_bytes()).hexdigest()
    result=Service(f.repo).start(f.s01.path,'synthetic',same['run']['run_id'],expected_snapshot_id=old['snapshot']['snapshot_id'])
    r=Repository(f.repo.path);ctx=r.get_record(result['source_context_id'])['body']
    assert ctx['snapshot_id']==old['snapshot']['snapshot_id']
    assert ctx['run_source_artifact_id']!=ctx['origin_source_artifact_id']
    assert r.get_blob(ctx['run_source_artifact_id'])==raw
    assert r.get_blob(ctx['origin_source_artifact_id'])==f.raw
    assert hashlib.sha256(f.s01.path.read_bytes()).hexdigest()==before
    assert r.heads(result['session_id'])==(None,None)

def test_precise_source_archive(tmp_path):
    s1=S01Repository(tmp_path/'one');s1.initialize();payload=source()
    payload['constraints']=[dict(id='C',text='Preserve numeric data',priority='must',acceptance_criteria=[],constraint=dict(kind='exact',value={'big':Decimal('123456789012345678901234567890'),'decimal':Decimal('0.12345678901234567890123456789'),'unknown':None}))]
    raw=serialize_json(payload);env=S01Service(s1).submit(raw,dict(mode='create',spec_id=None,base_revision=None))
    r=Repository(tmp_path/'two');r.initialize();out=Service(r).start(s1.path,'synthetic',env['run']['run_id'])
    r=Repository(r.path);ctx=r.get_record(out['source_context_id'])['body']
    assert r.get_blob(ctx['run_source_artifact_id'])==raw
    archived=parse_json(r.get_blob(ctx['envelope_artifact_id']))
    assert archived['snapshot']['input']['constraints'][0]['constraint']['value']==payload['constraints'][0]['constraint']['value']

def test_intake_rejects_missing_and_ineligible(foundation):
    f=foundation
    for run_id,code in [('missing','SOURCE_NOT_FOUND'),(S01Service(f.s01).submit(b'{',None)['run']['run_id'],'SOURCE_NOT_ELIGIBLE')]:
        with pytest.raises(S02Error) as e: Service(f.repo).start(f.s01.path,'synthetic',run_id)
        assert e.value.error['code']==code
    with pytest.raises(S02Error): Service(f.repo).start(f.s01.path,'synthetic',f.s01env['run']['run_id'],expected_snapshot_id='wrong')

def test_checked_adapter_never_accepts_json_or_calls_s01_writes(foundation,monkeypatch):
    f=foundation
    def forbidden(*args,**kwargs):raise AssertionError('S01 mutation forbidden during intake')
    monkeypatch.setattr(S01Repository,'initialize',forbidden);monkeypatch.setattr(S01Service,'submit',forbidden)
    out=Service(f.repo).start(f.s01.path,'synthetic',f.s01env['run']['run_id'])
    assert out['snapshot_id']==f.snapshot
    fake=f.tmp/'self-asserted-validated.json';fake.write_bytes(serialize_json(f.s01env))
    with pytest.raises(S02Error):Service(f.repo).start(fake,'synthetic',f.s01env['run']['run_id'])

def validation(m,a,identity='V1'):
    return record('validation',identity,dict(model_id=m['id'],analysis_set_id=a['id'],view_id=None,diagram_id=None,validator_version='phase1-test',checks=dict.fromkeys(['schema','references','mapping_inventory','freshness','view','conversion','render','fidelity'],'not_run'),errors=[],reported_issue_ids=a['body']['issue_ids'],completed_change_tasks=[],readability=dict(status='not_reviewed',reviewer=None,note=None)))

def test_f01_analysis_revision_log_freshness(foundation):
    f=foundation;m,a=f.initial();op=f.operation();f.repo.prepare(op)
    v=validation(m,a);f.repo.finalize(op['command_id'],[v,run(op,f.context,f.config)])
    assert f.repo.check_freshness('V1')['id']=='V1'
    f.repo.append_event(op['command_id'],'log',{'message':'Audit note only'})
    assert f.repo.heads(f.session)==('M1','AS1');assert f.repo.check_freshness('V1')==v
    op=f.operation();f.repo.prepare(op);q=issue(m);a2=aset(m,'AS2',a,issues=['Q2'])
    f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    r=Repository(f.repo.path);assert r.heads(f.session)==('M1','AS2');assert r.get_record('V1')==v
    with pytest.raises(S02Error) as e: r.check_freshness('V1')
    assert e.value.error['code']=='ANALYSIS_STALE'

def test_f01_no_drop_or_fork_current_issue(foundation):
    f=foundation;m,a=f.initial(True)
    op=f.operation();f.repo.prepare(op);a2=aset(m,'AS2',a,changed=[])
    with pytest.raises(S02Error) as e: f.repo.finalize(op['command_id'],[a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    assert e.value.error['details']['invariant']=='analysis_keys_not_dropped'
    assert f.repo.heads(f.session)==('M1','AS1') and f.repo.get_record('AS2') is None

@pytest.mark.parametrize('mutation,invariant',[
    (lambda m:m['body']['actions'][0]['actor_ids'].append('missing'),'action_initiator_actors'),
    (lambda m:m['body']['responsibilities'][0].update(component_id='missing'),'typed_local_reference_components'),
    (lambda m:m['body']['mappings'].append(deepcopy(m['body']['mappings'][0])),'model_ids_unique'),
    (lambda m:m['body']['mappings'][0]['source_ref'].update(input_pointer='/functional_requirements/0/text'),'mapping_source_kind'),
])
def test_invalid_graph_rollback(foundation,mutation,invariant):
    f=foundation;op=f.operation();f.repo.prepare(op);m=model(f.context,f.snapshot,op['reserved_run_id']);mutation(m);a=aset(m)
    with pytest.raises(S02Error) as e: f.repo.finalize(op['command_id'],[m,a,run(op,f.context,f.config,model_id=m['id'],set_id=a['id'])],head=(m['id'],a['id']))
    assert e.value.error['details']['invariant']==invariant
    assert f.repo.heads(f.session)==(None,None);assert f.repo.get_command(op['command_id'])['state']=='prepared'

def test_missing_mapping_and_source_ref(foundation):
    f=foundation;op=f.operation();f.repo.prepare(op);m=model(f.context,f.snapshot,op['reserved_run_id']);m['body']['mappings']=[];a=aset(m)
    with pytest.raises(S02Error) as e: f.repo.finalize(op['command_id'],[m,a,run(op,f.context,f.config,model_id=m['id'],set_id=a['id'])],head=(m['id'],a['id']))
    assert e.value.error['code']=='MAPPING_INVENTORY_INCOMPLETE'

def test_immutable_fk_unique_unknown_version(foundation):
    f=foundation;f.initial();c=sqlite3.connect(f.repo.path);c.execute('PRAGMA foreign_keys=ON')
    with pytest.raises(sqlite3.IntegrityError): c.execute("UPDATE records SET created_at='changed'")
    c.rollback()
    with pytest.raises(sqlite3.IntegrityError): c.execute('DELETE FROM records')
    c.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO record_links VALUES ('missing','x','missing')");c.commit()
    c.rollback();c.execute('PRAGMA user_version=99');c.close()
    with pytest.raises(S02Error): f.repo.initialize()
    with sqlite3.connect(f.repo.path) as c: assert c.execute('PRAGMA user_version').fetchone()[0]==99

def test_corruption_controlled(foundation):
    f=foundation;ctx=f.repo.get_record(f.context)['body']
    with sqlite3.connect(f.repo.path) as c:
        c.execute('DROP TRIGGER immutable_artifacts_update');c.execute("UPDATE artifacts SET bytes=zeroblob(byte_length) WHERE record_id=?",(ctx['run_source_artifact_id'],))
        from dacn_s02.storage_schema import DDL
        c.execute(DDL['immutable_artifacts_update'])
    with pytest.raises(S02Error) as e: f.repo.get_record(f.context)
    assert e.value.error['code']=='PERSISTENCE_FAILED'

@pytest.mark.parametrize('point',['after_stage','after_insert','before_commit','before_finalize_insert','after_records','after_finalize'])
def test_fault_rollback(foundation,point):
    f=foundation;op=f.operation();f.repo.prepare(op);f.repo=Repository(f.repo.path,_hook=lambda p,c:(_ for _ in ()).throw(OSError('injected')) if p==point else None)
    if point=='after_stage':
        call=lambda:f.repo.append_event(op['command_id'],'log',{'message':'Injected'},staged=[staged(op['command_id'],'Blob','llm_response',b'{')])
    else: call=lambda:f.repo.finalize(op['command_id'],[run(op,f.context,f.config)])
    with pytest.raises(S02Error): call()
    clean=Repository(f.repo.path);assert clean.get_command(op['command_id'])['state']=='prepared';assert clean.get_record(op['reserved_run_id']) is None
    evidence('fault_injection',point=point,outcome='rollback_checked_new_connection',heads=clean.heads(f.session))

def test_lost_commit_ack_reconciles(foundation):
    f=foundation;op=f.operation();f.repo.prepare(op)
    def hook(p,c):
        if p=='after_commit': raise OSError('Acknowledgement lost, commit already done')
    r=Repository(f.repo.path,_hook=hook);out=r.finalize(op['command_id'],[run(op,f.context,f.config)])
    assert out['id']==op['reserved_run_id'];assert Repository(r.path).get_command(op['command_id'])['state']=='finalized'
    assert r.finalize(op['command_id'],[])==out
    evidence('fault_injection',point='after_commit',outcome='reconciled_finalized_not_overwritten')

def test_real_lock_not_revision_conflict(foundation):
    f=foundation;op=f.operation();f.repo.prepare(op)
    c=sqlite3.connect(f.repo.path,autocommit=True);c.execute('BEGIN IMMEDIATE')
    try:
        with pytest.raises(S02Error) as e: Repository(f.repo.path,timeout=0.01).finalize(op['command_id'],[run(op,f.context,f.config)])
        assert e.value.error['code']=='PERSISTENCE_FAILED'
    finally: c.execute('ROLLBACK');c.close()
    assert Repository(f.repo.path).get_command(op['command_id'])['state']=='prepared'
    evidence('real_sqlite_lock',outcome='persistence_failure_not_conflict')

def test_id_collision_missing_lookup_and_clock(foundation):
    f=foundation
    with pytest.raises(S02Error): Repository(f.repo.path,_ids=lambda:f.context).allocate_id()
    assert f.repo.get_record('missing') is None and f.repo.get_command('missing') is None
    times=iter(['2026-01-02T00:00:00.000Z','2026-01-01T00:00:00.000Z'])
    r=Repository(f.repo.path,_clock=lambda:next(times));out=Service(r).start(f.s01.path,'synthetic',f.s01env['run']['run_id'])
    body=r.get_record(out['run_id'])['body'];assert body['started_at']==body['completed_at']=='2026-01-02T00:00:00.000Z'
