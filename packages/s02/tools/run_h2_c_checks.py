"""Installed-wheel H2-C checks, sequential backends and durable test state.

Uses the unchanged E1 adapter/conftest. Never installs/resolves packages, retries
failed tests, changes caps, or deletes basetemp (including failed DB/journals).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from prepare_p2_tests import prepare, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--scope', choices=('focused','full'), default='focused')
    parser.add_argument('--group', choices=('all','fixed_point','merge','stress'), default='all')
    args = parser.parse_args()
    if args.scope=='full' and args.group!='all':
        parser.error('--group only selects focused checks')
    out = args.report_dir.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error('Output must be outside checkout')
    out.mkdir(parents=True, exist_ok=False)
    environment = json.loads(args.environment.read_text())
    workspace = out/'workspace'
    tests = prepare(workspace/'packages/s02/tests')
    config = tests.parent/'pyproject.toml'
    shutil.copyfile(ROOT/'packages/s02/pyproject.toml', config)
    env = os.environ.copy()
    for k in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):
        env.pop(k, None)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               DACN_LEGACY_PYTHON=environment['python']['legacy'],
               DACN_P1_PYTHON=environment['python']['p1'],
               DACN_BASELINE_HELPERS=environment['helpers'])
    inputs = (sorted(tests.glob('test_h2_c_*.py')) if args.group=='all'
              else [tests/f'test_h2_c_{args.group}.py']) if args.scope=='focused' else [tests]
    commands = []
    for backend in ('c','python'):
        cwd = out/backend
        cwd.mkdir()
        env['S02_TEST_EVIDENCE_DIR'] = str(cwd/'process-artifacts')
        argv = [sys.executable,'-B','-m','pytest','-c',str(config),*map(str,inputs),
                '-s','-v','--tb=short','-p','no:cacheprovider','--encoder-backend='+backend,
                '--basetemp='+str(cwd/'tmp'),'--junitxml='+str(cwd/'junit.xml')]
        start = time.time()
        with (cwd/'pytest.log').open('xb') as log:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        stats = [dict(s.attrib) for s in ET.parse(cwd/'junit.xml').getroot().iter('testsuite')] if (cwd/'junit.xml').exists() else []
        commands.append(dict(argv=argv,cwd=str(cwd),backend=backend,start_epoch=start,
                             elapsed_seconds=time.time()-start,exit_code=result.returncode,junit=stats,
                             environment={k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD',
                                          'DACN_LEGACY_PYTHON','DACN_P1_PYTHON','DACN_BASELINE_HELPERS','S02_TEST_EVIDENCE_DIR')}))
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        print(backend, result.returncode, stats, flush=True)
    inventory = {str(p.relative_to(out)):dict(size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                 for p in sorted(out.rglob('*')) if p.is_file() and not p.is_symlink()}
    (out/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    return int(any(c['exit_code'] for c in commands))


if __name__=='__main__':
    raise SystemExit(main())
