"""H2-C synthetic source and projections; expected outcomes live in tests.

No policy/closure/impact function is used to construct expectations. The six
V families each own one action, one responsibility and three mapping rows.
U has an unknown permission; NFR/constraint remain in the full inventory.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from h1_fixtures import Case, input_data
from h2_checkpoint_fixtures import ScopedCase
from test_h2_checkpoint_processes import spec, final
from dacn_s02.codec_boundary import encode, decode
from dacn_s02.h2_service import H2Service
from dacn_s02.repository import Repository


class ManyCase(ScopedCase):
    def __init__(self, path, independent=6):
        source = input_data()
        source['title'] = f'H2-C SYNTHETIC U and {independent} independent V families'
        source['functional_requirements'][0]['text'] = 'Synthetic cancellation U; who may cancel is unknown'
        source['functional_requirements'] = [source['functional_requirements'][0]] + [
            dict(id=f'V{i}', text=f'Read independent synthetic register {i}',
                 priority=None, acceptance_criteria=[f'Retain {i} identity', f'Retain {i} status'])
            for i in range(1, independent+1)]
        Case.__init__(self, path, source)
        self.service = H2Service(self.repo)
        self.last = None
        self.authorities = {}
        self.checkpoints = []

    def unit(self, number):
        return self.units[f'/functional_requirements/{number}']

    def by_source(self, collection, number):
        ptr = f'/functional_requirements/{number}'
        return next(x for x in self.last['result']['model']['body'][collection]
                    if x['trace']['source_refs'][0]['input_pointer'] == ptr)

    def handle(self, collection, number):
        identity = self.by_source(collection, number)['id']
        return next(h for h, row in self.aliases().items() if row['id'] == identity)

    def unit_work(self, step, number, *, change=None, **options):
        ptr = f'/functional_requirements/{number}'

        def projection(candidate, analysis):
            if candidate:
                p = candidate['proposals']
                if step == 2:
                    p['actions'][0].update(name=f'Read V{number}', trace=self.tr(ptr))
                if step == 3:
                    p['components'][0].update(name=f'Component V{number}', trace=self.tr(ptr))
                    p['responsibilities'][0].update(
                        statement=f'Read V{number}', trace=self.tr(ptr),
                        action_ids=[dict(base_handle=self.handle('actions', number))])
                if step == 4:
                    for row in p['mappings']:
                        for part in row['parts']:
                            part.update(action_ids=[dict(base_handle=self.handle('actions', number))],
                                        primary_responsibility_ids=[dict(base_handle=self.handle('responsibilities', number))])
            if change:
                change(candidate, analysis)

        return self.work(step, units=[self.unit(number)], change=projection, **options)

    def reopen(self, command):
        self.repo = Repository(self.repo.path)
        self.parent = command
        self.refresh()

    def execute(self, work, authority, label):
        command = str(uuid4())
        H2Service(Repository(self.repo.path), authority=authority).prepare(
            command, self.parent, store_id=self.store_id, **work)
        result = finish_worker(self, spec(self, command, work, authority))()
        self.reopen(command)
        self.observe(command, label)
        return result

    def observe(self, command, label):
        view, plan = final(self, command)
        status=view['command']['run']['body']['status']
        row = dict(label=label, command_id=command, status=status,
                   result_pair=None if status=='stale' else plan['batch']['head'],
                   planned_pair=plan['batch']['head'], observed_current_pair=view['current_head'],
                   candidate_outcome=plan['candidate_outcome'],
                   stages={p: self.meta['progress_by_unit'][u]['work_completed_through'] for p, u in self.units.items()},
                   guards={q['body']['issue_key']:q['body']['status'] for q in self.last['result']['issues']
                           if q['body']['issue_key'] in self.meta['guards']})
        self.checkpoints.append(row)
        (self.path/'checkpoint-trace.json').write_bytes(encode(self.checkpoints))
        print('H2_C_CHECKPOINT ' + encode(row).decode(), flush=True)
        return view, plan


def finish_worker(case, value):
    """Start immediately; callers start all four before joining any of them."""
    evidence = Path(os.environ.get('S02_TEST_EVIDENCE_DIR', str(case.path/'process-evidence')))
    evidence.mkdir(parents=True, exist_ok=True)
    token = str(uuid4())
    path = evidence/(token+'.input.json')
    path.write_text(json.dumps(value))
    argv = [sys.executable, '-B', str(Path(__file__).with_name('h2_c_worker.py')), str(path)]
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    p = subprocess.Popen(argv, cwd=case.path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def finish():
        try:
            out, err = p.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
            raise
        finally:
            (evidence/(token+'.command.json')).write_text(json.dumps(dict(
                argv=argv, cwd=str(case.path), pid=p.pid, exit_code=p.returncode)))
            if 'out' in locals():
                (evidence/(token+'.stdout.log')).write_bytes(out)
                (evidence/(token+'.stderr.log')).write_bytes(err)
        assert p.returncode in (0, 2), (p.returncode, out, err)
        lines = out.decode().splitlines()
        counts = json.loads(next(s.removeprefix('H2_C_ENCODERS ') for s in lines if s.startswith('H2_C_ENCODERS ')))
        backend = os.environ.get('S02_TEST_CODEC_BACKEND', 'c')
        assert counts['pid'] == p.pid and counts['backend'] == backend
        assert counts['calls'][backend] > 0 and counts['calls']['c' if backend == 'python' else 'python'] == 0
        result = decode(next(s.removeprefix('H2_C_RESULT ') for s in lines if s.startswith('H2_C_RESULT ')).encode())
        return result

    finish.pid = p.pid
    return finish


def join_workers(workers):
    """Collect ALL worker diagnostics even when the first worker failed."""
    results=[]
    failures=[]
    for worker in workers:
        try:results.append(worker())
        except Exception as exc:failures.append((worker.pid,repr(exc)))
    assert not failures,failures
    return results
