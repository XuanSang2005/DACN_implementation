"""Run installed-package checks; each package/backend gets its own process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

WORKSPACE = Path(__file__).resolve().parents[1]


def main(*, fixed_package=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    if fixed_package is None:
        parser.add_argument('--package', choices=('s01', 's02', 'all'), required=True)
    else:
        # Package entry points have no public selector to override.
        if fixed_package not in ('s01', 's02'):
            raise ValueError('Invalid fixed package')
        parser.set_defaults(package=fixed_package)
    parser.add_argument('--report-dir', type=Path, required=True, help='Must not exist')
    parser.add_argument('--audit-file', type=Path, action='append', default=[])
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    if (args.audit_file or args.audit_only) and args.package != 's02':
        parser.error('External S02 audit helpers require --package s02')
    if args.audit_only and not args.audit_file:
        parser.error('--audit-only requires --audit-file')
    audits = [p.resolve(strict=True) for p in args.audit_file]
    report = args.report_dir.resolve()
    report.mkdir(parents=True, exist_ok=False)  # Never replace prior evidence.
    env = os.environ.copy()
    for name in ('PYTHONPATH', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
        env.pop(name, None)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    packages = ('s01', 's02') if args.package == 'all' else (args.package,)
    jobs = [(name, None) for name in packages] if not args.audit_only else []
    jobs += [('s02', p) for p in audits]
    commands, observations = [], []
    for package, audit in jobs:
        package_root = WORKSPACE / 'packages' / package
        label = package if audit is None else 'audit-' + str(audits.index(audit) + 1)
        for backend in ('c', 'python'):
            name = label + '-' + backend
            audit_hash = hashlib.sha256(audit.read_bytes()).hexdigest() if audit else None
            with tempfile.TemporaryDirectory(prefix='dacn-installed-checks-') as cwd:
                prefix = [sys.executable, '-B', '-m', 'pytest']
                if audit:
                    # Only locate test helpers at the new path. The external
                    # module and all its assertions execute unchanged.
                    bootstrap = 'import sys,pytest;sys.path.insert(0,sys.argv.pop(1));raise SystemExit(pytest.main(sys.argv[1:]))'
                    prefix = [sys.executable, '-B', '-c', bootstrap, str(package_root / 'tests'), '-p', 'conftest']
                argv = prefix + ['-c', str(package_root / 'pyproject.toml'), str(audit or package_root / 'tests'),
                                 '-s', '-v', '--tb=short', '-p', 'no:cacheprovider', '--encoder-backend=' + backend,
                                 '--basetemp=' + str(Path(cwd) / 'tmp'), '--junitxml=' + str(report / (name + '.xml'))]
                env['S02_TEST_EVIDENCE_DIR'] = str(report / 'process-artifacts' / backend)
                result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
                (report / (name + '.log')).write_text('$ ' + shlex.join(argv) + '\ncwd=' + cwd +
                    '\nPYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS unset; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTHONDONTWRITEBYTECODE=1\n' +
                    result.stdout + result.stderr + f'\nexit_code={result.returncode}\n')
                if audit:
                    assert hashlib.sha256(audit.read_bytes()).hexdigest() == audit_hash
                    for db in (Path(cwd) / 'tmp').rglob('*.sqlite3'):
                        target = report / (name + '-databases') / db.relative_to(Path(cwd) / 'tmp')
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(db, target)
                junit = report / (name + '.xml')
                stats = [dict(s.attrib) for s in ET.parse(junit).getroot().iter('testsuite')] if junit.exists() else []
                commands.append(dict(name=name,package=package,command=argv,cwd=cwd,exit_code=result.returncode,
                                     junit=stats,audit_file=str(audit) if audit else None,audit_sha256=audit_hash))
                for line in result.stdout.splitlines():
                    for marker in ('S02_EVIDENCE ', 'PHASE3_EVIDENCE ', 'PHASE4_EVIDENCE ', 'PHASE4_ENCODERS '):
                        if marker in line:
                            data, _ = json.JSONDecoder().raw_decode(line.split(marker, 1)[1])
                            observations.append(dict(suite=name, marker=marker.strip(), data=data))
                    if line.startswith(('S02_ENCODERS', 'Observed real encoder factory calls')):
                        observations.append(dict(suite=name, backend_instrumentation=line))
                print(name, 'exit', result.returncode, flush=True)
    (report / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    (report / 'observations.json').write_text(json.dumps(observations, indent=2) + '\n')
    return int(any(c['exit_code'] for c in commands))


if __name__ == '__main__':
    raise SystemExit(main())
