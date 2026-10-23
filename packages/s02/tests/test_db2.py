"""P2 synthetic storage tests, distinct from frozen DB1/P1 oracles."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,os,sqlite3,subprocess,sys
import pytest
from dacn_s02.repository import Repository
from dacn_s02.profiles import L1,E1,REGISTRY
from dacn_s02.storage_schema import DDL,DDL1,DB_VERSION
from dacn_s02.errors import S02Error
from dacn_s02.codec_boundary import encode
from helpers import operation,run,aset,evidence
from p2_helpers import Foundation,issue

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mutate(path,table,sql,params=()):
    with sqlite3.connect(path) as c:
        for action in ('update','delete'):c.execute('DROP TRIGGER immutable_'+table+'_'+action)
        c.execute(sql,params)
        for action in ('update','delete'):c.execute(DDL['immutable_'+table+'_'+action])

@pytest.fixture
def p2(tmp_path):return Foundation(tmp_path)

def test_fresh_exact_atomic_and_immutable(tmp_path):
    repo=Repository(tmp_path/'fresh.sqlite3');repo.initialize(operator='SYNTHETIC INIT')
    repo.verify();info=repo.store_info();before=repo.path.read_bytes();repo.initialize()
    assert repo.path.read_bytes()==before and info==repo.store_info() and info['db_version']==2
    with sqlite3.connect(repo.path) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==DB_VERSION==2
        assert dict(c.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))==DDL
        assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
        for p in REGISTRY.values():assert c.execute('SELECT * FROM schema_profiles WHERE profile_id=?',(p.profile_id,)).fetchone()==(p.profile_id,p.schema_bytes,p.schema_sha256,p.descriptor_bytes,p.descriptor_sha256)
        for table in ('schema_profiles','store_metadata','store_activation'):
            for sql in (f'DELETE FROM {table}',f'UPDATE {table} SET '+ ('slot=slot' if table!='schema_profiles' else 'profile_id=profile_id')):
                with pytest.raises(sqlite3.IntegrityError):c.execute(sql)
    evidence('db2_identity',store=info)

@pytest.mark.parametrize('point',['before_init_commit','after_init_commit'])
def test_fresh_init_fault_reopen(tmp_path,point):
    path=tmp_path/'fresh.sqlite3'
    def hook(at,c):
        if at==point:raise OSError('synthetic ACK fault')
    with pytest.raises(S02Error):Repository(path,_hook=hook).initialize()
    with sqlite3.connect(path) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==(2 if point=='after_init_commit' else 0)
        assert bool(c.execute("SELECT name FROM sqlite_master WHERE name='store_activation'").fetchall())==(point=='after_init_commit')
    if point=='after_init_commit':Repository(path).verify()

def test_inactive_checked_read_no_write_or_auto_activate(p2):
    r=p2.repo;mutate(r.path,'store_activation','DELETE FROM store_activation');r.verify();before=r.path.read_bytes()
    for work in (r.initialize,lambda:r.prepare(p2.operation()),lambda:r.append_event(p2.result['command_id'],'log',dict(message='x')),lambda:r.finalize(p2.result['command_id'],[])):
        with pytest.raises(S02Error,match='inactive'):work()
        assert r.path.read_bytes()==before
    assert r.store_info()['activation'] is None

@pytest.mark.parametrize('table,sql,params',[
 ('schema_profiles','UPDATE schema_profiles SET schema_sha256=? WHERE profile_id=?',('0'*64,E1)),
 ('schema_profiles','UPDATE schema_profiles SET schema_bytes=? WHERE profile_id=?',(b'{}',L1)),
 ('schema_profiles','UPDATE schema_profiles SET descriptor_bytes=? WHERE profile_id=?',(b'{"rules_id":"unknown"}',E1)),
 ('schema_profiles','UPDATE schema_profiles SET descriptor_sha256=? WHERE profile_id=?',('0'*64,E1)),
 ('schema_profiles','DELETE FROM schema_profiles WHERE profile_id=?',(L1,)),
 ('store_metadata','UPDATE store_metadata SET write_profile_id=?',(L1,)),
 ('store_activation','UPDATE store_activation SET profile_id=?',(L1,)),
 ('store_activation','UPDATE store_activation SET basis_sha256=?',('0'*64,)),
 ('store_activation','UPDATE store_activation SET store_id=?',('ffffffff-ffff-4fff-8fff-ffffffffffff',)),
 ('records','UPDATE records SET profile_id=?',('unknown',)),
 ('operations','UPDATE operations SET profile_id=?',('unknown',)),
])
def test_corrupt_owner_registry_rejects_whole_store(p2,table,sql,params):
    mutate(p2.repo.path,table,sql,params);before=p2.repo.path.read_bytes()
    for work in (p2.repo.verify,lambda:p2.repo.get_record('missing'),lambda:p2.repo.prepare(p2.operation(base=(None,None)))):
        with pytest.raises(S02Error):work()
        assert p2.repo.path.read_bytes()==before

def test_owner_lookup_raw_and_no_profile_override(p2):
    f=p2;m,a=f.initial(True);q=f.repo.get_record('Q2');value=f.repo.lookup_record('Q2')
    assert value==dict(profile_id=E1,record=q)
    with sqlite3.connect(f.repo.path) as c:raw=c.execute("SELECT record_json FROM records WHERE id='Q2'").fetchone()[0].encode('ascii')
    assert f.repo.lookup_record('Q2',raw=True)==dict(profile_id=E1,record=raw)
    cmd=f.result['command_id'];command=f.repo.lookup_command(cmd)
    assert command['profile_id']==E1
    for ev in command['events']:assert f.repo.lookup_event(cmd,ev['event_id'])==dict(profile_id=E1,event=ev)
    for st in command['staged_blobs']:assert f.repo.lookup_stage(cmd,st['blob_id'])['profile_id']==E1
    op=f.operation();op['profile_id']=L1
    with pytest.raises(S02Error):f.repo.prepare(op)
    op=f.operation();f.repo.prepare(op);old=f.repo.path.read_bytes()
    with pytest.raises(S02Error):f.repo.append_event(op['command_id'],'log',dict(message='x',profile_id=L1))
    assert f.repo.path.read_bytes()==old
    q=issue(m,'next',parent='Q2');del q['body']['resolution_carry'];del q['body']['resolution_replacement']
    new=aset(m,'AS-next',a,issues=['next'])
    with pytest.raises(S02Error):f.repo.finalize(op['command_id'],[q,new,run(op,f.context,f.config,set_id=new['id'])],head=(m['id'],new['id']))
    assert f.repo.heads(f.session)==('M1','AS1') and f.repo.get_record('next') is None

def test_downgrade_label_and_reopen_link_inventory(p2):
    p2.initial(True);mutate(p2.repo.path,'records',"UPDATE records SET profile_id=? WHERE id='Q2'",(L1,))
    with pytest.raises(S02Error):Repository(p2.repo.path).verify()

def test_missing_typed_link_rejected(p2):
    p2.initial(True);mutate(p2.repo.path,'record_links',"DELETE FROM record_links WHERE owner_id='Q2'")
    with pytest.raises(S02Error):Repository(p2.repo.path).get_record('Q2')

def test_duplicate_reserved_run_prepared(p2):
    a=p2.operation();p2.repo.prepare(a);b=p2.operation();b['reserved_run_id']=a['reserved_run_id']
    with pytest.raises(S02Error):p2.repo.prepare(b)
    assert p2.repo.get_command(b['command_id']) is None

def test_db1_first_connection_ro_and_write_refusal(tmp_path,monkeypatch):
    # Baseline process creates synthetic history; no installed P2 write into DB1.
    baseline=os.environ['DACN_P1_PYTHON'];helpers=os.environ['DACN_BASELINE_HELPERS'];d=tmp_path/'old';d.mkdir()
    code="import sys;sys.path.insert(0,sys.argv[1]);from helpers import Foundation;f=Foundation(sys.argv[2]);f.initial(True)"
    subprocess.run([baseline,'-B','-c',code,helpers,str(d)],check=True,cwd=tmp_path)
    path=d/'s02.sqlite3';before=path.read_bytes();opens=[];connect=sqlite3.connect
    def observed(database,*a,**kw):opens.append(str(database));return connect(database,*a,**kw)
    monkeypatch.setattr(sqlite3,'connect',observed);r=Repository(path);r.verify()
    assert r.lookup_record('Q2')['profile_id']==L1
    for work in (r.initialize,lambda:r.prepare(operation('s','ctx')),lambda:r.append_event('missing','log',dict(message='x')),lambda:r.finalize('missing',[])):
        with pytest.raises(S02Error) as err:work()
        assert err.value.error['code']=='MIGRATION_REQUIRED'
    assert opens and all('mode=ro' in uri for uri in opens) and path.read_bytes()==before
    evidence('db1_readonly',opens=opens,before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=sha(path))

@pytest.mark.parametrize('downgrade',[False,True])
@pytest.mark.parametrize('reader',['DACN_P1_PYTHON','DACN_LEGACY_PYTHON'])
def test_baseline_reader_rejects_db2_without_mutation(p2,downgrade,reader):
    path=p2.repo.path
    if downgrade:
        with sqlite3.connect(path) as c:c.execute('PRAGMA user_version=1')
    before=path.read_bytes()
    code="import sys;from dacn_s02.repository import Repository;Repository(sys.argv[1]).verify()"
    r=subprocess.run([os.environ[reader],'-B','-c',code,str(path)],capture_output=True,cwd=path.parent)
    assert r.returncode!=0 and b'S02Error' in r.stderr and path.read_bytes()==before

@pytest.fixture
def mixed(tmp_path,request):
    """Fixture seeding only: fixed synthetic DB1 tables, never a migration API."""
    old=tmp_path/'legacy';old.mkdir();info=tmp_path/'fixture.json'
    code="""import sys,json
