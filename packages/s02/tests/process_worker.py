"""Spawned workers; each opens its own real SQLite connection."""
import os
import time
from dacn_s02.repository import Repository
from dacn_s02.errors import S02Error

def observe_backend():
    import simplejson
    import simplejson.encoder as encoder
    mode=os.environ.get('S02_TEST_CODEC_BACKEND','c');simplejson._toggle_speedups(mode=='c')
    counts={'c':0,'python':0}
    if mode=='c':
        original=encoder.c_make_encoder
        if original is None:raise RuntimeError('C encoder unavailable')
        def seen(*a,**kw):counts['c']+=1;return original(*a,**kw)
        encoder.c_make_encoder=seen
    py=encoder._make_iterencode
    def seen_py(*a,**kw):counts['python']+=1;return py(*a,**kw)
    encoder._make_iterencode=seen_py
    return mode,counts

def worker(db,barrier,queue,task):
    backend,counts=observe_backend()
    def event(name,**extra): queue.put(dict(pid=os.getpid(),event=name,at_ns=time.monotonic_ns(),backend=backend,encoder_calls=dict(counts),**extra))
    def hook(point,c):
        if point in ('before_begin','after_begin','before_commit','after_commit'): event(point)
    repo=Repository(db,_hook=hook)
    try:
        event('ready');barrier.wait(timeout=25);event('released')
        if task['kind']=='claim':
            result=repo.prepare(task['operation']);event('result',status='claimed',command_id=result)
        elif task['kind']=='log':
            repo.append_event(task['command_id'],'log',{'message':'Concurrent synthetic log'});event('result',status='logged')
        else:
            result=repo.finalize(task['command_id'],task['records'],head=task.get('head'),application_events=task.get('application_events',()))
            event('result',status=result['body']['status'],run_id=result['id'],errors=result['body']['errors'])
    except S02Error as exc: event('result',status='error',error=exc.error)
    except BaseException as exc: event('worker_failure',error=repr(exc));raise

def kill_worker(db,pipe,release,task,point):
    backend,counts=observe_backend()
    def hook(p,c):
        if p==point:
            pipe.send(dict(pid=os.getpid(),point=p,at_ns=time.monotonic_ns(),in_transaction=c.in_transaction,backend=backend,encoder_calls=dict(counts)))
            if not release.wait(25): raise RuntimeError('Parent did not terminate synchronized worker')
    repo=Repository(db,_hook=hook)
    if task['kind']=='capture': repo.append_event(task['command_id'],'response_received',task['payload'],staged=task['staged'])
    else: repo.finalize(task['command_id'],task['records'])
