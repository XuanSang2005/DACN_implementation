"""P3 local migration protocol; all stores synthetic, no operational execution."""
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
from uuid import uuid4
import json,os,sqlite3,subprocess,sys
import pytest
from dacn_s02.migration import Migration,LAYOUTS,rows
from dacn_s02.errors import S02Error
from dacn_s02.repository import Repository
from dacn_s02.codec_boundary import encode
from migration_fixtures import make_migration
from helpers import evidence,operation,run

def disk(p):return {x.name:sha256(x.read_bytes()).hexdigest() for x in p.iterdir() if x.is_file()}

def test_golden_activation_lookup_and_e1_write(tmp_path,monkeypatch):
    m,r,f=make_migration(tmp_path);before=disk(m.source);opens=[];original=sqlite3.connect
    def connect(path,*a,**kw):opens.append(str(path));return original(path,*a,**kw)
    monkeypatch.setattr(sqlite3,'connect',connect)
    inspected=m.inspect(offline=True);assert inspected['status']=='eligible' and not m.destination.exists()
    copied=m.copy(r,offline=True);assert copied['status']=='committed_inactive'
    assert m.reconcile(r,offline=True)==copied
    with pytest.raises(S02Error):m.target.assert_writable()
    rr=r.read_bytes();a=m.activate(r,offline=True,confirm=True,operator='SYNTHETIC TEST')
    assert a['status']=='active' and m.activate(r,offline=True,confirm=True,operator='OTHER')==a
    old=r.parent/'old-command.json';old.write_bytes(encode(dict(receipt_version='s02/1',state_dir=str(m.source),command_id=f['command_id'])))
    assert m.lookup_migrated(old,r,offline=True)['operation']['command_id']==f['command_id']
    op=operation(f['session'],f['context'],m.target.heads(f['session']));m.target.prepare(op)
    assert not m.reconcile(r,offline=True)['rollback_eligible']
    m.target.finalize(op['command_id'],[run(op,f['context'],f['config'])]);m.target.verify()
    assert not m.reconcile(r,offline=True)['rollback_eligible']
    assert r.read_bytes()==rr and disk(m.source)==before
    source_opens=[u for u in opens if 'source/s02.sqlite3' in u]
    assert source_opens and all(u.endswith('?mode=ro') for u in source_opens)
    evidence('migration_golden',source_opens=source_opens,source_before=before,source_after=disk(m.source),copy=copied,activation=a,manifest=json.loads(m.target.store_info()['metadata']['migration_manifest']))

def test_empty_and_confirmation(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True)
    for work in (m.inspect,lambda:m.copy(r)):
        with pytest.raises(S02Error,match='confirmation'):work()
    assert not r.exists() and not m.destination.exists()
    assert m.copy(r,offline=True)['status']=='committed_inactive'
    with pytest.raises(S02Error):m.activate(r,offline=True,operator='x')

@pytest.mark.parametrize('point',['before_copy_'+n for n in LAYOUTS]+['after_copy_'+n for n in LAYOUTS]+['before_copy_commit','after_copy_commit','after_reserve'])
def test_copy_fault_same_receipt_no_reset(tmp_path,point):
    m,r,_=make_migration(tmp_path,empty=True);before=disk(m.source)
    def hook(p,c):
        if p==point:raise OSError('synthetic fault')
    m.hook=hook
    with pytest.raises((S02Error,OSError)):m.copy(r,offline=True)
    receipt=r.read_bytes();m.hook=lambda *a:None
    result=m.reconcile(r,offline=True)
    assert result['status']==('committed_inactive' if point=='after_copy_commit' else 'partial')
    if point=='after_copy_commit':assert m.copy(r,offline=True,resume=True)==result
    else:
        with pytest.raises(S02Error):m.copy(r,offline=True,resume=True)
    assert r.read_bytes()==receipt and disk(m.source)==before
    evidence('migration_copy_fault',point=point,result=result)

