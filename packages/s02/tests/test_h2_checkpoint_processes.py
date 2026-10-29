"""H2 writer races and durable crash boundaries with separate OS processes."""
import json,os,subprocess,sys
from pathlib import Path
from uuid import uuid4
import pytest
from h2_checkpoint_fixtures import ScopedCase
from dacn_s02.h2_service import H2Service
from dacn_s02.h2_store import ScopeStore
from dacn_s02.h2_limits import Budget
from dacn_s02.repository import Repository
from dacn_s02.codec_boundary import encode,decode


def spec(case,command,work,authority,**changes):
    token=str(uuid4());path=case.path/(token+'.work.json');saved=dict(work)
    for lane in ('candidate','analysis'):
        if saved[lane] is not None:
            dest=case.path/(token+'.'+lane);dest.write_bytes(saved[lane]);saved[lane]=str(dest)
    path.write_bytes(encode(saved))
    value=dict(db=str(case.repo.path),command=command,parent=case.parent,store_id=case.store_id,work=str(path),mode='resume',authority=str(authority.path) if authority else None,authority_sha256=authority.expected_sha256 if authority else None)
    value.update(changes);return value


def launch(case,value):
    evidence=Path(os.environ.get('S02_TEST_EVIDENCE_DIR',str(case.path/'evidence')));evidence.mkdir(parents=True,exist_ok=True)
    token=str(uuid4());path=evidence/(token+'.input.json');path.write_text(json.dumps(value))
    argv=[sys.executable,'-B',str(Path(__file__).with_name('h2_worker.py')),str(path)];env=os.environ.copy();env.pop('PYTHONPATH',None)
    p=subprocess.Popen(argv,cwd=case.path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def finish():
        out,err=p.communicate(timeout=45)
        (evidence/(token+'.stdout.log')).write_bytes(out);(evidence/(token+'.stderr.log')).write_bytes(err)
        (evidence/(token+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(case.path),exit_code=p.returncode)))
        if p.returncode!=71:
            line=next((x.removeprefix('H2_ENCODERS ') for x in out.decode().splitlines() if x.startswith('H2_ENCODERS ')),None)
            assert line is not None,(out,err)
            counts=json.loads(line);backend=os.environ.get('S02_TEST_CODEC_BACKEND','c')
            assert counts['backend']==backend and counts['calls'][backend]>0 and counts['calls']['c' if backend=='python' else 'python']==0
        return p.returncode,out.decode(),err.decode()
    return finish


def final(case,command):
    repo=Repository(case.repo.path);repo.verify();store=ScopeStore(repo,Budget());view=store.load(command);cmd=view['command']
    assert cmd['state']=='finalized'
    plans=store.plans(cmd,view['state']);assert len(plans)==1
    plan,stage=plans[0];assert sum(e['kind']=='finalized' for e in cmd['events'])==1
    assert cmd['run']['id']==cmd['operation']['reserved_run_id']
    print('H2_SAFETY '+encode(dict(command_id=command,run_id=cmd['run']['id'],plan_sha256=stage['sha256'],head=view['current_head'],raw_hashes={k:s['sha256'] if s else None for k,s in view['raw'].items()})).decode())
    return view,plan


@pytest.mark.parametrize('phase',['prepare','seal','finalize'])
@pytest.mark.parametrize('fault',[('before_commit','kill'),('after_commit','kill'),('after_commit','lost_ack'),('after_commit','unknown')])
def test_h2_process_crash_lost_ack(tmp_path,phase,fault):
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);command=str(uuid4());service=H2Service(case.repo,authority=authority)
    if phase!='prepare':service.prepare(command,case.parent,store_id=case.store_id,**work)
    point,action=fault
    result=launch(case,spec(case,command,work,authority,mode='prepare' if phase=='prepare' else 'resume',phase=phase,repo_point=point,action=action))()
    assert result[0]==(71 if action=='kill' else 3 if action=='unknown' else 0 if phase=='prepare' else 2),result
    if action=='unknown':
        assert 'Commit outcome unknown' in result[1]
        Path(str(case.repo.path)+'.unavailable').rename(case.repo.path)
    if phase=='prepare' and point=='before_commit':
        assert H2Service(case.repo).resume(command)['status']=='not_prepared'
        service.prepare(command,case.parent,store_id=case.store_id,**work)
    resumed=service.resume(command,store_id=case.store_id);assert resumed['status']=='blocked',resumed
    assert H2Service(Repository(case.repo.path)).resume(command)==resumed
    final(case,command)


