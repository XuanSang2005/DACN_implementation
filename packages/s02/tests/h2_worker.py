"""Real process death/lost-ACK harness using the public private fault hooks.

No validation gate or production function is monkeypatched. Inputs/stores are
synthetic and the worker is never imported by production.
"""
import json
import os
from pathlib import Path
import sys
import time

from process_worker import observe_backend
backend,counts=observe_backend()
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.repository import Repository
from dacn_s02.h1_service import exit_code
from dacn_s02.h2_service import H2Service
from dacn_s02.h2_authority import LocalSyntheticAuthority
from dacn_s02.local_io import settings,write_receipt


def main():
    spec=json.loads(Path(sys.argv[1]).read_text());phase=[None];fired=[False]
    def repo_hook(point,connection):
        if point!=spec.get('repo_point') or phase[0]!=spec.get('phase') or fired[0]:return
        fired[0]=True;print('H2_FAULT '+json.dumps(dict(phase=phase[0],point=point,action=spec['action'])),flush=True)
        if spec['action']=='kill':os._exit(71)
        if spec['action']=='unknown':Path(spec['db']).rename(spec['db']+'.unavailable')
        raise OSError('SYNTHETIC lost ACK after COMMIT')
    def hook(point):
        if point=='before_prepare':phase[0]='prepare'
        if point=='before_seal':phase[0]='seal'
        if point=='before_finalize':phase[0]='finalize'
        if point==spec.get('service_kill'):os._exit(71)
        if point==spec.get('barrier_point'):
            barrier=Path(spec['barrier']);barrier.mkdir(exist_ok=True)
            (barrier/str(os.getpid())).write_text(point)
            deadline=time.monotonic()+20
            while len(list(barrier.iterdir()))<2:
                if time.monotonic()>deadline:raise RuntimeError('Worker barrier timed out')
                time.sleep(.02)
    repo=Repository(spec['db'],_hook=repo_hook)
    authority=LocalSyntheticAuthority(spec['authority'],spec['authority_sha256']) if spec.get('authority') else None
    service=H2Service(repo,authority=authority,_hook=hook)
    try:
        if spec['mode']=='receipt_prepare':
            if spec.get('receipt_kill')=='before':os._exit(71)
            write_receipt(settings(spec['config']),spec['receipt'],spec['command'],store_id=spec['store_id'])
            if spec.get('receipt_kill')=='after':os._exit(71)
        if spec['mode'] in ('prepare','receipt_prepare'):
            work=json.loads(Path(spec['work']).read_text())
            for lane in ('candidate','analysis'):
                work[lane]=Path(work[lane]).read_bytes() if work[lane] else None
            if spec.get('barrier_point')=='prepare':hook('prepare')
            output=service.prepare(spec['command'],spec['parent'],store_id=spec['store_id'],**work)
        else:output=service.resume(spec['command'],store_id=spec['store_id'])
        print('H2_RESULT '+encode(output).decode('ascii'),flush=True)
        return exit_code(output)
    except S02Error as exc:
        print('H2_ERROR '+encode(exc.error).decode('ascii'),flush=True)
        return 3 if exc.error['stage']=='persistence' else 2
    finally:
        print('H2_ENCODERS '+json.dumps(dict(backend=backend,calls=counts)),flush=True)


if __name__=='__main__':raise SystemExit(main())
