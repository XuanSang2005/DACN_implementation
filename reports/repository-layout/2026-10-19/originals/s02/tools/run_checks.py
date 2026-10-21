"""Installed-package verification outside checkout; logs commands and outcomes."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--suite',choices=('s01','s02','audit'),required=True)
    parser.add_argument('--report-dir',type=Path,required=True)
    parser.add_argument('--audit-file',type=Path)
    args=parser.parse_args();s02=Path(__file__).resolve().parents[1];root=s02.parent
    report=args.report_dir.resolve();report.mkdir(parents=True,exist_ok=True);records=[];observations=[]
    if args.suite=='audit' and args.audit_file is None: parser.error('--audit-file required')
    env=os.environ.copy()
    for name in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(name,None)
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(prefix='dacn-s02-installed-checks-') as cwd:
        for backend in ('c','python'):
            tree=root if args.suite=='s01' else s02
            command=[sys.executable,'-B','-m','pytest','-c',str(tree/'pyproject.toml'),str(tree/'tests'),'-s','-v','--tb=short','-p','no:cacheprovider','--encoder-backend='+backend]
            if args.suite=='audit':
                # Load only the test instrumentation/helpers, never production src.
                bootstrap="import sys,pytest;sys.path.insert(0,sys.argv.pop(1));raise SystemExit(pytest.main(sys.argv[1:]))"
                command=[sys.executable,'-B','-c',bootstrap,str(s02/'tests'),'-p','conftest','-c',str(s02/'pyproject.toml'),str(args.audit_file.resolve()),'-s','-v','--tb=short','-p','no:cacheprovider','--encoder-backend='+backend]
            command+=['--junitxml='+str(report/(args.suite+'-'+backend+'.xml'))]
            evidence_dir=report/'process-artifacts'/backend
            env['S02_TEST_EVIDENCE_DIR']=str(evidence_dir)
            name=args.suite+'-'+backend;log=report/(name+'.log')
            result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True)
            log.write_text('$ '+shlex.join(command)+'\ncwd='+cwd+'\nPYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS unset; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTHONDONTWRITEBYTECODE=1\n'+result.stdout+result.stderr+f'\nexit_code={result.returncode}\n')
            records.append(dict(name=name,command=command,cwd=cwd,exit_code=result.returncode,log=str(log)))
            for line in result.stdout.splitlines():
                for marker in ('S02_EVIDENCE ','PHASE3_EVIDENCE ','PHASE4_EVIDENCE '):
                    if marker in line:
                        data,_=json.JSONDecoder().raw_decode(line.split(marker,1)[1]);observations.append(dict(suite=name,marker=marker.strip(),data=data))
                if 'encoder' in line.lower() or 'S02_ENCODERS' in line:observations.append(dict(suite=name,backend_instrumentation=line))
            print(name,'exit',result.returncode,flush=True)
    (report/(args.suite+'-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
    (report/(args.suite+'-observations.json')).write_text(json.dumps(observations,indent=2)+'\n')
    return int(any(r['exit_code'] for r in records))

if __name__=='__main__':raise SystemExit(main())
