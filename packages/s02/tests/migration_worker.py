"""Real spawned-process synchronization for synthetic P3 stores."""
import os,sqlite3,time
from dacn_s02.migration import Migration
from dacn_s02.errors import S02Error
from process_worker import observe_backend

def protocol(settings,source,receipt,task,pipe,gate,point=None,barrier=None):
    mode,counts=observe_backend()
    def send(event,**kw):pipe.send(dict(event=event,pid=os.getpid(),at_ns=time.monotonic_ns(),backend=mode,encoder_calls=dict(counts),**kw))
    def hook(p,c):
        if p==point:
            send('checkpoint',point=p,in_transaction=c.in_transaction if c else None)
            if not gate.wait(30):raise RuntimeError('Missing parent release')
        if barrier is not None and p=='before_activation_begin':barrier.wait(30)
    m=Migration(settings,source,_hook=hook)
    try:
        if task=='copy':result=m.copy(receipt,offline=True)
        elif task=='inspect':result=m.inspect(offline=True)
        else:result=m.activate(receipt,offline=True,confirm=True,operator='process-'+str(os.getpid()))
        send('result',result=result)
    except S02Error as e:send('error',error=e.error)
    except Exception as e:send('unexpected',error=repr(e));raise

def hot_source(path,pipe,gate):
    c=sqlite3.connect(path,autocommit=True);c.execute('PRAGMA cache_size=4');c.execute('PRAGMA synchronous=FULL');c.execute('BEGIN IMMEDIATE')
    c.execute('CREATE TABLE synthetic_crash (id INTEGER PRIMARY KEY, payload BLOB)')
    for i in range(80):c.execute('INSERT INTO synthetic_crash VALUES (?,?)',(i,b'x'*65536))
    pipe.send(dict(event='spilled',pid=os.getpid(),in_transaction=c.in_transaction))
    gate.wait(30);c.close()

def source_writer(path,pipe,gate):
    c=sqlite3.connect(path,autocommit=True,timeout=.05);c.execute('BEGIN IMMEDIATE')
    c.execute('UPDATE sessions SET sequence=sequence+1')
    try:c.execute('COMMIT');pipe.send(dict(event='unexpected_commit'))
    except sqlite3.OperationalError as e:pipe.send(dict(event='blocked',code=e.sqlite_errorcode))
    if gate.wait(30):c.execute('COMMIT');pipe.send(dict(event='committed'))
    c.close()

def target_lock(path,pipe,gate):
    c=sqlite3.connect(path,autocommit=True);c.execute('BEGIN IMMEDIATE');pipe.send(dict(event='locked'));gate.wait(30);c.execute('ROLLBACK');c.close()