@pytest.mark.parametrize('point',['receipt_before_publish','receipt_before_dir_sync','receipt_durable','before_reserve'])
def test_receipt_ack_stops_before_effects(tmp_path,point):
    m,r,_=make_migration(tmp_path,empty=True)
    def hook(p,c):
        if p==point:raise OSError('lost receipt ACK')
    m.hook=hook
    with pytest.raises((S02Error,OSError)):m.copy(r,offline=True)
    assert not m.destination.exists()
    m.hook=lambda *a:None
    if r.exists():
        receipt=r.read_bytes();assert m.copy(r,offline=True,resume=True)['status']=='committed_inactive';assert r.read_bytes()==receipt
    else:
        with pytest.raises(S02Error):m.copy(r,offline=True,resume=True)

@pytest.mark.parametrize('point',['before_activation_commit','after_activation_commit'])
def test_activation_lost_ack(tmp_path,point):
    m,r,_=make_migration(tmp_path,empty=True);m.copy(r,offline=True);raw=r.read_bytes()
    def hook(p,c):
        if p==point:raise OSError('activation ACK')
    m.hook=hook
    with pytest.raises(S02Error):m.activate(r,offline=True,confirm=True,operator='first')
    m.hook=lambda *a:None;observed=m.reconcile(r,offline=True)
    assert observed['status']==('active' if point=='after_activation_commit' else 'committed_inactive')
    final=m.activate(r,offline=True,confirm=True,operator='retry')
    assert final['activation']['operator']==('first' if point=='after_activation_commit' else 'retry') and r.read_bytes()==raw

@pytest.mark.parametrize('field',['migration_id','target_store_id','activation_id','source_inventory_sha256'])
def test_identity_conflict_without_mutation(tmp_path,field):
    m,r,_=make_migration(tmp_path);m.copy(r,offline=True);before=disk(m.destination)
    receipt=json.loads(r.read_bytes());receipt[field]=str(uuid4()) if field.endswith('_id') else '0'*64
    other=r.parent/'other.json';other.write_bytes(encode(receipt))
    for work in (lambda:m.reconcile(other,offline=True),lambda:m.copy(other,offline=True,resume=True),lambda:m.activate(other,offline=True,confirm=True,operator='bad')):
        with pytest.raises(S02Error) as err:work()
        assert err.value.error['code']=='MIGRATION_IDENTITY_CONFLICT' and disk(m.destination)==before

@pytest.mark.parametrize('fault',['extra','missing','null','version','path','uuid','hash','lost'])
def test_invalid_receipt(tmp_path,fault):
    m,r,_=make_migration(tmp_path,empty=True)
    # Seed only a durable receipt by stopping before destination reservation.
    def hook(p,c):
        if p=='before_reserve':raise OSError('stop')
    m.hook=hook
    with pytest.raises(OSError):m.copy(r,offline=True)
    value=json.loads(r.read_bytes());m.hook=lambda *a:None
    if fault=='extra':value['extra']=1
    if fault=='missing':value.pop('activation_id')
    if fault=='null':value['activation_id']=None
    if fault=='version':value['receipt_version']='s02/2'
    if fault=='path':value['destination_state_dir']+='/../else'
    if fault=='uuid':value['activation_id']='not-uuid'
    if fault=='hash':value['source_inventory_sha256']='G'*64
    r.write_bytes(encode(value))
    if fault=='lost':r.unlink()
    with pytest.raises(S02Error) as err:m.copy(r,offline=True,resume=True)
    assert err.value.error['code']=='MIGRATION_RECEIPT_INVALID' and not m.destination.exists()

@pytest.mark.parametrize('extra',[
 "f.repo.prepare(f.operation())",
 "op=f.operation();f.repo.prepare(op);f.repo.append_event(op['command_id'],'interrupted',dict(reason='test'))",
])
def test_unfinalized_ineligible(tmp_path,extra):
    m,r,_=make_migration(tmp_path,extra);before=disk(m.source)
    with pytest.raises(S02Error) as err:m.copy(r,offline=True)
    assert err.value.error['code']=='MIGRATION_INELIGIBLE' and not r.exists() and not m.destination.exists() and disk(m.source)==before

@pytest.mark.parametrize('fault',['ddl','hash','selection','fresh'])
def test_invalid_source_and_db2_invariants(tmp_path,fault):
    m,r,_=make_migration(tmp_path)
    with sqlite3.connect(m.source_repo.path) as c:
        if fault=='ddl':c.execute('CREATE TABLE extra (id TEXT)')
        if fault=='hash':
            c.execute('DROP TRIGGER immutable_records_update');c.execute("UPDATE records SET sha256='bad'")
        if fault=='selection':c.execute("INSERT INTO active_reviews VALUES ('none','none')")
        if fault=='fresh':c.execute('PRAGMA user_version=2')
    before=disk(m.source)
    with pytest.raises(S02Error):m.copy(r,offline=True)
    assert not r.exists() and not m.destination.exists() and disk(m.source)==before

