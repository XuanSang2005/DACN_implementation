"""Independent OS process B API worker; real engine faults, no validator mocks."""
import json,os,sys,time
from pathlib import Path
from process_worker import observe_backend
backend,counts=observe_backend()
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.local_io import settings
from dacn_s02.h3_history import ReviewTrustContext
from dacn_s02.h3_policy import SemanticTrustContext
from dacn_s02.h3_review_io import LocalSyntheticCheckpointAuthority
from dacn_s02.h3_service import HistoryService


def main():
    spec=json.loads(Path(sys.argv[1]).read_text());phase=[None];fired=[False]
    def repo_hook(point,c):
        if point!=spec.get('repo_point') or phase[0]!=spec.get('phase') or fired[0]:return
        fired[0]=True;print('H3_FAULT '+json.dumps(dict(pid=os.getpid(),phase=phase[0],point=point,action=spec['action'])),flush=True)
        if spec['action']=='kill':os._exit(71)
        if spec['action']=='unknown':Path(spec['db']).rename(spec['db']+'.unavailable')
        raise OSError('Synthetic B rollback/lost ACK/outcome unknown')
    def hook(point):
        if point=='before_prepare':phase[0]='prepare'
        if point=='before_seal':phase[0]='seal'
        if point=='before_finalize':phase[0]='finalize'
        if point==spec.get('service_kill'):os._exit(71)
        if point==spec.get('barrier_point'):
            root=Path(spec['barrier']);root.mkdir(exist_ok=True);(root/str(os.getpid())).write_text(point)
            deadline=time.monotonic()+20
            while len(list(root.iterdir()))<2:
                if time.monotonic()>deadline:raise RuntimeError('B process barrier timed out')
                time.sleep(.02)
    authority=LocalSyntheticCheckpointAuthority(spec['authority'],SemanticTrustContext(**spec['authority_trust'])) if spec.get('authority') else None
    service=HistoryService(settings(spec['config']),historical_reviews=ReviewTrustContext(**spec['review_trust']),authority=authority,_hook=hook,_repository_options={'_hook':repo_hook})
    try:
        if spec['mode']=='prepare':
            work=json.loads(Path(spec['work']).read_text());work['analysis']=Path(work['analysis']).read_bytes()
            result=service.prepare(spec['command'],spec['parent'],receipt=spec['receipt'],**work)
        elif spec['mode']=='report':result=service.report(spec['command'])
        else:result=service.resume(spec['command'],receipt=spec['receipt'])
        print('H3_RESULT '+encode(result).decode('ascii'),flush=True)
        return 5 if result['status']=='not_prepared' else 2 if result['status'] in ('blocked','stale','rejected') else 0
    except S02Error as exc:
        print('H3_ERROR '+encode(exc.error).decode('ascii'),flush=True);return 3 if exc.error['stage']=='persistence' else 2
    finally:print('H3_ENCODERS '+json.dumps(dict(pid=os.getpid(),backend=backend,calls=counts)),flush=True)


if __name__=='__main__':raise SystemExit(main())
