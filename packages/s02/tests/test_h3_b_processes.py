"""S1-S6 installed B writer paths with real DB/event/publication readbacks."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
import json,os,subprocess,sys,shutil
import pytest
from dacn_s02.codec_boundary import encode,decode
from h3_b_runtime_fixtures import BCase,baseline,readback,human_baseline


@pytest.fixture(scope='module')
def sources(tmp_path_factory):
    return {k:baseline(tmp_path_factory.mktemp('b-safety-'+k),guard=k!='adopt') for k in ('adopt','guard')}


def evidence(case):
    out=Path(os.environ.get('S02_TEST_EVIDENCE_DIR',str(case.path/'evidence')))/case.path.name;out.mkdir(parents=True,exist_ok=True);return out


def spec(case,command,work,a,**changes):
    token=str(uuid4());path=evidence(case)/(token+'.work.json');data=dict(work)
    raw=path.with_suffix('.analysis.json');raw.write_bytes(data['analysis']);data['analysis']=str(raw);path.write_bytes(encode(data))
    value=dict(db=str(case.db),config=str(case.config),command=command,parent=case.parent,receipt=str(case.path/(command+'.receipt.json')),work=str(path),mode='resume',
        review_trust=asdict(case.trust),authority=str(a.path) if a else None,authority_trust=asdict(a.trust) if a else None)
    value.update(changes);return value


def launch(case,value):
    out=evidence(case);token=str(uuid4());path=out/(token+'.input.json');path.write_text(json.dumps(value))
    argv=[sys.executable,'-B',str(Path(__file__).with_name('h3_b_worker.py')),str(path)];env=os.environ.copy();env.pop('PYTHONPATH',None)
    p=subprocess.Popen(argv,cwd=case.path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def finish():
        stdout,stderr=p.communicate(timeout=45);(out/(token+'.stdout.log')).write_bytes(stdout);(out/(token+'.stderr.log')).write_bytes(stderr)
        (out/(token+'.command.json')).write_text(json.dumps(dict(pid=p.pid,argv=argv,cwd=str(case.path),exit_code=p.returncode,
            test_case=os.environ.get('PYTEST_CURRENT_TEST'),backend=os.environ.get('S02_TEST_CODEC_BACKEND','c'))))
        if p.returncode!=71:
            row=next((x.removeprefix('H3_ENCODERS ') for x in stdout.decode().splitlines() if x.startswith('H3_ENCODERS ')),None);assert row is not None,(stdout,stderr)
            row=json.loads(row);backend=os.environ.get('S02_TEST_CODEC_BACKEND','c');assert row['backend']==backend and row['calls'][backend]>0 and row['calls']['c' if backend=='python' else 'python']==0
        return p.returncode,stdout.decode(),stderr.decode()
    return finish


def result(value):return decode(next(x.removeprefix('H3_RESULT ') for x in value[1].splitlines() if x.startswith('H3_RESULT ')).encode())


def save_snapshot(case,label):
    root=evidence(case)/label;root.mkdir(exist_ok=False)
    for p in case.db.parent.iterdir():
        if p.is_file():shutil.copy2(p,root/p.name)
    return root


def pending(case,command):
    from dacn_s02.h3_checkpoint_store import HistoryStore
    from dacn_s02.h3_review_io import LocalSyntheticHistoricalReviews
    from dacn_s02.h3_limits import Budget
    b=Budget();registry=LocalSyntheticHistoricalReviews.load(case.trust,b);store=HistoryStore(registry.open_repository(case.db),registry,b);v=store.load(command)
    if v is None:return None
    found=store.checked_plan(v)
    return dict(command=command,reserved_run_id=v['config']['reserved_run_id'],started_at=v['config']['started_at'],config_bytes=v['primary']['bytes'],raw_bytes=v['raw']['bytes'],
        config_sha256=v['primary']['sha256'],raw_sha256=v['raw']['sha256'],plan_bytes=found[1]['bytes'] if found else None,plan=found[0] if found else None)


def exact(case,command,previous=None,*,application_count=0):
    view,plan,identity=readback(case,command);cfg=view['config'];cmd=view['command'];published=cmd['run']['body']['status'] in ('completed','blocked')
    assert cfg['historical_reviews_pin']==plan['bindings']['historical_reviews_pin']
    assert len(cmd['staged_blobs'])==3 and len(cmd['events'])==3
    assert len(identity['applications'])==application_count
    assert identity['applications']==case.applications_before
    if previous:
        assert cfg['reserved_run_id']==previous['reserved_run_id'] and cfg['started_at']==previous['started_at']
        assert view['primary']['bytes']==previous['config_bytes'] and view['raw']['bytes']==previous['raw_bytes']
        if previous['plan_bytes'] is not None:assert encode(plan)==previous['plan_bytes']
    for record in plan['batch']['records']:
        if published:assert view['state']['records'][record['id']]==record
        elif record['type'] in ('analysis_set','issue'):assert record['id'] not in view['state']['records']
        elif record['type']=='artifact':assert view['state']['records'][record['id']]==record
        else:
            expected=deepcopy(record);expected['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=cmd['run']['body']['errors'])
            assert cmd['run']==expected
    for ref in plan['promotions']:
        stage=view['state']['stages'][ref['stage_ref']['command_id'],ref['stage_ref']['blob_id']]
        assert view['state']['blobs'][ref['artifact_id']]==stage['bytes']
    packed={k:v for k,v in identity.items() if k!='plan'};(evidence(case)/(command+'.readback.json')).write_bytes(encode(packed));return view,plan


@pytest.mark.parametrize('phase',['prepare','seal','finalize'])
@pytest.mark.parametrize('point,action',[('before_commit','rollback'),('before_commit','kill'),('after_commit','kill'),('after_commit','lost_ack'),('after_commit','unknown')])
def test_S3_T0_seal_T3_crash_rollback_lost_ack_unknown(tmp_path,sources,phase,point,action):
    c=BCase(tmp_path,sources['adopt']);work,a=c.work();command=str(uuid4());saved=None
    if phase!='prepare':c.prepare(command,work,a);saved=pending(c,command)
    value=spec(c,command,work,a,mode='prepare' if phase=='prepare' else 'resume',phase=phase,repo_point=point,action=action)
    code,out,err=launch(c,value)();assert code==(71 if action=='kill' else 3 if action in ('rollback','unknown') else 0 if phase=='prepare' else 2),(code,out,err)
    save_snapshot(c,'fault-before-recovery')
    if action=='unknown':
        assert 'Commit outcome unknown' in out;Path(str(c.db)+'.unavailable').rename(c.db)
    # A fresh process performs checked engine recovery before this process reads
    # any pending state, including a real hot rollback journal after SIG-exit.
    report=launch(c,spec(c,command,work,None,mode='report'))()
    # A seal lost ACK is reconciled in the original worker, which then executes
    # T3. Kill/outcome-unknown stop that worker before T3 instead.
    finished=(phase=='finalize' and point=='after_commit') or (phase=='seal' and action=='lost_ack')
    absent=phase=='prepare' and point=='before_commit'
    assert report[0]==(5 if absent else 2 if finished else 0),report
    expected_phase='not_prepared' if absent else 'finalized' if finished else 'sealed' if phase=='finalize' or phase=='seal' and point=='after_commit' else 'prepared'
    assert result(report)['result']['phase']==expected_phase
    if phase=='prepare' and point=='before_commit':
        assert c.path.joinpath(command+'.receipt.json').exists()
        probe=launch(c,spec(c,command,work,None))();assert probe[0]==5,probe
        c.prepare(command,work,a)
    before=pending(c,command)
    if saved:
        assert before['config_bytes']==saved['config_bytes'] and before['reserved_run_id']==saved['reserved_run_id']
    if phase=='seal' and point=='before_commit':assert before['plan'] is None
    if phase=='seal' and point=='after_commit' or phase=='finalize':assert before['plan'] is not None
    reopened=launch(c,spec(c,command,work,a))();assert reopened[0]==2,reopened
    assert result(reopened)['status']=='blocked'
    exact(c,command,before)


@pytest.mark.parametrize('path',['guard_pass','guard_held'])
@pytest.mark.parametrize('phase,point,action',[('seal','before_commit','kill'),('seal','after_commit','kill'),('finalize','before_commit','kill'),('finalize','after_commit','kill'),('finalize','after_commit','lost_ack')])
def test_S5_revalidate_effects_paths_crash_reopen(tmp_path,sources,path,phase,point,action):
    c=BCase(tmp_path,sources['guard']);c.execute(*c.work());old_model=c.repo().get_record(c.pair[0])
    def change(v):
        if path=='guard_held':
            for x in v['independence']:x['verdict']='unknown'
    work,a=c.work(mode='revalidate',step=1,change=change);command=str(uuid4());c.prepare(command,work,a);saved=pending(c,command)
    attempted=launch(c,spec(c,command,work,a,phase=phase,repo_point=point,action=action))();assert attempted[0]==(71 if action=='kill' else 2),attempted
    save_snapshot(c,'revalidate-fault')
    report=launch(c,spec(c,command,work,None,mode='report'))()
    assert report[0]==(2 if phase=='finalize' and point=='after_commit' else 0),report
    before=pending(c,command);assert before['config_bytes']==saved['config_bytes']
    reopened=launch(c,spec(c,command,work,a))();assert reopened[0]==2,reopened
    view,plan=exact(c,command,before);assert view['base'].context.model()==old_model
    changes=[r for r in plan['batch']['records'] if r['type']=='issue'];assert len(changes)==1
    assert changes[0]['body']['status']==('resolved' if path=='guard_pass' else 'open')
    assert changes[0]['body']['supersedes_id'] in view['base'].analysis_set['body']['issue_ids']


@pytest.mark.parametrize('different',[False,True])
def test_S1_two_OS_preparers_same_command_intent(tmp_path,sources,different):
    c=BCase(tmp_path,sources['adopt']);command=str(uuid4());work,a=c.work()
    def change(v):
        if different:v['inspections'][0]['reason']='Different explicit raw intent'
    other,a2=c.work(change=change)
    common=dict(mode='prepare',barrier_point='before_prepare',barrier=str(tmp_path/'barrier'))
    first=launch(c,spec(c,command,work,a,**common));second=launch(c,spec(c,command,other,a2,**common));one=first();two=second()
    assert sorted([one[0],two[0]])==([0,2] if different else [0,0]),(one,two)
    cmd=c.repo().get_command(command);assert len(cmd['events'])==1 and len(cmd['staged_blobs'])==2
    selected=a if pending(c,command)['raw_bytes']==work['analysis'] else a2
    saved=pending(c,command);assert c.service(selected).resume(command)['status']=='blocked';exact(c,command,saved)


def test_S1_two_preparers_different_registry_pin_cannot_replace_winning_T0(tmp_path,sources):
    from dataclasses import replace
    c=BCase(tmp_path,sources['adopt']);command=str(uuid4());work,a=c.work();original=(c.trust,c.registry_path,c.registry_raw)
    common=dict(mode='prepare',barrier_point='before_prepare',barrier=str(tmp_path/'barrier'))
    one=spec(c,command,work,a,**common)
    value=decode(c.registry_raw);value['registry_id']='AlternateReviewVersion';raw=encode(value);path=c.path/'alternate-reviews.json';path.write_bytes(raw)
    c.trust=replace(c.trust,path=str(path),expected_sha256=sha256(raw).hexdigest(),expected_registry_id=value['registry_id']);c.registry_path=path;c.registry_raw=raw
    alternate=(c.trust,path,raw);work2,a2=c.work();two=spec(c,command,work2,a2,**common)
    c.trust,c.registry_path,c.registry_raw=original
    first=launch(c,one);second=launch(c,two);r1=first();r2=second();assert sorted([r1[0],r2[0]])==[0,2],(r1,r2)
    if r2[0]==0:c.trust,c.registry_path,c.registry_raw=alternate;chosen=a2
    else:chosen=a
    saved=pending(c,command);assert saved['plan'] is None
    assert c.service(chosen).resume(command)['status']=='blocked'
    exact(c,command,saved)


@pytest.mark.parametrize('point',['before_seal','before_finalize'])
def test_S1_two_OS_resumers_concurrent_seal_or_finalize(tmp_path,sources,point):
    c=BCase(tmp_path,sources['adopt']);work,a=c.work();command=str(uuid4());c.prepare(command,work,a);saved=pending(c,command)
    value=spec(c,command,work,a,barrier_point=point,barrier=str(tmp_path/'barrier'))
    first=launch(c,value);second=launch(c,value);one=first();two=second();assert one[0]==two[0]==2,(one,two)
    assert result(one)==result(two);exact(c,command,saved)


def test_S2_two_AS_only_publishers_paired_CAS_real_DB(tmp_path,sources):
    c=BCase(tmp_path,sources['adopt']);commands=[str(uuid4()),str(uuid4())];prepared=[]
    for cmd in commands:
        work,a=c.work();c.prepare(cmd,work,a);prepared.append((cmd,work,a,pending(c,cmd)))
    common=dict(barrier_point='before_finalize',barrier=str(tmp_path/'barrier'))
    first=launch(c,spec(c,*prepared[0][:3],**common));second=launch(c,spec(c,*prepared[1][:3],**common));a=first();b=second();assert a[0]==b[0]==2,(a,b)
    statuses=[c.repo().get_command(cmd)['run']['body']['status'] for cmd in commands];assert sorted(statuses)==['blocked','stale']
    for cmd,_,_,saved in prepared:exact(c,cmd,saved)


def test_S2_valid_Model_AS_opponent_makes_sealed_B_loser_stale(tmp_path,sources):
    c=BCase(tmp_path,sources['adopt']);work,a=c.work();command=str(uuid4());c.prepare(command,work,a)
    def stop(point):
        if point=='after_seal':raise RuntimeError('Hold sealed B while valid H2 Model advances')
    with pytest.raises(RuntimeError):c.service(a,_hook=stop).resume(command)
    saved=pending(c,command);old=c.pair[:]
    opponent=c.h2.advance(3);assert opponent['result']['result_pair'][0]!=old[0] and opponent['result']['result_pair'][1]!=old[1]
    resumed=launch(c,spec(c,command,work,a))();assert resumed[0]==2 and result(resumed)['status']=='stale',resumed
    view,plan=exact(c,command,saved);assert view['current_head']==opponent['result']['result_pair']
    assert view['command']['run']['body']['result_model_id'] is None and view['command']['run']['body']['result_analysis_set_id'] is None


@pytest.fixture(scope='module')
def human_source(tmp_path_factory):return human_baseline(tmp_path_factory.mktemp('b-HR-P-process-source'))


@pytest.mark.parametrize('sealed',[False,True])
@pytest.mark.parametrize('failure',['missing','tampered','ancestor_missing','other_session_missing'])
def test_S4_HR_P_original_registry_process_restart_restore(tmp_path,human_source,sealed,failure):
    c=BCase(tmp_path,human_source);work,a=c.work();command=str(uuid4())
    first=launch(c,spec(c,command,work,a,mode='prepare',service_kill='after_prepare'))();assert first[0]==71,first
    saved=pending(c,command);assert saved['plan'] is None and saved['reserved_run_id']
    if sealed:
        stop=launch(c,spec(c,command,work,a,service_kill='after_seal'))();assert stop[0]==71,stop
        saved=pending(c,command);assert saved['plan_bytes'] is not None
    checksum=sha256(c.db.read_bytes()).hexdigest()
    if failure=='missing':c.registry_path.unlink()
    elif failure=='tampered':c.registry_path.write_bytes(c.registry_raw+b' ')
    else:
        control=decode(c.registry_raw)
        control['reviews']=[r for r in control['reviews'] if not (r['issue_id'].startswith('Carry-') if failure=='ancestor_missing' else r['issue_id'].startswith('Other.'))]
        control['required_issue_ids']=[r['issue_id'] for r in control['reviews']];c.registry_path.write_bytes(encode(control))
    value=spec(c,command,work,a)
    if failure in ('ancestor_missing','other_session_missing'):value['review_trust']['expected_sha256']=sha256(c.registry_path.read_bytes()).hexdigest()
    denied=launch(c,value)();assert denied[0]==3,denied
    assert sha256(c.db.read_bytes()).hexdigest()==checksum
    c.registry_path.write_bytes(c.registry_raw)
    recovered=launch(c,spec(c,command,work,a))();assert recovered[0]==2,recovered
    view,plan=exact(c,command,saved,application_count=2)
    assert len(plan['bindings']['historical_reviews_pin'])==6
    # Providerless finalized report: old authority and external analysis/work
    # files do not exist. Original historical registry is still mandatory.
    a.path.unlink();value=spec(c,command,work,None,mode='report');workfile=Path(value['work']);analysis=Path(json.loads(workfile.read_text())['analysis']);analysis.unlink();workfile.unlink()
    checksum=sha256(c.db.read_bytes()).hexdigest();reported=launch(c,value)();assert reported[0]==2 and result(reported)==result(recovered),reported
    assert sha256(c.db.read_bytes()).hexdigest()==checksum
    c.registry_path.unlink();assert launch(c,value)()[0]==3
