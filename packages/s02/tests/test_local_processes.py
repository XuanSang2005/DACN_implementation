"""Targeted OS-process crash/claim tests, no broad stress suite."""
from contextlib import contextmanager
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
import subprocess,sys,threading,time,os
import pytest

from dacn_s02.codec_boundary import encode,decode
from dacn_s02.errors import S02Error
from dacn_s02.local_journal import Journal,LIMITS
from dacn_s02.local_service import LocalService
from dacn_s02.local_work import LocalWork,identity
from dacn_s02.repository import digest
from local_llm_worker import HTTPFake
from test_local_pipeline import FakeProvider,setup,Crash

@contextmanager
def endpoint():
    provider=FakeProvider();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            raw=self.rfile.read(int(self.headers['Content-Length']));requests.append(raw)
            response=provider.send(raw,10)
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(response.body)));self.end_headers();self.wfile.write(response.body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}',requests
    finally:server.shutdown();server.server_close();thread.join(2);assert not thread.is_alive()


def worker(tmp_path,cfg,label):
    path=tmp_path/(label+'.json');out=tmp_path/(label+'.out');cfg=dict(cfg,out=str(out));path.write_bytes(encode(cfg))
    proc=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('local_llm_worker.py')),str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return proc,out


def finish(proc,out,code=0):
    stdout,stderr=proc.communicate(timeout=60)
    assert proc.returncode==code,(stdout,stderr)
    assert ('worker_backend='+os.environ.get('S02_TEST_CODEC_BACKEND','c')).encode() in stdout
    return decode(out.read_bytes()) if out.exists() else None


def race(tmp_path,configs):
    barrier=tmp_path/'go';workers=[worker(tmp_path,dict(cfg,barrier=str(barrier)),str(i)) for i,cfg in enumerate(configs)]
    deadline=time.monotonic()+10
    while not all(out.with_suffix('.ready').exists() for _,out in workers):
        assert time.monotonic()<deadline
        time.sleep(.01)
    barrier.write_text('go')
    return [finish(proc,out) for proc,out in workers]


def test_atomic_last_slot_and_claim_across_processes(tmp_path):
    store=str(uuid4());j=Journal(tmp_path/'journal.sqlite3',store);j.initialize()
    def cfg(step):return dict(command_id=str(uuid4()),session_id=str(uuid4()),step=step,store_id=store,limits=LIMITS,request_sha256=digest(b''),prompt_sha256=digest(b''))
    for step in range(1,4):j.reserve(cfg(step))
    base=dict(mode='reserve',journal=str(j.path),store_id=store)
    results=race(tmp_path,[dict(base,work=cfg(4)),dict(base,work=cfg(4))])
    assert sorted(r['ok'] for r in results)==[False,True]
    failure=next(r for r in results if not r['ok']);assert failure['error']=='S02Error' and failure['message']=='local_budget_exhausted'
    with j.connection() as c:
        rows=c.execute('SELECT command FROM work').fetchall();assert len(rows)==4;command=rows[0][0]
    sub=tmp_path/'claim';sub.mkdir();base=dict(mode='claim',journal=str(j.path),store_id=store,command=command)
    results=race(sub,[base,base]);assert sorted(r['claimed'] for r in results)==[False,True]
    with pytest.raises(S02Error,match='local_budget_exhausted'):Journal(j.path,store).reserve(cfg(1))


@pytest.mark.parametrize('point,total,status',[('after_intent',0,'interrupted'),('after_http',1,'interrupted'),('after_capture',4,'completed'),('after_s01_submit',4,'completed')])
def test_hard_exit_then_process_reopen_no_duplicate_post(tmp_path,point,total,status):
    s,source,receipt,_=setup(tmp_path)
    with endpoint() as (url,requests):
        cfg=dict(mode='analyze',settings=str(s.path),endpoint=url,input=str(source),receipt=str(receipt),crash=point)
        proc,out=worker(tmp_path,cfg,'crash');finish(proc,out,71)
        proc,out=worker(tmp_path,dict(cfg,mode='resume',crash=None),'resume');result=finish(proc,out)
        assert result['status']==status,result
        assert len(requests)==total
    # Real CLI readback with no daemon/provider, not the test driver.
    cli=subprocess.run([sys.executable,'-B','-m','dacn_s02','--config',str(s.path),'local-report','--receipt',str(receipt)],capture_output=True)
    assert cli.returncode==(0 if status=='completed' else 3),cli.stderr
    report=decode(cli.stdout);assert report['status']==status and report['command_id']==result['command_id']


def test_two_process_resumes_single_network_sender(tmp_path):
    s,source,receipt,_=setup(tmp_path)
    with endpoint() as (url,requests):
        def hook(point):
            if point=='after_prepare':raise Crash()
        with pytest.raises(Crash):LocalService(s,HTTPFake(url),_hook=hook).analyze(receipt=receipt,store_key='local',input_path=source)
        cfg=dict(mode='resume',settings=str(s.path),endpoint=url,receipt=str(receipt))
        results=race(tmp_path,[cfg,cfg])
        assert any(r.get('status')=='completed' for r in results),results
        assert all(r.get('status')=='completed' or 'in progress' in r.get('message','') for r in results)
        assert len(requests)==4
        again=LocalService(s).resume(receipt=receipt);assert again['status']=='completed' and len(requests)==4


def test_paired_cas_preserves_capture_but_loser_has_no_domain_output(tmp_path):
    s,source,receipt,provider=setup(tmp_path);service=LocalService(s,provider);done=[]
    def hook(point):
        if point!='after_response_event' or done:return
        done.append(True)
        journal=service.journal();flow=journal.flow();command=identity(flow['root'],'step:1');work=journal.get(command);cfg=decode(work['config'])
        competing=str(uuid4());cfg['command_id']=competing;cfg['reserved_run_id']=identity(competing,'run');cfg['attempt_id']=identity(competing,'attempt')
        store=LocalWork(service.repo);store.prepare(cfg,work['prompt'],work['request']);store.dispatch(competing)
        meta=decode(work['capture']);meta['command_id']=competing;store.capture(competing,meta,work['body']);store.seal(competing);assert store.publish(competing)['status']=='completed'
    service.hook=hook;result=service.analyze(receipt=receipt,store_key='local',input_path=source)
    assert result['status']=='stale' and result['result']['result_pair'] is None,result
    assert len(provider.calls)==1 and result['result']['attempts'][0]['response_artifact_id'] is not None
    assert LocalService(s).report(receipt=receipt)==result
