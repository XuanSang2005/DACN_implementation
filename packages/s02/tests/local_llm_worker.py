"""Process-only test driver, production imported solely from installed wheels."""
import os,sys,time
from pathlib import Path
import simplejson
if __name__=='__main__':
    backend=os.environ.get('S02_TEST_CODEC_BACKEND','c')
    simplejson._toggle_speedups(backend=='c')
    import simplejson.encoder
    assert (simplejson.encoder.c_make_encoder is not None)==(backend=='c')
    print('worker_backend='+backend,flush=True)
from dacn_s02.codec_boundary import decode,encode
from dacn_s02.local_journal import Journal
from dacn_s02.local_io import settings
from dacn_s02.local_service import LocalService
from dacn_s02.local_transport import exchange

class HTTPFake:
    origin='synthetic_mock'
    def __init__(self,endpoint):self.endpoint=endpoint
    def configuration(self):return dict(fake_http=self.endpoint)
    def pin(self):return dict(model='fake-local',model_digest='f'*64,endpoint=self.endpoint,runtime='fake-test-only')
    def bound(self,messages):return dict(eligible=True,input_upper_bound=20000,method='test_fixture_not_real_token_proof')
    def send(self,raw,remaining):return exchange(self.endpoint,method='POST',path='/api/chat',body=raw,timeout_seconds=remaining,response_limit_bytes=1048576)

if __name__=='__main__':
    cfg=decode(Path(sys.argv[1]).read_bytes());out=Path(cfg['out'])
    if cfg.get('barrier'):
        out.with_suffix('.ready').write_text('ready')
        deadline=time.monotonic()+10
        while not Path(cfg['barrier']).exists():
            if time.monotonic()>deadline:raise RuntimeError('test barrier timeout')
            time.sleep(.01)
    try:
        if cfg['mode'] in ('reserve','claim'):
            journal=Journal(Path(cfg['journal']),cfg['store_id'])
            result=journal.reserve(cfg['work']) if cfg['mode']=='reserve' else journal.claim(cfg['command'])
            result=dict(ok=True,claimed=result if cfg['mode']=='claim' else None)
        else:
            def hook(point):
                if point==cfg.get('crash'):os._exit(71)
            service=LocalService(settings(cfg['settings']),HTTPFake(cfg['endpoint']),_hook=hook)
            if cfg['mode']=='analyze':result=service.analyze(receipt=cfg['receipt'],store_key='local',input_path=cfg['input'])
            else:result=service.resume(receipt=cfg['receipt'])
        out.write_bytes(encode(result))
    except Exception as exc:
        out.write_bytes(encode(dict(ok=False,error=type(exc).__name__,message=str(exc))))
