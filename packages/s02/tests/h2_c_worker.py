"""Four-process H2-C barrier, with unmodified production Budget/publication.

Barrier is before T3, outside SQLite transactions. No cached seal or replaced
validation; every worker reopens the DB and reads its external authority file.
"""
import json
import os
from pathlib import Path
import sys
import time

from process_worker import observe_backend
backend, counts = observe_backend()
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h1_service import exit_code
from dacn_s02.h2_service import H2Service
from dacn_s02.h2_authority import LocalSyntheticAuthority
from dacn_s02.repository import Repository


def main():
    input_path = Path(sys.argv[1])
    spec = json.loads(input_path.read_text())

    def phase(point):
        with input_path.with_suffix('.phases.jsonl').open('a') as log:
            log.write(json.dumps(dict(pid=os.getpid(),point=point,monotonic=time.monotonic()))+'\n')

    def hook(point):
        phase(point)
        if point != spec.get('barrier_point'):
            return
        barrier = Path(spec['barrier'])
        barrier.mkdir(exist_ok=True)
        (barrier/str(os.getpid())).write_text(point)
        deadline = time.monotonic()+20
        while len(list(barrier.iterdir())) < 4:
            if time.monotonic() > deadline:
                raise RuntimeError('Four-process barrier timed out')
            time.sleep(.02)

    authority = LocalSyntheticAuthority(spec['authority'], spec['authority_sha256']) if spec.get('authority') else None
    service = H2Service(Repository(spec['db']), authority=authority, _hook=hook)
    try:
        phase('resume_enter')
        result = service.resume(spec['command'], store_id=spec['store_id'])
        phase('resume_return')
        print('H2_C_RESULT '+encode(result).decode(), flush=True)
        return exit_code(result)
    except S02Error as exc:
        phase('resume_error')
        print('H2_C_ERROR '+encode(exc.error).decode(), flush=True)
        return 3 if exc.error['stage']=='persistence' else 2
    finally:
        print('H2_C_ENCODERS '+json.dumps(dict(pid=os.getpid(), backend=backend, calls=counts)), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