def test_path_guards(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True)
    for source in (m.destination,m.destination/'child',m.source.parent):
        with pytest.raises(S02Error):Migration(m.settings,source)
    link=tmp_path/'linked';link.symlink_to(m.source,target_is_directory=True)
    with pytest.raises(S02Error):Migration(m.settings,link)
    protected=replace(m.settings,protected=(m.source,))
    with pytest.raises(S02Error):Migration(protected,m.source)
    alias=tmp_path/'hardlink';os.link(m.source_repo.path,alias)
    with pytest.raises(S02Error):m.inspect(offline=True)

@pytest.mark.parametrize('reader',['DACN_LEGACY_PYTHON','DACN_P1_PYTHON'])
@pytest.mark.parametrize('downgrade',[False,True])
def test_migrated_rejected_by_legacy(tmp_path,reader,downgrade):
    m,r,_=make_migration(tmp_path);m.copy(r,offline=True)
    if downgrade:
        with sqlite3.connect(m.target.path) as c:c.execute('PRAGMA user_version=1')
    before=disk(m.destination)
    p=subprocess.run([os.environ[reader],'-B','-c','import sys;from dacn_s02.repository import Repository;Repository(sys.argv[1]).verify()',str(m.target.path)],capture_output=True,cwd=tmp_path)
    assert p.returncode!=0 and disk(m.destination)==before

@pytest.mark.parametrize('status',['unknown_outcome','transport_failed'])
def test_finalized_unobserved_call_is_not_eligible(tmp_path,status):
    extra="from test_audit_guards import test_unknown_call_keeps_dispatch_and_null_response;test_unknown_call_keeps_dispatch_and_null_response(f,"+repr(status)+")"
    m,r,_=make_migration(tmp_path,extra)
    # The accepted DB1 verifier admits this finalized history; migration eligibility does not.
    m.source_repo.verify();before=disk(m.source)
    with pytest.raises(S02Error) as err:m.copy(r,offline=True)
    assert err.value.error['code']=='MIGRATION_INELIGIBLE' and not r.exists() and disk(m.source)==before

@pytest.mark.parametrize('status',['stale','refused','invalid_output'])
def test_known_finalized_capture_preserves_raw_bytes(tmp_path,status):
    extra="from test_audit_guards import test_captured_status_keeps_exact_evidence;test_captured_status_keeps_exact_evidence(f,"+repr(status)+")"
    m,r,_=make_migration(tmp_path,extra);before=disk(m.source)
    assert m.copy(r,offline=True)['status']=='committed_inactive'
    assert m.target.get_blob('ArtResponse')==m.source_repo.get_blob('ArtResponse') and disk(m.source)==before

RICH='''
from test_lifecycle import add_answer,application_batch
from test_audit_guards import test_captured_status_keeps_exact_evidence
from dacn_s02.repository import record
from dacn_s02.scope import make_scope
from helpers import allscope
from test_repository import validation
m,a,answer=add_answer(f);op,batch,events=application_batch(f,m,a,answer)
f.repo.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events)
m=f.repo.get_record('M2');a=f.repo.get_record('AS-M2');op=f.operation();f.repo.prepare(op)
view=record('view','V',dict(model_id='M2',name='Synthetic',component_ids=['C1','C2'],interface_ids=[],dependency_ids=[],omitted_element_ids=[],scope_note='Not rendered',config_artifact_id=f.config))
diagram=record('diagram','D',dict(model_id='M2',view_id='V',converter_version='not_run',toolchain_artifact_id=f.config,status='not_run',puml_artifact_id=None,svg_artifact_id=None,aliases=[],validation_id=None))
v=validation(m,a,'Validation');v['body'].update(view_id='V',diagram_id='D')
bundle=record('bundle','Bundle',dict(model_id='M2',analysis_set_id='AS-M2',source_context_id=f.context,scenario_ids=[],characteristic_ids=[],issue_ids=['Q2-resolved'],answer_ids=['Answer1'],change_ids=['CH1'],view_id='V',diagram_id='D',validation_id='Validation',status='preparing_review',disclosures=['Synthetic only']))
review=record('review','Review',dict(bundle_id='Bundle',model_id='M2',source_context_id=f.context,reviewer='SYNTHETIC',decision='request_changes',supersedes_review_id=None,accepted_scope=make_scope('M2'),blocked_scope=allscope(m),workflow_choices=[],conditions=[],acknowledged_issue_ids=['Q2-resolved'],feedback='Synthetic'))
f.repo.finalize(op['command_id'],[view,diagram,v,bundle,review,run(op,f.context,f.config)])
test_captured_status_keeps_exact_evidence(f,'stale')
'''

