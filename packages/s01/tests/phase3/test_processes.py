"""Two actual processes/connections, pipe synchronization, deadlines, no sleeps."""

import base64
from copy import deepcopy
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import time

import pytest

from dacn_s01.codec import serialize_json
from dacn_s01.repository import Repository
from dacn_s01.service import Service

CREATE = {'mode':'create', 'spec_id':None, 'base_revision':None}


class Worker:
    def __init__(self, config):
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        self.proc = subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('process_worker.py'))],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.proc.stdin.write(json.dumps(config).encode()+b'\n'); self.proc.stdin.flush()
        self.buffer = b''
        self.events = []
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)

    def until(self, event):
        deadline = time.monotonic()+20
        while True:
            while b'\n' not in self.buffer:
                remaining = deadline-time.monotonic()
                assert remaining > 0 and self.selector.select(remaining), 'worker event deadline exceeded'
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                assert chunk, f'worker exited early: {self.proc.stderr.read().decode()}'
                self.buffer += chunk
            line, self.buffer = self.buffer.split(b'\n', 1)
            message = json.loads(line)
            self.events.append({k:v for k,v in message.items() if k != 'envelope'})
            if message['event'] == event:
                return message

    def release(self):
        self.proc.stdin.write(b'continue\n'); self.proc.stdin.flush()

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=10)
        self.selector.close()
        for stream in (self.proc.stdin,self.proc.stdout,self.proc.stderr): stream.close()


def config(repository, payload, context, backend, role, **options):
    return {'database':str(repository.path), 'raw':base64.b64encode(serialize_json(payload)).decode(),
            'request_json':serialize_json(context).decode(), 'backend':backend, 'role':role, 'run_id':'process-'+role, **options}


def state(repository):
    with sqlite3.connect(repository.path) as connection:
        return {'runs':connection.execute('SELECT count(*) FROM runs').fetchone()[0],
                'sources':connection.execute('SELECT count(*) FROM sources').fetchone()[0],
                'snapshots':connection.execute('SELECT count(*) FROM snapshots').fetchone()[0],
                'heads':[list(row) for row in connection.execute('SELECT s.spec_id,p.revision FROM specs s JOIN snapshots p ON s.head_snapshot_id=p.snapshot_id')]}


@pytest.mark.parametrize('case,a_changed,b_changed,same,expected', [
    ('both-unchanged',False,False,True,('unchanged','unchanged',1)),
    ('same-change',True,True,True,('new_revision','conflict',2)),
    ('different-changes',True,True,False,('new_revision','conflict',2)),
    ('unchanged-first',False,True,False,('unchanged','new_revision',2)),
    ('changed-first',True,False,False,('new_revision','conflict',2)),
])
def test_five_real_process_schedules(payload, repository, pytestconfig, case, a_changed, b_changed, same, expected):
    seed = Service(repository).submit(serialize_json(payload), CREATE)['snapshot']
    context = {'mode':'update','spec_id':seed['spec_id'],'base_revision':1}
    a_input, b_input = deepcopy(payload), deepcopy(payload)
    if a_changed: a_input['title'] = 'P'
    if b_changed: b_input['title'] = 'P' if same else 'Q'
    backend = pytestconfig.getoption('--encoder-backend')
    a = Worker(config(repository,a_input,context,backend,'A',stop_at='after_begin'))
    b = None
    try:
        a.until('after_begin')  # A holds RESERVED writer lock and waits on IPC.
        b = Worker(config(repository,b_input,context,backend,'B',probe_busy=True))
        b.until('busy_observed')  # SQLite actually refused B's BEGIN on its own connection.
        b.until('sql_begin_attempt')  # B now enters its service transaction on that connection.
        a.release()
        outputs = [a.until('result'), b.until('result')]
        for worker in (a,b): assert worker.proc.wait(timeout=10) == 0
        for output, kind in zip(outputs, expected[:2]):
            envelope = output['envelope']
            assert output['encoder_calls'][backend] > 0
            assert output['encoder_calls']['python' if backend == 'c' else 'c'] == 0
            if kind == 'conflict':
                assert envelope['status'] == 'rejected' and envelope['snapshot'] is None
                assert [e['code'] for e in envelope['run']['validation']['errors']] == ['REVISION_CONFLICT']
            else:
                assert envelope['status'] == 'validated' and envelope['result_kind'] == kind
                if kind == 'unchanged': assert envelope['snapshot'] == seed
        final = state(repository)
        assert final['runs'] == final['sources'] == 3 and final['snapshots'] == expected[2]
        assert Repository(repository.path).get_head(seed['spec_id'])['revision'] == expected[2]
        print('PHASE3_EVIDENCE '+json.dumps({'case':case,'kind':'two real processes; actual SQLITE_BUSY probe',
            'backend':backend,'events':sorted(a.events+b.events,key=lambda e:e['time_ns']),'final_state':final}))
    finally:
        a.close()
        if b: b.close()


@pytest.mark.parametrize('point,committed', [('before_commit',False),('after_commit',True)])
def test_kill_process_at_synchronized_commit_boundary(payload, repository, pytestconfig, point, committed):
    backend = pytestconfig.getoption('--encoder-backend')
    worker = Worker(config(repository,payload,CREATE,backend,'kill',stop_at=point))
    try:
        worker.until(point)
        worker.proc.kill()
        returncode = worker.proc.wait(timeout=10)
        result = Repository(repository.path).get_run('process-kill')
        assert (result is not None) is committed
        final = state(repository)
        assert final['runs'] == final['sources'] == final['snapshots'] == int(committed)
        if result is not None:
            assert result['status'] == 'validated'
            assert repository.get_source(result['run']['source']['source_id']) == serialize_json(payload)
        print('PHASE3_EVIDENCE '+json.dumps({'case':'kill-'+point,'kind':'actual process kill', 'backend':backend,
            'returncode':returncode,'events':worker.events,'final_state':final}))
    finally:
        worker.close()
