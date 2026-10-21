"""Collect actual installed/wheel/source, runtime and protected-file evidence."""
import hashlib
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shlex
import sqlite3
import subprocess
import sys
import sysconfig
import tempfile
from datetime import datetime,timezone
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
S02=ROOT/'s02';REPORT=ROOT/'reports/s02-phase1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def command(name,argv,cwd,env):
    result=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True)
    log=REPORT/(name+'.log');log.write_text('$ '+shlex.join(map(str,argv))+'\ncwd='+str(cwd)+'\n'+result.stdout+result.stderr+f'\nexit_code={result.returncode}\n')
    return dict(name=name,command=list(map(str,argv)),cwd=str(cwd),exit_code=result.returncode,log=str(log))

def package_comparison(namespace,source,wheel):
    module=__import__(namespace);installed=Path(module.__file__).parent;entries=[]
    with ZipFile(wheel) as z:
        names={n for n in z.namelist() if n.startswith(namespace+'/') and not n.endswith('/')}
        source_names={namespace+'/'+str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        installed_names={namespace+'/'+str(p.relative_to(installed)) for p in installed.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        assert names==source_names==installed_names,(names-source_names,source_names-names,names-installed_names,installed_names-names)
        for name in sorted(names):
            relative=name.split('/',1)[1];a=sha(source/relative);b=sha(installed/relative);c=hashlib.sha256(z.read(name)).hexdigest()
            entries.append(dict(path=relative,source_sha256=a,installed_sha256=b,wheel_sha256=c,equal=a==b==c))
    assert all(x['equal'] for x in entries)
    return dict(version=importlib.metadata.version(namespace.replace('_','-')),import_path=str(module.__file__),wheel=str(wheel),wheel_sha256=sha(wheel),files=entries)

def main():
    global REPORT
    parser=argparse.ArgumentParser()
    parser.add_argument('--report-dir',type=Path,required=True)
    parser.add_argument('--version',required=True)
    args=parser.parse_args();REPORT=args.report_dir.resolve()
    wheel=S02/f'dist/dacn_s02-{args.version}-py3-none-any.whl'
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
    commands=[]
    with tempfile.TemporaryDirectory(prefix='dacn-s02-clean-install-') as cwd:
        verify=Path(cwd)/'venv'
        commands.append(command('clean-venv',[sys.executable,'-B','-m','venv','--without-pip',str(verify)],cwd,env))
        commands.append(command('clean-install-lock',[str(ROOT/'.tools/uv'),'pip','install','--python',str(verify/'bin/python'),'--no-index','--find-links',str(ROOT/'.tools/wheelhouse'),'--find-links',str(ROOT/'dist'),'--require-hashes','-r',str(S02/'requirements-dev.lock')],cwd,env))
        commands.append(command('clean-install-s02',[str(verify/'bin/python'),'-B','-m','pip','install','--no-index','--no-deps',str(wheel)],cwd,env))
        commands.append(command('clean-pip-check',[str(verify/'bin/python'),'-B','-m','pip','check'],cwd,env))
        probe="import json,sys,sqlite3,importlib.metadata as m,dacn_s01,dacn_s02;print(json.dumps({'python':sys.version,'sqlite':sqlite3.sqlite_version,'s01':dacn_s01.__file__,'s02':dacn_s02.__file__,'versions':{k:m.version(k) for k in ('dacn-s01','dacn-s02','simplejson','jsonschema','pytest')}}))"
        commands.append(command('clean-import-paths',[str(verify/'bin/python'),'-B','-c',probe],cwd,env))
        config=Path(cwd)/'s02.toml';config.write_text('state_dir="state"\n')
        commands.append(command('clean-cli-init',[str(verify/'bin/python'),'-B','-m','dacn_s02','--config',str(config),'init'],cwd,env))
        commands.append(command('installed-pip-check',[sys.executable,'-B','-m','pip','check'],cwd,env))
    assert all(c['exit_code']==0 for c in commands),commands
    packages=[package_comparison('dacn_s01',ROOT/'src/dacn_s01',ROOT/'dist/dacn_s01-0.1.0a6-py3-none-any.whl'),package_comparison('dacn_s02',S02/'src/dacn_s02',wheel)]
    from dacn_s02.storage_schema import DDL,DB_VERSION,APPLICATION_ID
    (REPORT/'DDL.sql').write_text('-- S02 structure 1; generated from the installed wheel, not executed against S01.\n'+';\n\n'.join(DDL.values())+';\n')
    pragma=[]
    for p in sorted((REPORT/'process-artifacts').rglob('*.sqlite3')):
        with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as c:
            pragma.append(dict(path=str(p),sha256=sha(p),user_version=c.execute('PRAGMA user_version').fetchone()[0],application_id=c.execute('PRAGMA application_id').fetchone()[0],journal_mode=c.execute('PRAGMA journal_mode').fetchone()[0],foreign_key_check=c.execute('PRAGMA foreign_key_check').fetchall()))
    manifest=dict(captured_at_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,executable=sys.executable,platform=platform.platform(),machine=platform.machine(),sqlite=sqlite3.sqlite_version,gil_enabled=sys._is_gil_enabled(),dependencies={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},locks={p.name:sha(p) for p in S02.glob('*.lock')},packages=packages,db_structure=dict(version=DB_VERSION,application_id=APPLICATION_ID,ddl_sha256=sha(REPORT/'DDL.sql'),observed_process_databases=pragma),commands=commands)
    (REPORT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    baseline=json.loads((REPORT/'baseline.json').read_bytes())
    protected=[dict(path=p,before_sha256=h,after_sha256=sha(Path(p)),unchanged=h==sha(Path(p))) for p,h in baseline['protected'].items()]
    assert all(v['unchanged'] for v in protected)
    (REPORT/'protected-after.json').write_text(json.dumps(dict(captured_at_utc=datetime.now(timezone.utc).isoformat(),files=protected,unchanged_count=len(protected),scope='Explicit fresh inventory from baseline.json; not all filesystem/dataset files'),indent=2)+'\n')
    print(json.dumps(dict(packages=[dict(name=p['version'],files=len(p['files']),wheel_sha256=p['wheel_sha256']) for p in packages],protected=len(protected),commands_passed=len(commands),process_databases=len(pragma))))

if __name__=='__main__':main()