def test_rich_db1_inventory_claim_review_and_bytes(tmp_path):
    m,r,_=make_migration(tmp_path,RICH,initial=False);before=disk(m.source)
    with m.source_repo._read() as c:original=rows(c)
    for table in ('sessions','records','operations','application_heads','active_reviews','staged_blobs','promotions','record_event_links','event_event_links','event_stage_links'):
        assert original[table],table
    m.copy(r,offline=True)
    with m.target._read() as c:assert rows(c)==original
    manifest=json.loads(m.target.store_info()['metadata']['migration_manifest'])
    assert set(manifest['tables'])==set(LAYOUTS) and disk(m.source)==before
    evidence('migration_rich_inventory',table_counts={n:len(v) for n,v in original.items()},source=before,manifest=manifest)

@pytest.mark.parametrize('fault',['missing_review_selection','stale_claim'])
def test_db1_read_compatibility_is_wider_than_migration(tmp_path,fault):
    m,r,_=make_migration(tmp_path,RICH,initial=False)
    with sqlite3.connect(m.source_repo.path) as c:
        if fault=='missing_review_selection':c.execute('DELETE FROM active_reviews')
        else:c.execute('DELETE FROM application_heads')
    m.source_repo.verify()  # pinned DB1 behavior intentionally preserved
    before=disk(m.source)
    with pytest.raises(S02Error):m.copy(r,offline=True)
    assert disk(m.source)==before and not r.exists() and not m.destination.exists()

def test_s01_dispatch_unobserved_finalized_blocks(tmp_path):
    extra='''
from test_lifecycle import test_f03_consent_exact_and_recovery_identity
test_f03_consent_exact_and_recovery_identity(f)
with f.repo._read() as c:cmd=c.execute("SELECT command_id FROM operations WHERE request_json LIKE '%apply_answer%'").fetchone()[0]
state=f.repo.get_command(cmd);op=state['operation'];consent=next(e for e in state['events'] if e['kind']=='consent_recorded')
f.repo.append_event(cmd,'s01_dispatch_intent',dict(answer_id='Answer1',consent_event=dict(command_id=cmd,event_id=consent['event_id']),s01_store_key='synthetic',s01_run_id='ReservedRun',s01_request=dict(mode='update',spec_id=f.s01env['snapshot']['spec_id'],base_revision=1),input_stage_ref=dict(command_id=cmd,blob_id='Input')))
f.repo.finalize(cmd,[run(op,f.context,f.config,status='interrupted')])
'''
    m,r,_=make_migration(tmp_path,extra,initial=False);m.source_repo.verify()
    with pytest.raises(S02Error) as err:m.copy(r,offline=True)
    assert err.value.error['code']=='MIGRATION_INELIGIBLE' and not r.exists()

def test_cli_explicit_protocol(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True);config=tmp_path/'config.toml';config.write_text('state_dir = '+json.dumps(str(m.destination))+'\n')
    base=[sys.executable,'-B','-m','dacn_s02','--config',str(config)]
    def call(command,*args):
        p=subprocess.run([*base,command,'--source-state-dir',str(m.source),'--offline-confirmed',*args],cwd=tmp_path,capture_output=True)
        assert p.returncode==0,p.stdout+p.stderr
        return json.loads(p.stdout)['result']
    assert call('migration-inspect')['status']=='eligible'
    assert call('migration-copy','--migration-receipt',str(r))['status']=='committed_inactive'
    assert call('migration-reconcile','--migration-receipt',str(r))['status']=='committed_inactive'
    assert call('migration-activate','--migration-receipt',str(r),'--confirm-activation','--operator','SYNTHETIC')['status']=='active'

