from dataclasses import replace
from pathlib import Path
import json,multiprocessing as mp,os,signal,sqlite3
import pytest
from dacn_s02.migration import Migration
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from migration_fixtures import make_migration
from migration_worker import protocol,hot_source,source_writer,target_lock
from helpers import evidence
from test_migration import disk
CTX=mp.get_context('spawn')

def launch(fn,args):
    parent,child=CTX.Pipe();gate=CTX.Event();p=CTX.Process(target=fn,args=(*args,child,gate));p.start();return p,parent,gate

def recv(pipe):
    assert pipe.poll(35),'worker IPC deadline';return pipe.recv()

def kill(p):
    os.kill(p.pid,signal.SIGKILL);p.join(10);assert p.exitcode==-signal.SIGKILL

@pytest.mark.parametrize('phase',['inspect','resume_missing','resume_committed'])
def test_hot_journal_readonly_all_entry_gates(tmp_path,phase):
    m,r,_=make_migration(tmp_path)
    if phase=='resume_committed':m.copy(r,offline=True)
    if phase=='resume_missing':
        def stop(p,c):
            if p=='before_reserve':raise OSError('pause')
        m.hook=stop
        with pytest.raises(OSError):m.copy(r,offline=True)
        m.hook=lambda *a:None
    p,pipe,gate=launch(hot_source,(str(m.source_repo.path),));observed=recv(pipe);kill(p)
    journal=m.source_repo.path.with_name('s02.sqlite3-journal');raw=journal.read_bytes()
    assert len(raw)>512 and raw[:8]==bytes.fromhex('d9d505f920a163d7')
    before=disk(m.source);target_before=disk(m.destination) if m.destination.exists() else None
    calls=[lambda:m.inspect(offline=True)] if phase=='inspect' else [lambda:m.copy(r,offline=True,resume=True),lambda:m.reconcile(r,offline=True),lambda:m.activate(r,offline=True,confirm=True,operator='test')]
    for call in calls:
        with pytest.raises(S02Error) as err:call()
        assert err.value.error['code']=='SOURCE_RECOVERY_REQUIRED'
        assert err.value.error['details']['sqlite_errorcode']==sqlite3.SQLITE_READONLY_ROLLBACK
        assert disk(m.source)==before
        assert (disk(m.destination) if m.destination.exists() else None)==target_before
    evidence('migration_hot_journal',phase=phase,ipc=observed,journal_header=raw[:28].hex(),source_before=before,source_after=disk(m.source),target_unchanged=True)

@pytest.mark.parametrize('task,point,status',[
 ('copy','before_copy_commit','partial'),('copy','after_copy_commit','committed_inactive'),
 ('activate','before_activation_commit','committed_inactive'),('activate','after_activation_commit','active'),
 ('copy','receipt_durable','missing')])
def test_real_kill_boundaries(tmp_path,task,point,status):
    m,r,_=make_migration(tmp_path,empty=True)
    if task=='activate':m.copy(r,offline=True)
    before=disk(m.source);parent,child=CTX.Pipe();gate=CTX.Event()
    p=CTX.Process(target=protocol,args=(m.settings,m.source,r,task,child,gate,point));p.start()
    observed=recv(parent);assert observed['event']=='checkpoint';kill(p)
    result=m.reconcile(r,offline=True);assert result['status']==status and disk(m.source)==before
    evidence('migration_real_kill',task=task,point=point,ipc=observed,result=result)

@pytest.mark.parametrize('order',['simultaneous','wrong_first','right_first'])
def test_activation_process_identity_and_cas(tmp_path,order):
    m,r,_=make_migration(tmp_path,empty=True);m=Migration(replace(m.settings,timeout=5000),m.source);m.copy(r,offline=True)
    bad=r.parent/'wrong.json';v=json.loads(r.read_bytes());v['activation_id']='00000000-0000-4000-8000-000000000001';bad.write_bytes(encode(v))
    outputs=[]
    if order=='simultaneous':
        barrier=CTX.Barrier(2);workers=[]
        for _ in range(2):
            parent,child=CTX.Pipe();gate=CTX.Event();p=CTX.Process(target=protocol,args=(m.settings,m.source,r,'activate',child,gate,None,barrier));p.start();workers.append((p,parent,gate))
        for p,parent,gate in workers:outputs.append(recv(parent));p.join(10);assert p.exitcode==0
        assert all(v['event']=='result' for v in outputs) and outputs[0]['result']==outputs[1]['result']
    else:
        for path in ([bad,r] if order=='wrong_first' else [r,bad]):
            p,pipe,gate=launch(protocol,(m.settings,m.source,path,'activate'));outputs.append(recv(pipe));p.join(10);assert p.exitcode==0
        assert {v['event'] for v in outputs}=={'result','error'}
        assert next(v for v in outputs if v['event']=='error')['error']['code']=='MIGRATION_IDENTITY_CONFLICT'
    with sqlite3.connect(m.target.path) as c:assert c.execute('SELECT count(*) FROM store_activation').fetchone()[0]==1
    evidence('migration_activation_race',order=order,workers=outputs)

def test_source_read_lock_blocks_commit_not_future_writer(tmp_path):
    m,r,_=make_migration(tmp_path);m.copy(r,offline=True)
    parent,child=CTX.Pipe();gate=CTX.Event();p=CTX.Process(target=protocol,args=(m.settings,m.source,r,'inspect',child,gate,'source_locked'));p.start()
    first=recv(parent);assert first['event']=='checkpoint'
    w,pipe,release=launch(source_writer,(str(m.source_repo.path),));blocked=recv(pipe)
    assert blocked==dict(event='blocked',code=sqlite3.SQLITE_BUSY)
    gate.set();assert recv(parent)['event']=='result';p.join(10);assert p.exitcode==0
    release.set();assert recv(pipe)['event']=='committed';w.join(10);assert w.exitcode==0
    before=disk(m.destination)
    with pytest.raises(S02Error):m.activate(r,offline=True,confirm=True,operator='test')
    assert disk(m.destination)==before
    evidence('migration_source_lock',reader=first,writer=blocked,future_source_change_rejected=True)

def test_activation_busy_is_not_identity_conflict(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True);m.copy(r,offline=True)
    p,pipe,gate=launch(target_lock,(str(m.target.path),));assert recv(pipe)['event']=='locked'
    try:
        with pytest.raises(S02Error) as err:m.activate(r,offline=True,confirm=True,operator='test')
        assert err.value.error['code']=='MIGRATION_ACTIVATION_UNACKNOWLEDGED' and err.value.error['details']['sqlite_errorcode']==sqlite3.SQLITE_BUSY
    finally:gate.set();p.join(10)
    assert p.exitcode==0 and m.reconcile(r,offline=True)['status']=='committed_inactive'