@pytest.mark.parametrize('point',['before_seal','before_finalize'])
def test_h2_two_resumers(tmp_path,point):
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);cmd=str(uuid4());service=H2Service(case.repo,authority=authority)
    service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    value=spec(case,cmd,work,authority,barrier_point=point,barrier=str(tmp_path/'barrier'))
    first=launch(case,value);second=launch(case,value);a=first();b=second()
    assert a[0]==b[0]==2,(a,b)
    def result(v):return decode(next(s.removeprefix('H2_RESULT ') for s in v[1].splitlines() if s.startswith('H2_RESULT ')).encode())
    assert result(a)==result(b)
    final(case,cmd)


@pytest.mark.parametrize('different',[False,True])
def test_h2_two_preparers(tmp_path,different):
    case=ScopedCase(tmp_path);case.bootstrap();cmd=str(uuid4());work,authority=case.work(1)
    other,other_authority=case.work(1,change=(lambda c,a:a['inspections'][0].update(reason='Different explicit intent')) if different else None)
    common=dict(mode='prepare',barrier_point='before_prepare',barrier=str(tmp_path/'barrier'))
    first=launch(case,spec(case,cmd,work,authority,**common));second=launch(case,spec(case,cmd,other,other_authority,**common))
    a=first();b=second();assert sorted([a[0],b[0]])==([0,2] if different else [0,0]),(a,b)
    view=ScopeStore(case.repo,Budget()).load(cmd)
    assert len(view['command']['events'])==1 and len(view['command']['staged_blobs'])==3


def test_h2_two_writers_as_cas(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);service=H2Service(case.repo,authority=authority)
    commands=[str(uuid4()),str(uuid4())]
    for cmd in commands:service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    common=dict(barrier_point='before_finalize',barrier=str(tmp_path/'barrier'))
    first=launch(case,spec(case,commands[0],work,authority,**common));second=launch(case,spec(case,commands[1],work,authority,**common))
    a=first();b=second();assert a[0]==b[0]==2,(a,b)
    states=[case.repo.lookup_command(cmd)['run']['body']['status'] for cmd in commands]
    assert sorted(states)==['blocked','stale']
    for cmd in commands:final(case,cmd)


@pytest.mark.parametrize('scenario',['build','guard','revalidate'])
@pytest.mark.parametrize('phase,point',[('seal','before_commit'),('seal','after_commit'),('finalize','before_commit'),('finalize','after_commit')])
def test_h2_model_guard_revalidate_crash_paths(tmp_path,scenario,phase,point):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1)
    if scenario=='revalidate':
        case.advance(2,proof=False)
        work,authority=case.work(2,mode='revalidate',goal='admission',guards=list(case.meta['guards']))
    else:work,authority=case.work(2,proof=scenario=='build')
    cmd=str(uuid4());service=H2Service(case.repo,authority=authority);service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    result=launch(case,spec(case,cmd,work,authority,phase=phase,repo_point=point,action='kill'))()
    assert result[0]==71,result
    resumed=service.resume(cmd,store_id=case.store_id);assert resumed['status']=='blocked',resumed
    assert resumed['result']['candidate_outcome']=={'build':'valid','guard':'guard_only','revalidate':'revalidated'}[scenario]
    final(case,cmd)