def test_resume_activation_reconcile_never_reallocate_identity(tmp_path,monkeypatch):
    m,r,_=make_migration(tmp_path,empty=True)
    def stop(p,c):
        if p=='before_reserve':raise OSError('stop before effects')
    m.hook=stop
    with pytest.raises(OSError):m.copy(r,offline=True)
    raw=r.read_bytes();m.hook=lambda *a:None
    def forbidden():raise AssertionError('Resume must not allocate IDs')
    monkeypatch.setattr('dacn_s02.migration.uuid4',forbidden)
    m.copy(r,offline=True,resume=True);m.activate(r,offline=True,confirm=True,operator='SYNTHETIC');m.reconcile(r,offline=True)
    assert r.read_bytes()==raw

@pytest.mark.parametrize('field',['basis_sha256','profile_id'])
def test_activation_wrong_basis_profile_is_not_success(tmp_path,field):
    from dacn_s02.storage_schema import DDL
    m,r,_=make_migration(tmp_path,empty=True);m.copy(r,offline=True);m.activate(r,offline=True,confirm=True,operator='synthetic')
    with sqlite3.connect(m.target.path) as c:
        c.execute('DROP TRIGGER immutable_store_activation_update')
        c.execute('UPDATE store_activation SET '+field+'=?',('0'*64 if field=='basis_sha256' else 's02-profile/legacy-a3',))
        c.execute(DDL['immutable_store_activation_update'])
    before=disk(m.destination)
    for work in (lambda:m.reconcile(r,offline=True),lambda:m.activate(r,offline=True,confirm=True,operator='retry')):
        with pytest.raises(S02Error):work()
        assert disk(m.destination)==before

def test_valid_source_change_refuses_old_receipt(tmp_path):
    m,r,f=make_migration(tmp_path);m.copy(r,offline=True)
    code='''import sys,json
sys.path.insert(0,sys.argv[1])
from helpers import operation,run
from dacn_s02.repository import Repository
f=json.loads(sys.argv[3]);r=Repository(sys.argv[2]);op=operation(f['session'],f['context'],r.heads(f['session']));r.prepare(op);r.finalize(op['command_id'],[run(op,f['context'],f['config'])])
'''
    subprocess.run([os.environ['DACN_LEGACY_PYTHON'],'-B','-c',code,os.environ['DACN_BASELINE_HELPERS'],str(m.source_repo.path),json.dumps(f)],cwd=tmp_path,check=True)
    before=disk(m.destination)
    with pytest.raises(S02Error) as err:m.activate(r,offline=True,confirm=True,operator='test')
    assert err.value.error['code']=='MIGRATION_IDENTITY_CONFLICT' and disk(m.destination)==before

def test_finalized_stale_claim_is_copied_without_release(tmp_path):
    extra='''
from helpers import issue,aset
from test_lifecycle import add_answer
m,a,answer=add_answer(f)
old=f.operation(kind='apply_answer',answer_id='Answer1',issue_key='Question2');f.repo.prepare(old)
op=f.operation();f.repo.prepare(op)
q=issue(m,'Pending',parent='Q2',status='answered_pending_application');q['body']['answer_ids']=['Answer1']
a2=aset(m,'AS2',a,issues=['Pending'])
f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
f.repo.finalize(old['command_id'],[run(old,f.context,f.config)])
assert f.repo.get_command(old['command_id'])['run']['body']['status']=='stale'
'''
    m,r,_=make_migration(tmp_path,extra,initial=False)
    with m.source_repo._read() as c:claims=rows(c)['application_heads']
    assert claims;m.copy(r,offline=True)
    with m.target._read() as c:assert rows(c)['application_heads']==claims

