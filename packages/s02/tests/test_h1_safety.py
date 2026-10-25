"""The complete H1 minimum safety matrix is an H1 release gate."""
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from dacn_s02.codec_boundary import decode,encode
from dacn_s02.errors import S02Error
from dacn_s02.h1_service import H1Service
from dacn_s02.h1_store import WorkStore
from dacn_s02.repository import Repository,digest
from h1_fixtures import Case,input_data


def spec(case,command,**changes):
    value=dict(db=str(case.repo.path),command=command,mode='resume',parent=case.parent,
               step='bootstrap',store_id=case.store_id)
    value.update(changes);return value


def start_worker(case,value):
    evidence=Path(os.environ.get('S02_TEST_EVIDENCE_DIR',str(case.path/'evidence')));evidence.mkdir(parents=True,exist_ok=True)
    token=str(uuid4());input_path=evidence/(token+'.input.json');input_path.write_text(json.dumps(value))
    argv=[sys.executable,'-B',str(Path(__file__).with_name('h1_worker.py')),str(input_path)]
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
    process=subprocess.Popen(argv,cwd=case.path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def finish():
        stdout,stderr=process.communicate(timeout=45)
        (evidence/(token+'.stdout.log')).write_bytes(stdout);(evidence/(token+'.stderr.log')).write_bytes(stderr)
        (evidence/(token+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(case.path),exit_code=process.returncode)))
        if process.returncode!=71:
            lines=stdout.decode().splitlines();observed=json.loads(next(s.removeprefix('H1_ENCODERS ') for s in lines if s.startswith('H1_ENCODERS ')))
            selected=os.environ.get('S02_TEST_CODEC_BACKEND','c');assert observed['backend']==selected
            assert observed['calls'][selected]>0 and observed['calls']['python' if selected=='c' else 'c']==0
        return process.returncode,stdout.decode(),stderr.decode()
    return finish


def worker(case,value):return start_worker(case,value)()


def assert_final(case,command):
    repo=Repository(case.repo.path);repo.verify();cmd=repo.get_command(command);assert cmd['state']=='finalized'
    store=WorkStore(repo);view=store.load(command);plan,stage=store.checked_plan(cmd,view['state'],view['config'],view['primary'],view['raw'])
    assert sum(e['kind']=='finalized' for e in cmd['events'])==1
    assert len(store.plans(cmd,view['state']))==1
    assert cmd['run']['id']==cmd['operation']['reserved_run_id']
    assert cmd['run']['body']['completed_at']==next(r for r in plan['batch']['records'] if r['type']=='run')['body']['completed_at']
    print('H1_SAFETY '+encode(dict(command=command,run=cmd['run']['id'],plan_sha256=stage['sha256'],raw_sha256=view['raw']['sha256'] if view['raw'] else None,
        head=view['current_head'],created_at=cmd['run']['created_at'],completed_at=cmd['run']['body']['completed_at'])).decode('ascii'))
    return view,plan,stage


@pytest.mark.parametrize('when',['before','after'])
def test_crash_receipt_creation_and_explicit_prepare(tmp_path,when):
    case=Case(tmp_path);config=tmp_path/'cli.toml';config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    receipt=tmp_path/'work.receipt';cmd=str(uuid4())
    code,out,err=worker(case,spec(case,cmd,mode='receipt_prepare',config=str(config),receipt=str(receipt),receipt_kill=when))
    assert code==71 and receipt.exists()==(when=='after')
    assert Repository(case.repo.path).get_command(cmd) is None
    assert H1Service(case.repo).resume(cmd)['status']=='not_prepared'
    result=H1Service(case.repo).prepare(cmd,case.parent,'bootstrap',None,case.store_id);assert result['status']=='prepared'
    assert H1Service(case.repo).resume(cmd)['status']=='completed';assert_final(case,cmd)


@pytest.mark.parametrize('phase',['prepare','seal','finalize'])
@pytest.mark.parametrize('fault',[('before_commit','kill'),('after_commit','kill'),('after_commit','lost_ack'),('after_commit','unknown')])
def test_commit_crash_lost_ack_unknown_reopen(tmp_path,phase,fault):
    case=Case(tmp_path);cmd=str(uuid4())
    if phase!='prepare':H1Service(case.repo).prepare(cmd,case.parent,'bootstrap',None,case.store_id)
    mode='prepare' if phase=='prepare' else 'resume'
    point,action=fault
    code,out,err=worker(case,spec(case,cmd,mode=mode,phase=phase,repo_point=point,action=action))
    assert code==(71 if action=='kill' else 3 if action=='unknown' else 0),(code,out,err)
    if action=='unknown':
        assert 'Commit outcome unknown' in out
        assert not case.repo.path.exists()
        Path(str(case.repo.path)+'.unavailable').rename(case.repo.path)
    repo=Repository(case.repo.path);repo.verify();stored=repo.get_command(cmd)
    if phase=='prepare' and point=='before_commit':
        assert stored is None
        assert H1Service(repo).resume(cmd)['status']=='not_prepared'
        H1Service(repo).prepare(cmd,case.parent,'bootstrap',None,case.store_id)
    elif phase=='seal':
        view=WorkStore(repo).load(cmd);assert len(WorkStore(repo).plans(stored,view['state']))==(0 if point=='before_commit' else 1)
    elif phase=='finalize':
        assert (stored['state']=='finalized')==(point=='after_commit')
        assert (repo.heads(case.intake['session_id'])!=(None,None))==(point=='after_commit')
    output=H1Service(repo).resume(cmd);assert output['status']=='completed',output
    before=encode(output);assert encode(H1Service(Repository(repo.path)).resume(cmd))==before
    assert_final(case,cmd)


