import hashlib
import multiprocessing as mp
import os
from pathlib import Path
import queue
import sqlite3
import pytest
from dacn_s02.repository import Repository
from dacn_s02.service import staged
from helpers import model,aset,issue,run,evidence
from process_worker import worker,kill_worker
from test_lifecycle import add_answer,application_batch

def state(repo,session):
    repo.verify()
    with sqlite3.connect(repo.path) as c:
        tables={k:c.execute(f'SELECT COUNT(*) FROM {k}').fetchone()[0] for k in ('records','models','analysis_sets','operations','operation_events','staged_blobs','promotions','application_heads')}
        applied=c.execute("SELECT COUNT(*) FROM operation_events WHERE kind='application_applied'").fetchone()[0]
    return dict(heads=repo.heads(session),counts=tables,applied_events=applied)

def archive(repo,name):
    raw=repo.path.read_bytes();result=dict(sha256=hashlib.sha256(raw).hexdigest(),byte_length=len(raw))
    directory=os.environ.get('S02_TEST_EVIDENCE_DIR')
    if directory:
        path=Path(directory)/(name+'.sqlite3');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);result['path']=str(path)
    return result

def race(repo,tasks):
    ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
    processes=[ctx.Process(target=worker,args=(str(repo.path),barrier,q,t)) for t in tasks]
    events=[]
    try:
        for p in processes:p.start()
        while sum(e['event']=='result' for e in events)<2:
            events.append(q.get(timeout=30))
        for p in processes:p.join(15);assert not p.is_alive() and p.exitcode==0
    finally:
        for p in processes:
            if p.is_alive():p.terminate();p.join(10)
        q.close();q.join_thread()
    assert len({e['pid'] for e in events if e['event']=='ready'})==2
    assert max(e['at_ns'] for e in events if e['event']=='ready')<min(e['at_ns'] for e in events if e['event']=='released')
    for e in events:
        if e['event']=='result':
            assert e['encoder_calls'][e['backend']]>0
            assert e['encoder_calls']['python' if e['backend']=='c' else 'c']==0
    return events,[e for e in events if e['event']=='result']

@pytest.mark.parametrize('kind',['model','analysis_set','analysis_and_log'])
def test_real_two_process_publication(foundation,kind):
    f=foundation;tasks=[]
    if kind!='model':m,a=f.initial()
    for n in (1,2):
        op=f.operation();f.repo.prepare(op)
        if kind=='analysis_and_log' and n==2:tasks.append(dict(kind='log',command_id=op['command_id']));continue
        if kind=='model':
            m=model(f.context,f.snapshot,op['reserved_run_id'],f'M{n}');a=aset(m,f'AS{n}');batch=[m,a];head=(m['id'],a['id'])
            rr=run(op,f.context,f.config,model_id=m['id'],set_id=a['id'])
        else:
            q=issue(m,f'Q{n}',key=f'Question{n}');new=aset(m,f'AS-new-{n}',a,issues=[q['id']]);batch=[q,new];head=(m['id'],new['id'])
            rr=run(op,f.context,f.config,set_id=new['id'])
        tasks.append(dict(kind='finalize',command_id=op['command_id'],records=batch+[rr],head=head))
    events,results=race(f.repo,tasks)
    statuses=sorted(r['status'] for r in results)
    assert statuses==(['completed','logged'] if kind=='analysis_and_log' else ['completed','stale'])
    if kind!='analysis_and_log':
        error=next(r for r in results if r['status']=='stale')['errors'][0]
        assert error['code']==('MODEL_CONFLICT' if kind=='model' else 'ANALYSIS_CONFLICT')
    final=state(Repository(f.repo.path),f.session)
    assert final['counts']['models']==1
    assert final['counts']['analysis_sets']==(1 if kind=='model' else 2)
    evidence('real_two_process_race',case=kind,events=events,final=final,database=archive(f.repo,'race-'+kind))

def test_two_process_application_claim(foundation):
    f=foundation;add_answer(f)
    tasks=[dict(kind='claim',operation=f.operation(kind='apply_answer',answer_id='Answer1',issue_key='Question2')) for _ in range(2)]
    events,results=race(f.repo,tasks)
    assert sorted(r['status'] for r in results)==['claimed','error']
    assert next(r for r in results if r['status']=='error')['error']['code']=='APPLICATION_CONFLICT'
    final=state(f.repo,f.session);assert final['counts']['application_heads']==1
    evidence('real_two_process_race',case='application_claim',events=events,final=final,database=archive(f.repo,'race-application-claim'))

def test_two_process_same_application_finalization(foundation):
    f=foundation;m,a,answer=add_answer(f);op,batch,extra=application_batch(f,m,a,answer)
    task=dict(kind='finalize',command_id=op['command_id'],records=batch,head=('M2','AS-M2'),application_events=extra)
    events,results=race(f.repo,[task,task]);assert [r['status'] for r in results]==['completed','completed']
    assert len({r['run_id'] for r in results})==1
    final=state(f.repo,f.session);assert final['applied_events']==1 and final['counts']['models']==2
    evidence('real_two_process_race',case='same_application_finalization',events=events,final=final,database=archive(f.repo,'race-application-finalize'))

@pytest.mark.parametrize('kind',['finalize','capture'])
@pytest.mark.parametrize('point',['before_commit','after_commit'])
def test_real_kill_synchronized(foundation,kind,point):
    f=foundation;op=f.operation();f.repo.prepare(op);cmd=op['command_id']
    if kind=='finalize':task=dict(kind=kind,command_id=cmd,records=[run(op,f.context,f.config)])
    else:
        e=f.repo.get_command(cmd)['events'][0]
        f.repo.append_event(cmd,'dispatch_intent',dict(prepared_event=dict(command_id=cmd,event_id=e['event_id']),transport_attempt=1))
        item=staged(cmd,'Response','llm_response',b'invalid bytes retained')
        task=dict(kind=kind,command_id=cmd,staged=[item],payload=dict(response=dict(command_id=cmd,blob_id='Response'),http_status=200,safe_headers={},requested_model='stub',returned_model=None,provider_response_id=None,usage=None,elapsed_ms=1))
    ctx=mp.get_context('spawn');parent,child=ctx.Pipe();release=ctx.Event();p=ctx.Process(target=kill_worker,args=(str(f.repo.path),child,release,task,point))
    try:
        p.start();assert parent.poll(25);sync=parent.recv();p.terminate();p.join(15);assert not p.is_alive() and p.exitcode<0
    finally:
        if p.is_alive():p.kill();p.join(10)
        parent.close();child.close()
    repo=Repository(f.repo.path);command=repo.get_command(cmd)
    expected=('finalized' if kind=='finalize' else 'captured') if point=='after_commit' else ('prepared' if kind=='finalize' else 'dispatch_unknown')
    assert command['state']==expected
    assert sync['encoder_calls'][sync['backend']]>0
    evidence('real_process_termination',case=kind,point=point,synchronized=sync,exit_code=p.exitcode,result_state=expected,final=state(repo,f.session),database=archive(repo,'kill-'+kind+'-'+point))