def test_reconcile_trusted_external_review_bindings_after_e1_writes(tmp_path):
    from profile_fixtures import Graph
    from dacn_s02.profiles import L1
    from dacn_s02.resolution import HumanReviewEvidence
    m,r,meta=make_migration(tmp_path,RICH,initial=False);m.copy(r,offline=True);m.activate(r,offline=True,confirm=True,operator='synthetic')
    repo=m.target
    with repo._read() as c:records,blobs,commands,events,stages=repo._check(c)
    ids=set(records);meta={k:meta[k] for k in ('session','context','config','snapshot')}
    g=Graph(records,{i:L1 for i in records},{i:meta['session'] for i in records},commands,{i:L1 for i in commands},events,stages,blobs,**meta)
    q=g.carry(method='human_review',new_model=True);op=list(g.commands.values())[-1];batch=[v for i,v in g.records.items() if i not in ids]
    trusted=Repository(repo.path,reviews=g.reviews);trusted.prepare(op);trusted.finalize(op['command_id'],batch,head=(g.model_id,g.set_id))
    for bindings in (None,{q['id']:HumanReviewEvidence('wrong','0'*64,'applicable')}):
        with pytest.raises(S02Error):Migration(m.settings,m.source,reviews=bindings).reconcile(r,offline=True)
    result=Migration(m.settings,m.source,reviews=g.reviews).reconcile(r,offline=True)
    assert result['status']=='active' and not result['rollback_eligible']

@pytest.mark.parametrize('observation_status,new_unobserved_dispatch',[('rejected',False),('failed',False),('unknown',False),('rejected',True)])
def test_s01_observation_matches_exact_dispatch_across_lineage(tmp_path,observation_status,new_unobserved_dispatch):
    extra='''
from test_lifecycle import test_f03_consent_exact_and_recovery_identity
from helpers import issue,aset
from copy import deepcopy
test_f03_consent_exact_and_recovery_identity(f)
with f.repo._read() as c:cmd=c.execute("SELECT command_id FROM operations WHERE request_json LIKE '%apply_answer%'").fetchone()[0]
state=f.repo.get_command(cmd);old=state['operation'];consent=next(e for e in state['events'] if e['kind']=='consent_recorded')
payload=dict(answer_id='Answer1',consent_event=dict(command_id=cmd,event_id=consent['event_id']),s01_store_key='synthetic',s01_run_id='ReservedRun',s01_request=dict(mode='update',spec_id=f.s01env['snapshot']['spec_id'],base_revision=1),input_stage_ref=dict(command_id=cmd,blob_id='Input'))
dispatch=f.repo.append_event(cmd,'s01_dispatch_intent',payload)
m=f.repo.get_record('M1');a=f.repo.get_record('AS1');op=f.operation();f.repo.prepare(op)
q=issue(m,'Pending',parent='Q2',status='answered_pending_application');q['body']['answer_ids']=['Answer1']
a2=aset(m,'AS2',a,issues=['Pending']);f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
f.repo.finalize(cmd,[run(old,f.context,f.config)])
assert f.repo.get_command(cmd)['run']['body']['status']=='stale'
child=f.operation(kind='apply_answer',answer_id='Answer1',issue_key='Question2',parent=cmd);child['command_id']='0';f.repo.prepare(child,claim_from=cmd)
f.repo.append_event(child['command_id'],'s01_result_observed',dict(answer_id='Answer1',dispatch_event=dict(command_id=cmd,event_id=dispatch['event_id']),s01_run_id='ReservedRun',lookup_status='rejected',snapshot_id=None))
'''
    extra=extra.replace("lookup_status='rejected'","lookup_status="+repr(observation_status))
    if new_unobserved_dispatch:
        # Synthetic fault fixture: the old writer refuses redispatch, but the
        # pinned L1 reader admits it. Migration must match each actual dispatch.
        extra+="payload=deepcopy(payload);payload['s01_run_id']='SecondReservedRun'\n"
        extra+="def inject(c):f.repo._put_event(c,f.repo._event(c,child['command_id'],'s01_dispatch_intent',payload))\n"
        extra+="f.repo._write(inject,lambda:None)\n"
    extra+="f.repo.finalize(child['command_id'],[run(child,f.context,f.config)])\n"
    m,r,_=make_migration(tmp_path,extra,initial=False);m.source_repo.verify()
    if new_unobserved_dispatch or observation_status=='unknown':
        with pytest.raises(S02Error) as err:m.copy(r,offline=True)
        assert err.value.error['code']=='MIGRATION_INELIGIBLE' and not r.exists()
    else:assert m.copy(r,offline=True)['status']=='committed_inactive'