@pytest.mark.parametrize('barrier_point',['before_seal','before_finalize'])
def test_two_resumers_before_and_after_seal(tmp_path,barrier_point):
    case=Case(tmp_path);cmd=case.prepare('bootstrap')
    if barrier_point=='before_finalize':
        def pause(point):
            if point=='after_seal':raise RuntimeError('Pause after durable seal')
        with pytest.raises(RuntimeError,match='durable seal'):H1Service(case.repo,_hook=pause).resume(cmd)
    value=spec(case,cmd,barrier_point=barrier_point,barrier=str(tmp_path/'barrier'))
    one=start_worker(case,value);two=start_worker(case,value)
    a=one();b=two();assert a[0]==b[0]==0,(a,b)
    result_a=decode(next(s.removeprefix('H1_RESULT ') for s in a[1].splitlines() if s.startswith('H1_RESULT ')).encode())
    result_b=decode(next(s.removeprefix('H1_RESULT ') for s in b[1].splitlines() if s.startswith('H1_RESULT ')).encode())
    assert result_a==result_b
    assert_final(case,cmd)


@pytest.mark.parametrize('different',[False,True])
def test_two_preparers_same_receipt_compare_intent(tmp_path,different):
    case=Case(tmp_path);case.advance('bootstrap');cmd=str(uuid4());paths=[]
    for n in range(2):
        candidate=case.responses[0].copy()
        if different and n:candidate['inspection']=[]  # Raw differs; not parsed at T0.
        path=tmp_path/('raw'+str(n));path.write_bytes(encode(candidate));paths.append(path)
    common=dict(mode='prepare',step=1,barrier_point='prepare',barrier=str(tmp_path/'barrier'))
    one=start_worker(case,spec(case,cmd,raw=str(paths[0]),**common));two=start_worker(case,spec(case,cmd,raw=str(paths[1]),**common))
    a=one();b=two();assert sorted((a[0],b[0]))==([0,2] if different else [0,0]),(a,b)
    view=WorkStore(Repository(case.repo.path)).load(cmd)
    assert len(view['command']['events'])==1 and len(view['command']['staged_blobs'])==2
    assert view['raw']['bytes'] in [p.read_bytes() for p in paths]


@pytest.mark.parametrize('step',[1,2])
def test_stale_as_head_and_model_head_are_separate(tmp_path,step):
    case=Case(tmp_path);case.advance('bootstrap')
    if step==2:case.advance(1)
    original=case.repo.heads(case.intake['session_id']);raw=encode(case.responses[step-1]);cmd=case.prepare(step,raw)
    def pause(point):
        if point=='after_seal':raise RuntimeError('Sealed loser')
    with pytest.raises(RuntimeError):H1Service(case.repo,_hook=pause).resume(cmd)
    winner=case.prepare(step,raw);result=H1Service(case.repo).resume(winner);assert result['status']=='completed'
    current=case.repo.heads(case.intake['session_id'])
    assert (original[0]==current[0])==(step==1)
    assert original[1]!=current[1]
    stale=H1Service(case.repo).resume(cmd);assert stale['status']=='stale' and stale['result']['result_pair'] is None
    assert case.repo.heads(case.intake['session_id'])==current
    view,plan,_=assert_final(case,cmd)
    assert all(i not in view['state']['records'] for i in [plan['batch']['head'][1],*([plan['batch']['head'][0]] if step==2 else [])])


def test_default_cache_spill_crash_seal_recovery(tmp_path):
    source=input_data();source['actors']=['Synthetic A '+('漢'*200000),'Synthetic B '+('漢'*200000)]
    case=Case(tmp_path,source);cmd=case.prepare('bootstrap')
    from dacn_s02.local_io import settings,write_receipt
    config=tmp_path/'cli.toml';config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    receipt=tmp_path/'large.receipt';write_receipt(settings(config),receipt,cmd,store_id=case.store_id)
    code,out,err=worker(case,spec(case,cmd,mode='resume',phase='seal',repo_point='before_commit',action='kill'))
    assert code==71,(code,out,err)
    journal=Path(str(case.repo.path)+'-journal')
    assert journal.is_file() and journal.read_bytes()[:8]==bytes.fromhex('d9d505f920a163d7')
    before=(digest(case.repo.path.read_bytes()),digest(journal.read_bytes()))
    with pytest.raises(S02Error) as bad_store:H1Service(Repository(case.repo.path)).resume(cmd,store_id=str(uuid4()))
    assert bad_store.value.error['details']['invariant']=='receipt_store_identity'
    assert (digest(case.repo.path.read_bytes()),digest(journal.read_bytes()))==before
    with pytest.raises(S02Error) as readonly:H1Service(Repository(case.repo.path)).report(cmd,progress=True)
    assert readonly.value.error['stage']=='persistence'
    assert (digest(case.repo.path.read_bytes()),digest(journal.read_bytes()))==before
    from dacn_s02 import reservation
    reservation.namespace(case.repo.path.parent).mkdir(exist_ok=True)
    mark=reservation.marker(case.repo.path.parent);mark.write_bytes(b'SYNTHETIC reserved partial state')
    with pytest.raises(S02Error) as reserved:H1Service(Repository(case.repo.path)).resume(cmd,store_id=case.store_id)
    assert 'migration-reserved' in reserved.value.error['message']
    assert (digest(case.repo.path.read_bytes()),digest(journal.read_bytes()))==before
    mark.rename(mark.with_suffix('.fixture-cleared'))  # Explicit test fault removal, never a production repair.
    from test_h1_cli import cli
    recovered,output=cli(config,'resume','--receipt',receipt)
    assert recovered.returncode==0 and output['status']=='completed',(recovered.stderr,output)
    assert_final(case,cmd)
