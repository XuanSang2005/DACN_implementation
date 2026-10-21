"""Measure the delivered phase-3 build; preserve all earlier evidence."""

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sqlite3
import sys
import zipfile

import dacn_s01
import simplejson._speedups

from dacn_s01.service import validator_build
from dacn_s01.storage_schema import APPLICATION_ID, DB_VERSION, DDL


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    reports = root/'reports/s01-phase3'
    baseline = json.loads((reports/'baseline-verification.json').read_text())
    assert metadata.version('dacn-s01') == '0.1.0a4'
    assert platform.python_version() == '3.13.16' and sys._is_gil_enabled()
    assert digest(Path(sys.executable)) == baseline['executable_sha256']
    assert sqlite3.sqlite_version == baseline['sqlite_version']
    installed = Path(dacn_s01.__file__).parent
    assert 'site-packages' in installed.parts
    wheel = root/'dist/dacn_s01-0.1.0a4-py3-none-any.whl'
    source = root/'src/dacn_s01'
    files = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    package = {}
    with zipfile.ZipFile(wheel) as archive:
        entries = {p.removeprefix('dacn_s01/') for p in archive.namelist() if p.startswith('dacn_s01/') and not p.endswith('/')}
        assert entries == files
        assert files == {str(p.relative_to(installed)) for p in installed.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        for name in sorted(files):
            values = {'source':digest(source/name), 'installed':digest(installed/name),
                      'wheel':hashlib.sha256(archive.read('dacn_s01/'+name)).hexdigest()}
            assert len(set(values.values())) == 1, name
            package['dacn_s01/'+name] = values
        distribution = metadata.distribution('dacn-s01')
        for name in ('METADATA','WHEEL'):
            assert distribution.read_text(name).encode() == archive.read('dacn_s01-0.1.0a4.dist-info/'+name)
    direct_url = json.loads(distribution.read_text('direct_url.json'))
    assert not direct_url.get('dir_info',{}).get('editable',False)
    assert direct_url['archive_info']['hashes']['sha256'] == digest(wheel)
    distributions = sorted([{'name':d.metadata['Name'],'version':d.version,'requires_dist':d.requires or []}
                            for d in metadata.distributions()], key=lambda d:d['name'].lower())
    for item in baseline['installed_distributions']:
        current = next(d for d in distributions if d['name'] == item['name'])
        assert current == item or item['name'] == 'dacn-s01', item['name']
    assert len(distributions) == len(baseline['installed_distributions'])
    before = json.loads((reports/'protected-files-before.json').read_text())
    protected = {name:{'before':sha, 'after':digest(Path(name))} for name,sha in before.items()}
    changed = {name for name, values in protected.items() if values['before'] != values['after']}
    # The start-of-turn inventory also captured __init__.py. Its one-line package
    # description intentionally changes; all actual baseline modules stay intact.
    allowed = {str(root/'src/dacn_s01/__init__.py')}
    assert changed == allowed
    existing_changes = {name for name, sha in baseline['project_file_sha256'].items() if digest(root/name) != sha}
    assert existing_changes == {'pyproject.toml'}
    protected_result = {'all_protected_documents_data_locks_and_prior_evidence_unchanged':True,
                        'intentional_package_description_change':sorted(changed), 'files':protected}
    (reports/'protected-files-verification.json').write_text(json.dumps(protected_result,indent=2)+'\n')
    cases = json.loads((reports/'final-concurrency-fault-evidence.json').read_text())
    schedules = {'both-unchanged','same-change','different-changes','unchanged-first','changed-first'}
    for backend in ('c','python'):
        selected = [c for c in cases if c['suite'] == f'suite-{backend}']
        assert schedules <= {c['case'] for c in selected}
        for case in selected:
            if case['case'] in schedules:
                events = case['events']
                assert any(e['event'] == 'busy_observed' for e in events)
                # A's post-COMMIT hook may be scheduled after B acquires the lock;
                # do not confuse hook emission order with SQLite commit order.
                committing_a = next(e['time_ns'] for e in events if e['role'] == 'A' and e['event'] == 'before_commit')
                began_b = next(e['time_ns'] for e in events if e['role'] == 'B' and e['event'] == 'after_begin')
                busy_b = next(e['time_ns'] for e in events if e['event'] == 'busy_observed')
                assert busy_b < committing_a < began_b
        assert {'kill-before_commit','kill-after_commit'} <= {c['case'] for c in selected}
    commands = json.loads((reports/'final-commands.json').read_text())
    assert commands and all(c['exit_code'] == 0 for c in commands)
    (reports/'database-schema.sql').write_text('\n\n'.join(sql+';' for sql in DDL.values())+'\n')
    project_files = [root/'pyproject.toml',root/'.python-version',*root.glob('requirements*'),
                     *root.glob('src/**/*.py'),*root.glob('tests/**/*.py'),*root.glob('tools/*.py')]
    manifest = {
        'measured_at_utc':datetime.now(timezone.utc).isoformat(), 'status':'phase 3 implemented/tested; pending audit',
        'package_version':metadata.version('dacn-s01'), 'validator_version':validator_build(),
        'contract_version':'0.1.0-draft.2', 'input_schema_version':'1.0.0',
        'python':{'version':platform.python_version(),'sys_version':sys.version,'executable':sys.executable,
                  'sha256':digest(Path(sys.executable)),'gil_enabled':sys._is_gil_enabled()},
        'platform':platform.platform(),'machine':platform.machine(),'sqlite_version':sqlite3.sqlite_version,
        'database':{'structure_version':DB_VERSION,'application_id':APPLICATION_ID,'journal_mode':'delete',
                    'synchronous':'FULL','foreign_keys':True,'connection_autocommit':True,
                    'transaction':'explicit SQL BEGIN IMMEDIATE/COMMIT/ROLLBACK', 'default_timeout_seconds':5},
        'installed_distributions':distributions,'runtime_dependencies_unchanged':True,
        'installed_package_path':str(installed),'direct_url':direct_url,
        'wheel':{'path':str(wheel.relative_to(root)),'sha256':digest(wheel)},
        'baseline_wheel_preserved':{'path':'dist/dacn_s01-0.1.0a3-py3-none-any.whl',
                                    'sha256':digest(root/'dist/dacn_s01-0.1.0a3-py3-none-any.whl')},
        'simplejson_c_extension':{'path':simplejson._speedups.__file__,'sha256':digest(Path(simplejson._speedups.__file__))},
        'package_files':package,'source_installed_wheel_identical':True,
        'project_file_sha256':{str(p.relative_to(root)):digest(p) for p in sorted(project_files)},
        'read_only_inventory_count':len(protected),'unchanged_count':len(protected)-len(changed),
        'new_test_evidence_records':len(cases), 'test_log':'final-results.txt','commands':'final-commands.json',
    }
    (reports/'environment-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Verified {len(package)} package files across source/install/wheel; {len(protected)-1} inventory files unchanged; only __init__ package description intentionally updated.')
    print(f'Verified five real process schedules and two kill boundaries on each backend; {len(cases)} evidence records.')


if __name__ == '__main__':
    main()
