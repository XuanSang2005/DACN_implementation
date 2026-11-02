"""S1-S6 on real Model+A2 C commands, independent OS processes, no CLI."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
import pytest
from dacn_s02.codec_boundary import encode,decode
from h3_c_runtime_fixtures import CCase,baseline
from h3_c_process_fixtures import spec,launch,result,pending,exact,save_snapshot


@pytest.fixture(scope='module')
def sources(tmp_path_factory):
    class Sources(dict):
        def __missing__(self,branch):
            with pytest.MonkeyPatch.context() as patch:
                source=baseline(tmp_path_factory.mktemp('C-'+branch),patch,branch)
            c=CCase(tmp_path_factory.mktemp('C-ready-'+branch),source);value=c.descriptor();self[branch]=value;return value
    return Sources()


@pytest.mark.parametrize('phase',['prepare','seal','finalize'])
@pytest.mark.parametrize('point,action',[('before_commit','rollback'),('before_commit','kill'),('after_commit','kill'),('after_commit','lost_ack'),('after_commit','unknown')])
def test_S3_C_T0_seal_T3_crash_rollback_lost_ack_unknown(tmp_path,sources,phase,point,action):
    c=CCase(tmp_path,sources['direct']);work,a=c.work();command=str(uuid4());saved=None
    if phase!='prepare':c.prepare(command,work,a);saved=pending(c,command)
    attempted=launch(c,spec(c,command,work,a,mode='prepare' if phase=='prepare' else 'resume',phase=phase,repo_point=point,action=action))()
    assert attempted[0]==(71 if action=='kill' else 3 if action in ('rollback','unknown') else 0 if phase=='prepare' else 2),attempted
    save_snapshot(c,'fault-before-recovery')
    if action=='unknown':assert 'Commit outcome unknown' in attempted[1];Path(str(c.db)+'.unavailable').rename(c.db)
    report=launch(c,spec(c,command,work,None,mode='report'))();finished=(phase=='finalize' and point=='after_commit') or (phase=='seal' and action=='lost_ack');absent=phase=='prepare' and point=='before_commit'
    assert report[0]==(5 if absent else 2 if finished else 0),report
    assert result(report)['result']['phase']==('not_prepared' if absent else 'finalized' if finished else 'sealed' if phase=='finalize' or phase=='seal' and point=='after_commit' else 'prepared')
    if absent:
        assert (c.path/(command+'.receipt.json')).exists();assert launch(c,spec(c,command,work,None))()[0]==5;c.prepare(command,work,a)
    before=pending(c,command)
    if saved:assert before['config_bytes']==saved['config_bytes'] and before['reserved_run_id']==saved['reserved_run_id']
    if phase=='seal' and point=='before_commit':assert before['plan'] is None
    if phase=='seal' and point=='after_commit' or phase=='finalize':assert before['plan'] is not None
    reopened=launch(c,spec(c,command,work,a))();assert reopened[0]==2 and result(reopened)['status']=='blocked',reopened
    v,p=exact(c,command,before);assert p['candidate_outcome']=='valid' and p['batch']['head'][0]!=v['base'].pair[0]


@pytest.mark.parametrize('branch',['direct','pending','replacement','replacement_tasks','obsolete','rejection'])
@pytest.mark.parametrize('phase,point,action',[('seal','before_commit','kill'),('seal','after_commit','kill'),('finalize','before_commit','kill'),('finalize','after_commit','kill'),('finalize','after_commit','lost_ack')])
def test_S5_C_each_effects_class_crash_reopen(tmp_path,sources,branch,phase,point,action):
    c=CCase(tmp_path,sources['direct' if branch=='rejection' else branch])
    def bad(raw,analysis):raw['unexpected']=True
    work,a=c.work(change=bad if branch=='rejection' else None);command=str(uuid4());c.prepare(command,work,a);saved=pending(c,command)
    attempted=launch(c,spec(c,command,work,a,phase=phase,repo_point=point,action=action))();assert attempted[0]==(71 if action=='kill' else 2),attempted
    save_snapshot(c,'effects-fault');report=launch(c,spec(c,command,work,None,mode='report'))();assert report[0]==(2 if phase=='finalize' and point=='after_commit' else 0),report
    before=pending(c,command);assert before['config_bytes']==saved['config_bytes'];reopened=launch(c,spec(c,command,work,a))();assert reopened[0]==2,reopened
    v,p=exact(c,command,before);assert p['candidate_outcome']==('rejected' if branch=='rejection' else 'guard_only' if branch=='obsolete' else 'valid')
    if branch in ('direct','pending','replacement','replacement_tasks'):
        assert p['batch']['head'][0]!=v['base'].pair[0];q=next(r for r in p['batch']['records'] if r['type']=='issue' and r['body']['issue_key']=='Question2')['body']
        if branch=='direct':assert q['resolution_carry']['assessment']=='applicable'
        if branch=='pending':assert q['resolution_carry']['assessment']=='undetermined' and q['status']=='resolution_pending_revalidation'
        if branch in ('replacement','replacement_tasks'):assert q['resolution_replacement']['assessment']==('complete' if branch=='replacement' else 'incomplete')
    elif branch=='obsolete':assert p['batch']['head'][0]==v['base'].pair[0] and p['admission']['guards']
    else:assert p['batch']['head'] is None


@pytest.mark.parametrize('branch',['direct','replacement'])
@pytest.mark.parametrize('different',[False,True])
def test_S1_C_two_OS_preparers_same_command(tmp_path,sources,branch,different):
    c=CCase(tmp_path,sources[branch]);cmd=str(uuid4());work,a=c.work()
    def change(raw,analysis):
        if different:raw['proposals']['actions'][0]['name']='Different raw intent'
    other,a2=c.work(change=change);common=dict(mode='prepare',barrier_point='before_prepare',barrier=str(tmp_path/'barrier'))
    one=launch(c,spec(c,cmd,work,a,**common));two=launch(c,spec(c,cmd,other,a2,**common));r1=one();r2=two();assert sorted([r1[0],r2[0]])==([0,2] if different else [0,0]),(r1,r2)
    operation=c.repo().get_command(cmd);assert len(operation['events'])==1 and len(operation['staged_blobs'])==3
    saved=pending(c,cmd);chosen=a if saved['raw_bytes']['candidate']==work['candidate'] else a2
    assert c.service(chosen).resume(cmd)['status']=='blocked';exact(c,cmd,saved)


@pytest.mark.parametrize('branch',['direct','replacement'])
@pytest.mark.parametrize('point',['before_seal','before_finalize'])
def test_S1_C_two_OS_resumers_build_seal_finalize(tmp_path,sources,branch,point):
    c=CCase(tmp_path,sources[branch]);work,a=c.work();cmd=str(uuid4());c.prepare(cmd,work,a);saved=pending(c,cmd);value=spec(c,cmd,work,a,barrier_point=point,barrier=str(tmp_path/'barrier'))
    one=launch(c,value);two=launch(c,value);r1=one();r2=two();assert r1[0]==r2[0]==2 and result(r1)==result(r2),(r1,r2);exact(c,cmd,saved)


def test_S1_C_two_preparers_cannot_replace_registry_pin(tmp_path,sources):
    c=CCase(tmp_path,sources['replacement']);cmd=str(uuid4());work,a=c.work();one=spec(c,cmd,work,a,mode='prepare')
    value=decode(c.registry_raw);value['registry_id']='AlternateCVersion';raw=encode(value);path=c.path/'alternate.json';path.write_bytes(raw)
    two=deepcopy(one);two['review_trust'].update(path=str(path),expected_sha256=sha256(raw).hexdigest(),expected_registry_id=value['registry_id'])
    # A C parent already pins the original registry. Alternate R must fail
    # before reaching T0; there is no legal alternate parent/authority grant.
    first=launch(c,one);second=launch(c,two);r1=first();r2=second();assert r1[0]==0 and r2[0]==2,(r1,r2)
    saved=pending(c,cmd);assert c.service(a).resume(cmd)['status']=='blocked';exact(c,cmd,saved)


def test_S2_C_two_Model_A2_publishers_paired_CAS(tmp_path,sources):
    c=CCase(tmp_path,sources['replacement']);prepared=[]
    for _ in range(2):
        cmd=str(uuid4());work,a=c.work();c.prepare(cmd,work,a);prepared.append((cmd,work,a,pending(c,cmd)))
    common=dict(barrier_point='before_finalize',barrier=str(tmp_path/'barrier'));first=launch(c,spec(c,*prepared[0][:3],**common));second=launch(c,spec(c,*prepared[1][:3],**common));r1=first();r2=second();assert r1[0]==r2[0]==2,(r1,r2)
    assert sorted(c.repo().get_command(cmd)['run']['body']['status'] for cmd,_,_,_ in prepared)==['blocked','stale']
    for cmd,_,_,saved in prepared:exact(c,cmd,saved)


@pytest.mark.parametrize('opponent',['AS_only','Model_AS'])
def test_S2_C_sealed_loser_both_head_change_opponents(tmp_path,sources,opponent):
    c=CCase(tmp_path,sources['direct']);work,a=c.work();cmd=str(uuid4());c.prepare(cmd,work,a)
    def stop(point):
        if point=='after_seal':raise RuntimeError('Hold original C seal')
    with pytest.raises(RuntimeError,match='Hold original'):c.service(a,_hook=stop).resume(cmd)
    saved=pending(c,cmd);old=c.pair[:];r=c.execute(*c.work(mode='revalidate' if opponent=='AS_only' else 'step',step=1 if opponent=='AS_only' else 2));assert r['status']=='blocked';assert c.pair[1]!=old[1] and (c.pair[0]==old[0])==(opponent=='AS_only')
    resumed=launch(c,spec(c,cmd,work,a))();assert resumed[0]==2 and result(resumed)['status']=='stale',resumed
    v,p=exact(c,cmd,saved);assert v['command']['run']['body']['errors'][0]['code']==('ANALYSIS_CONFLICT' if opponent=='AS_only' else 'MODEL_CONFLICT')


@pytest.fixture(scope='module')
def human_source(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:source=baseline(tmp_path_factory.mktemp('C-HR-P'),patch,'replacement',other=True)
    c=CCase(tmp_path_factory.mktemp('C-HR-P-ready'),source);return c.descriptor()


@pytest.mark.parametrize('sealed',[False,True])
@pytest.mark.parametrize('failure',['missing','tampered','ancestor_missing','other_session_missing'])
def test_S4_C_original_registry_restart_restore_all_store_R(tmp_path,human_source,sealed,failure):
    c=CCase(tmp_path,human_source);work,a=c.work();cmd=str(uuid4());first=launch(c,spec(c,cmd,work,a,mode='prepare',service_kill='after_prepare'))();assert first[0]==71,first
    saved=pending(c,cmd);assert saved['plan'] is None
    if sealed:
        stop=launch(c,spec(c,cmd,work,a,service_kill='after_seal'))();assert stop[0]==71,stop
        saved=pending(c,cmd);assert saved['plan_bytes'] is not None
    checksum=sha256(c.db.read_bytes()).hexdigest()
    if failure=='missing':c.registry_path.unlink()
    elif failure=='tampered':c.registry_path.write_bytes(c.registry_raw+b' ')
    else:
        control=decode(c.registry_raw);control['reviews']=[r for r in control['reviews'] if not (r['issue_id'].startswith('Carry-') if failure=='ancestor_missing' else r['issue_id'].startswith('Other.'))];control['required_issue_ids']=[r['issue_id'] for r in control['reviews']];c.registry_path.write_bytes(encode(control))
    value=spec(c,cmd,work,a)
    if failure in ('ancestor_missing','other_session_missing'):value['review_trust']['expected_sha256']=sha256(c.registry_path.read_bytes()).hexdigest()
    denied=launch(c,value)();assert denied[0]==3,denied
    assert sha256(c.db.read_bytes()).hexdigest()==checksum
    c.registry_path.write_bytes(c.registry_raw);recovered=launch(c,spec(c,cmd,work,a))();assert recovered[0]==2,recovered
    v,p=exact(c,cmd,saved);assert len(c.applications_before)==2 and len(p['bindings']['historical_reviews_pin'])==6
    # No authority or external raw/work files needed after finalize. Historical
    # review pin still required, including human ancestors in the other session.
    a.path.unlink();value=spec(c,cmd,work,None,mode='report');workfile=Path(value['work']);inputs=decode(workfile.read_bytes())
    for lane in ('candidate','analysis'):Path(inputs[lane]).unlink()
    workfile.unlink();checksum=sha256(c.db.read_bytes()).hexdigest();reported=launch(c,value)();assert reported[0]==2 and result(reported)==result(recovered),reported
    assert sha256(c.db.read_bytes()).hexdigest()==checksum;c.registry_path.unlink();assert launch(c,value)()[0]==3


@pytest.mark.parametrize('phase,point,action',[('seal','before_commit','kill'),('seal','after_commit','kill'),('finalize','before_commit','kill'),('finalize','after_commit','kill'),('finalize','after_commit','lost_ack')])
def test_S5_C_completed_Model_A2_effects_crash_reopen(tmp_path,sources,phase,point,action):
    c=CCase(tmp_path,sources['actor_only']);work,a=c.work();cmd=str(uuid4());c.prepare(cmd,work,a);saved=pending(c,cmd)
    attempted=launch(c,spec(c,cmd,work,a,phase=phase,repo_point=point,action=action))();assert attempted[0]==(71 if action=='kill' else 0),attempted
    save_snapshot(c,'completed-effects-fault');reported=launch(c,spec(c,cmd,work,None,mode='report'))();assert reported[0]==0,reported
    assert result(reported)['result']['phase']==('finalized' if phase=='finalize' and point=='after_commit' else 'prepared' if phase=='seal' and point=='before_commit' else 'sealed')
    before=pending(c,cmd);assert before['config_bytes']==saved['config_bytes'];resumed=launch(c,spec(c,cmd,work,a))();assert resumed[0]==0 and result(resumed)['status']=='completed',resumed
    v,p=exact(c,cmd,before);assert p['candidate_outcome']=='valid' and p['batch']['head'][0]!=v['base'].pair[0]
    q=next(r for r in p['batch']['records'] if r['type']=='issue' and r['body']['issue_key']=='Question2');assert q['body']['resolution_carry']['assessment']=='applicable'
