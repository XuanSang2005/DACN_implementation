"""Build/install and exercise the phase-3 package outside the source directory."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--audit-test', action='append', type=Path, default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reports = root/'reports/s01-phase3'
    tag = 'development' if args.development else 'final'
    log_path = reports/f'{tag}-results.txt'
    env = os.environ.copy()
    for key in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):
        env.pop(key, None)
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    records, evidence = [], []
    with tempfile.TemporaryDirectory(prefix='dacn-phase3-checks-') as cwd:
        commands = []
        if args.build:
            commands += [('build', [sys.executable,'-m','pip','wheel','--no-index','--no-deps','--no-build-isolation','--wheel-dir','dist','.'], str(root)),
                         ('install',[sys.executable,'-m','pip','install','--no-index','--no-deps','--force-reinstall','dist/dacn_s01-0.1.0a4-py3-none-any.whl'], str(root))]
        prefix = [sys.executable,'-B','-m','pytest','-c',str(root/'pyproject.toml'),'-s','-v','--tb=short','-p','no:cacheprovider']
        for backend in ('c','python'):
            commands.append((f'suite-{backend}', prefix+[str(root/('tests/phase3' if args.development else 'tests')),f'--encoder-backend={backend}'], cwd))
        if not args.development:
            commands.append(('pip-check',[sys.executable,'-B','-m','pip','check'],cwd))
            commands += [(f'audit-{i}',prefix+[str(path.resolve()),'--noconftest'],cwd) for i,path in enumerate(args.audit_test)]
        for name, command, working in commands:
            with log_path.open('a') as log:
                log.write(f'\n{name}\n$ {shlex.join(command)}\ncwd={working}\n'
                          'PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS unset; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTHONDONTWRITEBYTECODE=1\n')
                log.flush()
                completed = subprocess.run(command,cwd=working,env=env,capture_output=True,text=True)
                log.write(completed.stdout+completed.stderr+f'\nexit_code={completed.returncode}\n')
            records.append({'name':name,'command':command,'cwd':working,'exit_code':completed.returncode})
            for line in completed.stdout.splitlines():
                if 'PHASE3_EVIDENCE ' in line:
                    data, _ = json.JSONDecoder().raw_decode(line.split('PHASE3_EVIDENCE ',1)[1])
                    evidence.append({'suite':name,**data})
            print(f'{name}: exit_code={completed.returncode}',flush=True)
            if name in ('build','install') and completed.returncode:
                break
    (reports/f'{tag}-commands.json').write_text(json.dumps(records,indent=2)+'\n')
    (reports/f'{tag}-concurrency-fault-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return int(any(r['exit_code'] for r in records))


if __name__ == '__main__':
    raise SystemExit(main())
