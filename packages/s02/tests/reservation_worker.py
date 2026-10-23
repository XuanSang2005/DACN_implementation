"""Spawned contenders use the real installed API/CLI and OS lock."""
import os,time,subprocess,sys
from dacn_s02.repository import Repository
from dacn_s02.errors import S02Error
from process_worker import observe_backend

def initialize(path,pipe,gate,point=None,config=None):
    mode,counts=observe_backend()
    def send(event,**kw):pipe.send(dict(event=event,pid=os.getpid(),at_ns=time.monotonic_ns(),backend=mode,encoder_calls=dict(counts),**kw))
    def hook(p,c):
        if p==point:
            send('checkpoint',point=p)
            if not gate.wait(30):raise RuntimeError('Missing parent release')
    send('started')
    try:
        if config is not None:
            p=subprocess.run([sys.executable,'-B','-m','dacn_s02','--config',str(config),'init'],capture_output=True,text=True)
            send('result',exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        else:
            Repository(path,timeout=5,_hook=hook).initialize(create_parent=True)
            send('result',exit_code=0)
    except S02Error as e:send('error',error=e.error)