sys.path.insert(0,sys.argv[1])
from helpers import Foundation
from profile_fixtures import graph
f=Foundation(sys.argv[2]);g=graph(f)
from dacn_s02.repository import record
from dacn_s02.scope import make_scope
from helpers import run,allscope
from test_repository import validation
m=g.records['M2'];a=g.records['AS-M2'];op=f.operation();f.repo.prepare(op)
view=record('view','LegacyView',dict(model_id='M2',name='Synthetic view',component_ids=['C1','C2'],interface_ids=[],dependency_ids=[],omitted_element_ids=[],scope_note='Not rendered',config_artifact_id=f.config))
diagram=record('diagram','LegacyDiagram',dict(model_id='M2',view_id=view['id'],converter_version='not_run',toolchain_artifact_id=f.config,status='not_run',puml_artifact_id=None,svg_artifact_id=None,aliases=[],validation_id=None))
v=validation(m,a,'LegacyValidation');v['body'].update(view_id=view['id'],diagram_id=diagram['id'])
bundle=record('bundle','LegacyBundle',dict(model_id='M2',analysis_set_id='AS-M2',source_context_id=f.context,scenario_ids=[],characteristic_ids=[],issue_ids=['Q2-resolved'],answer_ids=['Answer1'],change_ids=['CH1'],view_id=view['id'],diagram_id=diagram['id'],validation_id=v['id'],status='preparing_review',disclosures=['Synthetic fixture, not actual review']))
review=record('review','LegacyReview',dict(bundle_id=bundle['id'],model_id='M2',source_context_id=f.context,reviewer='SYNTHETIC',decision='request_changes',supersedes_review_id=None,accepted_scope=make_scope('M2'),blocked_scope=allscope(m),workflow_choices=[],conditions=[],acknowledged_issue_ids=['Q2-resolved'],feedback='Synthetic request only'))
f.repo.finalize(op['command_id'],[view,diagram,v,bundle,review,run(op,f.context,f.config)])
open(sys.argv[3],'w').write(json.dumps({k:getattr(g,k) for k in ('session','context','config','snapshot')}))
"""
    if getattr(request,'param',None)=='stale_claim':
        code="""import sys,json
