"""Bootstrap offline from the hash-pinned macOS arm64 bundle into new venvs."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import zipfile
from artifact_bundle import verify,restore

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--environment-root',type=Path,required=True)
    args=parser.parse_args();out=args.environment_root.resolve()
    if out.exists() or out==ROOT or ROOT in out.parents:parser.error('Environment root must be new and outside checkout')
    if platform.system()!='Darwin' or platform.machine()!='arm64':parser.error('Pinned bundle requires macOS arm64')
    spec,entries=verify(args.bundle,ROOT/'artifacts/bootstrap-bundle.json',ROOT/'artifacts/bootstrap.inventory.json')
    restore(args.bundle,ROOT,entries)
    out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    for key in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(key,None)
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',UV_CACHE_DIR=str(out/'uv-cache'))
    def run(label,argv):
        argv=list(map(str,argv));start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (out/(label+'.log')).open('x') as stream:
            result=subprocess.run(argv,cwd=out,env=env,stdout=stream,stderr=subprocess.STDOUT)
        (out/(label+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(out),start=start,exit_code=result.returncode),indent=2)+'\n')
        if result.returncode:raise RuntimeError(label+' failed; see '+str(out/(label+'.log')))
    def python(lane):return out/(lane+'/bin/python')
    wheels=ROOT/'.bootstrap/wheels';s01=wheels/'dacn_s01-0.1.0a6-py3-none-any.whl';s02=wheels/'dacn_s02-0.4.0a3-py3-none-any.whl'
    runtime=ROOT/'.runtime/python/bin/python3.13'
    run('runtime',[runtime,'-B','-c','import platform,sqlite3,sys; assert platform.python_version()=="3.13.16" and sqlite3.sqlite_version=="3.53.1" and sys._is_gil_enabled(); print(sys.version,sqlite3.sqlite_version)'])
    for lane,version in (('candidate','0.4.0a3'),('p1','0.2.0a3'),('legacy','0.1.0a3')):
        run(lane+'-venv',[runtime,'-B','-m','venv','--without-pip',out/lane])
        run(lane+'-locks',[ROOT/'.tools/uv','pip','install','--python',python(lane),'--no-index',
            '--find-links',ROOT/'.tools/wheelhouse','--find-links',wheels,'--require-hashes','-r',ROOT/'packages/s02/requirements-dev.lock'])
        run(lane+'-wheels',[python(lane),'-B','-m','pip','install','--force-reinstall','--no-index','--no-deps',s01,wheels/('dacn_s02-'+version+'-py3-none-any.whl')])
    build=out/'build-inputs'
    for relative in ('tools/build_packages.py','packages/s01/pyproject.toml','packages/s02/pyproject.toml'):
        target=build/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
    for stage in ('s01','s02'):
        shutil.copytree(ROOT/('packages/'+stage+'/src'),build/('packages/'+stage+'/src'),ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
    run('build',[python('candidate'),'-B',build/'tools/build_packages.py','--package','all','--output-dir',out/'builds'])
    comparisons={}
    for wheel in (s01,s02):
        with zipfile.ZipFile(wheel) as old,zipfile.ZipFile(out/'builds'/wheel.name) as new:
            if old.namelist()!=new.namelist() or any(old.read(n)!=new.read(n) for n in old.namelist()):
                raise ValueError('Source build differs from accepted wheel: '+wheel.name)
            comparisons[wheel.name]=dict(entries=len(old.namelist()),all_entries_equal=True)
    run('candidate-rebuilt',[python('candidate'),'-B','-m','pip','install','--force-reinstall','--no-index','--no-deps',*[out/'builds'/p.name for p in (s01,s02)]])
    run('pip-check',[python('candidate'),'-B','-m','pip','check'])
    run('package-evidence',[python('candidate'),'-B',ROOT/'tools/collect_evidence.py','--package','all',
        '--wheel-dir',out/'builds','--baseline-wheel','s01='+str(s01),'--baseline-wheel','s02='+str(s02),'--report-dir',out/'package-evidence'])
    result=dict(checkout=str(ROOT),bundle_sha256=spec['sha256'],python={lane:str(python(lane)) for lane in ('candidate','p1','legacy')},
        helpers=str(ROOT/'.bootstrap/p1-helpers'),comparisons=comparisons,source='Accepted wheels and clean copied-source rebuilds; all entries compared')
    (out/'environment.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(bootstrap='passed',environment=str(out/'environment.json'),comparisons=comparisons)))


if __name__=='__main__':main()
