"""Run the explicit DB2/E1 lane with fresh test workspace and encoder instrumentation."""
from pathlib import Path
import argparse,os,shutil,subprocess,sys,tempfile
from prepare_p2_tests import prepare,ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    p.add_argument('--report-dir',type=Path,required=True)
    p.add_argument('--baseline-python',type=Path,required=True)
    p.add_argument('--baseline-helpers',type=Path,required=True)
    p.add_argument('--legacy-python',type=Path,required=True)
    p.add_argument('--audit-file',type=Path,action='append',default=[])
    p.add_argument('--audit-only',action='store_true')
    a=p.parse_args();out=a.report_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(DACN_LEGACY_PYTHON=str(a.legacy_python.absolute()),DACN_P1_PYTHON=str(a.baseline_python.absolute()),DACN_BASELINE_HELPERS=str(a.baseline_helpers.resolve()),PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH',None)
    with tempfile.TemporaryDirectory(prefix='dacn-p2-test-lane-') as directory:
        root=Path(directory);tests=prepare(root/'packages/s02/tests')
        shutil.copyfile(tests/'ADAPTER.json',out/'ADAPTER.json')
        shutil.copytree(tests,out/'test-inputs')
        shutil.copyfile(ROOT/'packages/s02/pyproject.toml',root/'packages/s02/pyproject.toml')
        (root/'tools').mkdir();shutil.copyfile(ROOT/'tools/run_checks.py',root/'tools/run_checks.py')
        argv=[sys.executable,'-B',str(root/'tools/run_checks.py'),'--package','s02','--report-dir',str(out/'checks')]
        if a.audit_only:argv+=['--audit-only']
        for f in a.audit_file:argv+=['--audit-file',str(f.resolve())]
        return subprocess.run(argv,cwd=root,env=env).returncode
if __name__=='__main__':raise SystemExit(main())