sys.path.insert(0,sys.argv[1])
from helpers import Foundation,issue,aset,run
from test_lifecycle import add_answer
f=Foundation(sys.argv[2]);m,a,answer=add_answer(f)
old=f.operation(kind='apply_answer',answer_id='Answer1',issue_key='Question2');f.repo.prepare(old)
op=f.operation();f.repo.prepare(op)
q=issue(m,'Pending',parent='Q2',status='answered_pending_application');q['body']['answer_ids']=['Answer1']
a2=aset(m,'AS2',a,issues=['Pending'])
f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
f.repo.finalize(old['command_id'],[run(old,f.context,f.config)])
open(sys.argv[3],'w').write(json.dumps({k:getattr(f,k) for k in ('session','context','config','snapshot')}))
"""
    subprocess.run([os.environ['DACN_P1_PYTHON'],'-B','-c',code,os.environ['DACN_BASELINE_HELPERS'],str(old),str(info)],check=True,cwd=tmp_path)
    src=old/'s02.sqlite3';before=src.read_bytes();repo=Repository(tmp_path/'mixed.sqlite3');repo.initialize()
    tables=[n for n,sql in DDL1.items() if sql.startswith('CREATE TABLE')]
    original={}
    with sqlite3.connect(src.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(repo.path) as target:
        target.execute('PRAGMA foreign_keys=ON');target.execute('BEGIN')
        for name in tables:
            rows=source.execute('SELECT * FROM '+name).fetchall();original[name]=rows
            for row in rows:
                values=(*row,L1) if name in ('records','operations') else row
                target.execute('INSERT INTO '+name+' VALUES ('+','.join('?' for _ in values)+')',values)
    repo.verify();assert src.read_bytes()==before
    from p2_helpers import synthetic_manifest,install_manifest_fixture
    install_manifest_fixture(repo,synthetic_manifest(repo,original));repo.verify()
    return repo,json.loads(info.read_text()),original

@pytest.mark.parametrize('method',['structural_check','human_review'])
def test_mixed_legacy_direct_to_e1_carry_reopen(mixed,method):
    from profile_fixtures import Graph
    repo,meta,original=mixed
    with repo._read() as c:records,blobs,commands,events,stages=repo._check(c)
    ids=set(records);g=Graph(records,{i:L1 for i in records},{i:meta['session'] for i in records},commands,{i:L1 for i in commands},events,stages,blobs,**meta)
    q=g.carry(method=method,new_model=True);op=list(g.commands.values())[-1];batch=[r for i,r in g.records.items() if i not in ids]
    if method=='human_review':repo=Repository(repo.path,reviews=g.reviews)
    repo.prepare(op);repo.finalize(op['command_id'],batch,head=(g.model_id,g.set_id))
    reopened=Repository(repo.path,reviews=g.reviews);reopened.verify()
    assert reopened.lookup_record(q['id'])==dict(profile_id=E1,record=q)
    assert reopened.lookup_record('Q2-resolved')['profile_id']==L1
    if method=='human_review':
        with pytest.raises(S02Error):Repository(repo.path).verify()
        bad=dict(g.reviews);from dacn_s02.resolution import HumanReviewEvidence
        bad[q['id']]=HumanReviewEvidence('wrong','0'*64,'applicable')
        with pytest.raises(S02Error):Repository(repo.path,reviews=bad).verify()
    with sqlite3.connect(repo.path) as c:
        for name,oldrows in original.items():
            if name in ('sessions','application_heads','active_reviews'):continue
            cols=[r[1] for r in c.execute('PRAGMA table_info('+name+')') if r[1]!='profile_id']
            now=c.execute('SELECT '+','.join(cols)+' FROM '+name).fetchall()
            assert all(row in now for row in oldrows),name
    # Legacy commands are immutable even if caller asks only for a log or retry.
    legacy=next(iter(commands))
    for work in (lambda:repo.append_event(legacy,'log',dict(message='forbidden')),lambda:repo.finalize(legacy,[])):
        with pytest.raises(S02Error,match='command_write_profile_e1'):work()
    evidence('mixed_fixture',migration_api=False,method=method,heads=reopened.heads(meta['session']),legacy_records=len(ids),new_profile=E1)

@pytest.mark.parametrize('field,value',[('profile_id',L1),('rules_id','unknown'),('contract_version','s02/0.1.0-draft.3'),('profile_id',None)])
def test_new_config_pins_are_checked(p2,field,value):
    from dacn_s02.codec_boundary import decode
    from dacn_s02.service import artifact
    f=p2;config=decode(f.repo.get_blob(f.config));config[field]=value;raw=encode(config)
    op=f.operation();f.repo.prepare(op);r=artifact('bad-config','config',raw,op['reserved_run_id'])
    with pytest.raises(S02Error,match='config_profile_binding'):
        f.repo.finalize(op['command_id'],[r,run(op,f.context,f.config)],blobs={r['id']:raw})
    assert f.repo.get_record(r['id']) is None

@pytest.mark.parametrize('field,value',[('store_id','ffffffff-ffff-4fff-8fff-ffffffffffff'),('state_dir','/wrong'),('receipt_version','s02/1')])
def test_receipt_identity_guard(p2,tmp_path,field,value):
    from dacn_s02.local_io import Settings,write_receipt,read_receipt
    state=tmp_path/'state';state.mkdir();cfg=tmp_path/'settings.toml';cfg.write_text('state_dir="state"')
    settings=Settings(cfg,state,{},(),5000);store_id=p2.repo.store_info()['metadata']['store_id']
    receipt=tmp_path/'receipt.json';write_receipt(settings,receipt,'command',store_id=store_id)
    original=receipt.read_bytes();v=json.loads(original);assert v['receipt_version']=='s02/2' and v['store_id']==store_id
    assert read_receipt(settings,receipt,store_id=store_id)==v
    v[field]=value;receipt.write_bytes(encode(v))
    with pytest.raises(S02Error):read_receipt(settings,receipt,store_id=store_id)
    with pytest.raises(S02Error):write_receipt(settings,receipt,'other',store_id=store_id)

@pytest.mark.parametrize('fault',['profile','activation_id','manifest_id','hash'])
def test_migration_metadata_fixture_binding(tmp_path,fault):
    # Metadata-only synthetic fixture, no DB1 copy, activation tool or receipt.
    from uuid import uuid4
    r=Repository(tmp_path/'metadata.sqlite3');r.initialize();info=r.store_info();m=info['metadata'];a=info['activation'];migration_id=str(uuid4())
    from p2_helpers import synthetic_manifest
    manifest=synthetic_manifest(r);manifest['migration_id']=migration_id
    raw=encode(manifest);basis=hashlib.sha256(raw).hexdigest()
    mutate(r.path,'store_metadata',"UPDATE store_metadata SET origin_kind='migration',migration_id=?,migration_manifest=?,manifest_sha256=?",(migration_id,raw,basis))
    mutate(r.path,'store_activation','UPDATE store_activation SET basis_sha256=?',(basis,));r.verify()
    if fault=='activation_id':mutate(r.path,'store_activation','UPDATE store_activation SET activation_id=?',(str(uuid4()),))
    else:
        if fault=='profile':manifest['write_profile_id']=L1
        if fault=='manifest_id':manifest['migration_id']=str(uuid4())
        raw=encode(manifest)
        mutate(r.path,'store_metadata','UPDATE store_metadata SET migration_manifest=?,manifest_sha256=?',(raw,hashlib.sha256(raw).hexdigest() if fault!='hash' else '0'*64))
    with pytest.raises(S02Error):Repository(r.path).verify()

def test_e1_repository_explicit_dispatch_not_legacy_alias(p2,monkeypatch):
    import dacn_s02.repository as repository
    import dacn_s02.validation as validation
    import dacn_s02.events as events
    monkeypatch.setattr(repository,'SCHEMA',{})
    monkeypatch.setattr(validation,'SCHEMA',{})
    monkeypatch.setattr(events,'SCHEMA',{})
    p2.initial(True);Repository(p2.repo.path).verify()
    assert p2.repo.lookup_record('Q2')['profile_id']==E1


def test_mixed_global_application_unique(mixed):
    repo,meta,original=mixed
    before=repo.path.read_bytes()
    op=operation(meta['session'],meta['context'],repo.heads(meta['session']),kind='apply_answer',answer_id='Answer1',issue_key='Question2')
    with pytest.raises(S02Error) as error:repo.prepare(op)
    assert error.value.error['code']=='APPLICATION_CONFLICT'
    assert repo.path.read_bytes()==before and repo.get_command(op['command_id']) is None

@pytest.mark.parametrize('fault',['missing','extra','format','plan','path','source_path','profile','rules','ddl','table','column','pk','count','root','equal_hash','bool_count','mutable_duplicate','mutable_head','mutable_sequence','mutable_claim','mutable_review'])
def test_full_manifest_rejects_inconsistent_inventory(mixed,fault):
    from dacn_s02.codec_boundary import decode
    from p2_helpers import install_manifest_fixture
    repo,meta,original=mixed;v=decode(repo.store_info()['metadata']['migration_manifest'])
    if fault=='missing':del v['tool']
    if fault=='extra':v['ignored']=True
    if fault=='format':v['format']='s02-migration-manifest/2'
    if fault=='plan':v['plan_version']='unknown'
    if fault=='path':v['destination_state_dir']='/different'
    if fault=='source_path':v['source_state_dir']=v['destination_state_dir']
    if fault=='profile':v['profiles'][L1]['schema_sha256']='0'*64
    if fault=='rules':v['profiles'][E1]['rules_id']='unknown'
    if fault=='ddl':v['source_ddl_sha256']='0'*64
    if fault=='table':del v['tables']['records']
    if fault=='column':v['tables']['records']['columns'].reverse()
    if fault=='pk':v['tables']['records']['primary_key']=['session_id']
    if fault=='count':v['tables']['records']['row_count']+=1
    if fault=='root':v['source_inventory_sha256']='0'*64
    if fault=='equal_hash':v['tables']['records']['copied_legacy_sha256']='0'*64
    if fault=='bool_count':v['tables']['records']['row_count']=True
    if fault=='mutable_duplicate':v['mutable_baseline']['sessions']*=2
    if fault=='mutable_head':v['mutable_baseline']['sessions'][0]['head_model_id']='missing'
    if fault=='mutable_sequence':v['mutable_baseline']['sessions'][0]['sequence']+=1
    if fault=='mutable_claim':v['mutable_baseline']['application_heads'][0]['active_command_id']='missing'
    if fault=='mutable_review':v['mutable_baseline']['active_reviews']=[dict(bundle_id='missing',review_id='missing')]
    install_manifest_fixture(repo,v);before=repo.path.read_bytes()
    for call in (repo.verify,lambda:repo.lookup_record('Q2-resolved')):
        with pytest.raises(S02Error):call()
        assert repo.path.read_bytes()==before

@pytest.mark.parametrize('table',['records','artifacts','record_links'])
def test_manifest_detects_l1_byte_drift_before_graph(mixed,table):
    repo,meta,original=mixed
    with sqlite3.connect(repo.path) as c:
        c.execute('DROP TRIGGER immutable_'+table+'_update')
        if table=='records':
            raw=c.execute("SELECT record_json FROM records WHERE id='Q2-resolved'").fetchone()[0]+' '
            c.execute("UPDATE records SET record_json=?,sha256=? WHERE id='Q2-resolved'",(raw,hashlib.sha256(raw.encode('ascii')).hexdigest()))
        elif table=='artifacts':
            rid=c.execute('SELECT record_id FROM artifacts LIMIT 1').fetchone()[0]
            c.execute('UPDATE artifacts SET bytes=zeroblob(byte_length) WHERE record_id=?',(rid,))
        else:c.execute("UPDATE record_links SET role='/different' WHERE owner_id='Q2-resolved' AND role=(SELECT min(role) FROM record_links WHERE owner_id='Q2-resolved')")
        c.execute(DDL['immutable_'+table+'_update'])
    before=repo.path.read_bytes()
    with pytest.raises(S02Error) as error:repo.verify()
    assert error.value.__cause__.error['details']['invariant']=='migration_legacy_inventory'
    assert repo.path.read_bytes()==before


def test_manifest_framing_vectors():
    from dacn_s02.migration_manifest import cell,table_digest
    from decimal import Decimal
    assert cell(None).hex()=='4e0000000000000000'
    assert cell(12).hex()=='4900000000000000023132'
    assert cell('é').hex()=='540000000000000002c3a9'
    assert cell(b'\x00\xff').hex()=='42000000000000000200ff'
    assert cell(Decimal(12))==cell(12)
    for value in (True,1.1,Decimal('1.1')):
        with pytest.raises(S02Error):cell(value)
    assert table_digest('staged_blobs',[('C','B','x','p','0'*64,1,b'\x00')])=='c4961892c9c4ad42dfbb013c1a500aa9ff8e49e0c016dccb8b84769a95cbc0e9'

@pytest.mark.parametrize('fault',['heads','sequence','claim','review'])
def test_manifest_rehashed_mutable_baseline_still_needs_lineage(mixed,fault):
    from p2_helpers import synthetic_manifest,install_manifest_fixture
    repo,meta,original=mixed;changed=deepcopy(original)
    if fault in ('heads','sequence'):
        row=list(changed['sessions'][0])
        if fault=='heads':row[2:4]=['M1','AS1']
        else:row[4]+=100
        changed['sessions'][0]=tuple(row)
    if fault=='claim':
        row=list(changed['application_heads'][0]);row[1]=changed['operations'][0][0];changed['application_heads'][0]=tuple(row)
    if fault=='review':changed['active_reviews']=[('MissingBundle','MissingReview')]
    manifest=synthetic_manifest(repo,changed);install_manifest_fixture(repo,manifest)
    with pytest.raises(S02Error) as error:repo.verify()
    assert error.value.__cause__.error['details']['invariant'] in ('migration_baseline_heads','migration_session_identity','migration_baseline_claims','migration_baseline_reviews')


def test_init_corrupt_existing_is_controlled_readonly(tmp_path,monkeypatch):
    path=tmp_path/'bad.sqlite3';path.write_bytes(b'not a sqlite store');before=path.read_bytes()
    real=sqlite3.connect;opens=[]
    def observed(database,*a,**k):opens.append(database);return real(database,*a,**k)
    monkeypatch.setattr(sqlite3,'connect',observed)
    with pytest.raises(S02Error):Repository(path).initialize()
    assert opens and all('mode=ro' in v for v in opens) and path.read_bytes()==before


def test_manifest_legacy_review_can_gain_e1_successor(mixed):
    repo,meta,original=mixed;old=repo.get_record('LegacyReview');new=deepcopy(old);new['id']='Review-E1'
    new['body'].update(supersedes_review_id=old['id'],feedback='Synthetic second request, not acceptance')
    op=operation(meta['session'],meta['context'],repo.heads(meta['session']));repo.prepare(op)
    repo.finalize(op['command_id'],[new,run(op,meta['context'],meta['config'])])
    Repository(repo.path).verify();assert repo.lookup_record(new['id'])['profile_id']==E1
    assert repo.get_record(old['id'])==old
    with sqlite3.connect(repo.path) as c:assert c.execute('SELECT review_id FROM active_reviews WHERE bundle_id=?',('LegacyBundle',)).fetchone()[0]==new['id']


@pytest.mark.parametrize('mixed',['stale_claim'],indirect=True)
def test_manifest_legacy_stale_claim_can_gain_e1_successor(mixed):
    repo,meta,original=mixed;old=original['application_heads'][0][1]
    assert repo.lookup_command(old)['profile_id']==L1
    assert repo.get_command(old)['run']['body']['status']=='stale'
    op=operation(meta['session'],meta['context'],repo.heads(meta['session']),kind='apply_answer',answer_id='Answer1',issue_key='Question2',parent=old)
    repo.prepare(op,claim_from=old);Repository(repo.path).verify()
    with sqlite3.connect(repo.path) as c:assert c.execute('SELECT active_command_id FROM application_heads WHERE answer_id=?',('Answer1',)).fetchone()[0]==op['command_id']
    assert repo.lookup_command(op['command_id'])['profile_id']==E1
    assert repo.get_command(old)['run']['body']['status']=='stale'
