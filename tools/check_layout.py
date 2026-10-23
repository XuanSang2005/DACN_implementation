"""Read-only artifact checks plus synthetic CLI smoke outside the checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib
from uuid import uuid4

WORKSPACE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, required=True, help='Must not exist')
    args = parser.parse_args()
    report = args.report_dir.resolve()
    report.mkdir(parents=True, exist_ok=False)
    from dacn_s01.codec import parse_json
    from dacn_s01.schema_resource import read_schema_bytes
    from dacn_s02.local_io import settings
    from dacn_s02.errors import S02Error
    from dacn_s02.validation import shape
    import dacn_s01, dacn_s02
    assert all('site-packages' in Path(m.__file__).parts for m in (dacn_s01,dacn_s02))
    project = tomllib.loads((WORKSPACE / 'pyproject.toml').read_text())
    assert 'project' not in project and 'build-system' not in project
    assert (WORKSPACE / 'AGENTS.md').is_file()
    schema = read_schema_bytes()
    assert schema == (WORKSPACE / 'packages/s01/src/dacn_s01/schemas/input/1.0.0/system-input.schema.json').read_bytes()
    examples = []
    record_count = 0
    def walk(value):
        nonlocal record_count
        if type(value) is dict:
            if value.keys() == {'type','id','created_at','body'}:
                shape(value);record_count += 1
            for child in value.values(): walk(child)
        elif type(value) is list:
            for child in value: walk(child)
    for path in sorted((WORKSPACE / 'docs/examples').rglob('*.json')):
        value = parse_json(path.read_bytes())
        if path.parent.name == 's02': walk(value)
        examples.append(dict(path=str(path.relative_to(WORKSPACE)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assert record_count == 33
    commands, guards = [], []
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    with tempfile.TemporaryDirectory(prefix='dacn-layout-smoke-') as cwd:
        work = Path(cwd)
        def command(name, argv, expected=0):
            result = subprocess.run([sys.executable,'-B',*map(str,argv)],cwd=cwd,env=env,capture_output=True)
            full = [sys.executable,'-B',*map(str,argv)]
            (report / (name + '.log')).write_text('$ ' + shlex.join(full) + '\ncwd=' + cwd + '\n' +
                result.stdout.decode('utf-8',errors='backslashreplace') + result.stderr.decode('utf-8',errors='backslashreplace') + f'\nexit_code={result.returncode}\n')
            commands.append(dict(name=name,command=full,cwd=cwd,exit_code=result.returncode,expected_exit=expected))
            assert result.returncode == expected, (name,result.stdout,result.stderr)
            return result.stdout
        command('s01-init',['-m','dacn_s01','--state-dir',work/'s01-state','init'])
        output=command('s01-submit',['-m','dacn_s01','--state-dir',work/'s01-state','submit','--mode','create',
            '--input',WORKSPACE/'docs/examples/s01-local/synthetic-clinic.input.json','--receipt',work/'s01.receipt.json'])
        envelope=parse_json(output);assert envelope['status']=='validated'
        assert command('s01-lookup',['-m','dacn_s01','show-run','--receipt',work/'s01.receipt.json'])==output
        config=work/'s02.toml';config.write_text('state_dir="s02-state"\n[s01_stores]\nsynthetic="s01-state/s01.sqlite3"\n')
        command('s02-init',['-m','dacn_s02','--config',config,'init'])
        started=parse_json(command('s02-start',['-m','dacn_s02','--config',config,'start','--store-key','synthetic',
            '--s01-run-id',envelope['run']['run_id'],'--receipt',work/'s02.receipt.json']))
        assert started['status']=='completed'
        lookup=parse_json(command('s02-lookup',['-m','dacn_s02','--config',config,'show-command','--receipt',work/'s02.receipt.json']))
        assert lookup['result']['state']=='finalized'
        context=parse_json(command('s02-source-context',['-m','dacn_s02','--config',config,'show-record','--id',started['result']['source_context_id']]))
        assert context['result']['record']['body']['snapshot_id']==envelope['snapshot']['snapshot_id']
        # Test the unchanged guard at exact roots AND fresh descendants. First
        # check the pure path boundary, so CLI cannot write if that guard regresses.
        for name,root in [('workspace',WORKSPACE),('s01',WORKSPACE/'packages/s01'),('s02',WORKSPACE/'packages/s02')]:
            for suffix in ('root','child'):
                target=root if suffix=='root' else root/('guard-probe-'+str(uuid4()))
                guard_config=work/'guard.toml';guard_config.write_text('state_dir='+json.dumps(str(target))+'\n')
                try: settings(guard_config)
                except S02Error as exc: assert exc.error['code']=='PERSISTENCE_FAILED'
                else: raise AssertionError(('Guard accepted write target',target))
                result=parse_json(command('guard-'+name+'-'+suffix,['-m','dacn_s02','--config',guard_config,'init'],3))
                assert result['status']=='failed' and not (target/'s02.sqlite3').exists()
                if suffix=='child': assert not target.exists()
                guards.append(dict(target=str(target),rejected=True,state_not_created=True))
        command('schema-materializer',[WORKSPACE/'packages/s02/tools/materialize_schema.py','--check'])
        existing=work/'existing';existing.mkdir();sentinel=existing/'sentinel';sentinel.write_bytes(b'keep')
        for name,arguments in [
            ('runner',[WORKSPACE/'tools/run_checks.py','--package','all','--report-dir',existing]),
            ('builder',[WORKSPACE/'tools/build_packages.py','--package','all','--output-dir',existing]),
            ('collector',[WORKSPACE/'tools/collect_evidence.py','--package','all','--wheel-dir',existing,'--report-dir',existing]),
            ('schema-output',[WORKSPACE/'packages/s02/tools/materialize_schema.py','--output',sentinel])]:
            command('no-overwrite-'+name,arguments,1)
            assert list(existing.iterdir())==[sentinel] and sentinel.read_bytes()==b'keep'
    guides=[WORKSPACE/p for p in ('AGENTS.md','README.md','docs/README.md','docs/s01/README.md','docs/s02/README.md',
            'reports/README.md','s02/README.md','packages/s01/tools/legacy/README.md','packages/s02/tools/legacy/README.md')]
    links=[]
    for guide in guides:
        for target in re.findall(r'\]\(([^)]+)\)',guide.read_text()):
            if '://' in target or target.startswith('#'): continue
            location=(guide.parent/target.split('#',1)[0]).resolve()
            assert location.exists(),(guide,target)
            links.append(dict(guide=str(guide.relative_to(WORKSPACE)),target=target,resolves=True))
    result=dict(commands=commands,guard_checks=guards,examples=examples,s02_example_record_shapes=record_count,
                source_schema_sha256=hashlib.sha256(schema).hexdigest(),guide_links=links,
                scope='Synthetic CLI smoke and structural artifact checks; no business/LLM/renderer acceptance')
    (report/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(commands=len(commands),guard_checks=len(guards),examples=len(examples),guide_links=len(links),passed=True)))


if __name__=='__main__':
    main()
