"""Verify a bootstrapped checkout with unchanged product tests and P3 oracles."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--environment',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--focused-only',action='store_true')
    args=parser.parse_args();out=args.output.resolve()
    if out==ROOT or ROOT in out.parents:parser.error('Checks output must be outside checkout')
    data=json.loads(args.environment.read_text())
    if Path(data['checkout']).resolve()!=ROOT:parser.error('Environment belongs to another checkout')
    out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    for key in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(key,None)
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        DACN_P1_PYTHON=data['python']['p1'],DACN_LEGACY_PYTHON=data['python']['legacy'],DACN_BASELINE_HELPERS=data['helpers'])
    python=data['python']['candidate']
    def run(label,argv,*,cwd=None,extra_env=None):
        argv=list(map(str,argv));start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        child_env=env.copy();child_env.update(extra_env or {});cwd=cwd or out
        with (out/(label+'.log')).open('x') as stream:result=subprocess.run(argv,cwd=cwd,env=child_env,stdout=stream,stderr=subprocess.STDOUT)
        (out/(label+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(cwd),start=start,exit_code=result.returncode,environment=extra_env or {}),indent=2)+'\n')
        if result.returncode:raise RuntimeError(label+' failed; see '+str(out/(label+'.log')))
    common=['--baseline-python',data['python']['p1'],'--baseline-helpers',data['helpers'],'--legacy-python',data['python']['legacy']]
    oracles=ROOT/'.bootstrap/oracles'
    files=[oracles/name for name in ('test_independent_p3_partial.py','test_independent_p3_preservation.py','test_independent_reservation_paths.py','test_independent_reservation_cli.py')]
    files.append(ROOT/'reports/s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/test_cli_policy_controls.py')
    run('p3-oracles',[python,'-B',ROOT/'packages/s02/tools/run_p2_checks.py',*common,'--audit-only',
        *[part for path in files for part in ('--audit-file',path)],'--report-dir',out/'p3-oracles'])
    run('wrappers',[python,'-B','-m','unittest','discover','-s',ROOT/'tools/tests','-p','test_package_wrappers.py','-v'])
    run('layout',[python,'-B',ROOT/'tools/check_layout.py','--report-dir',out/'layout'])
    if not args.focused_only:
        # Prepare the established E1 adapter once; only scheduling differs from
        # run_checks.py. Every assertion, conftest and backend hook is unchanged.
        import sys
        sys.path.insert(0,str(ROOT/'packages/s02/tools'))
        from prepare_p2_tests import prepare
        with tempfile.TemporaryDirectory(prefix='dacn-clean-checkout-') as temporary:
            work=Path(temporary);tests=prepare(work/'packages/s02/tests')
            shutil.copytree(tests,out/'s02-test-inputs')
            project=work/'packages/s02/pyproject.toml';shutil.copyfile(ROOT/'packages/s02/pyproject.toml',project)
            def job(backend):
                with tempfile.TemporaryDirectory(prefix='dacn-installed-checks-') as cwd:
                    run('s02-'+backend,[python,'-B','-m','pytest','-c',project,tests,'-s','-v','--tb=short',
                        '-p','no:cacheprovider','--encoder-backend='+backend,'--basetemp='+str(Path(cwd)/'tmp'),
                        '--junitxml='+str(out/('s02-'+backend+'.xml'))],cwd=cwd,
                        extra_env={'S02_TEST_EVIDENCE_DIR':str(out/'process-artifacts'/backend)})
            with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(job,('c','python')))
        run('s01',[python,'-B',ROOT/'tools/run_checks.py','--package','s01','--report-dir',out/'s01'])
    stats={}
    for path in out.rglob('*.xml'):
        suites=list(ET.parse(path).getroot().iter('testsuite'))
        stat={key:sum(int(node.attrib.get(key,0)) for node in suites) for key in ('tests','failures','errors','skipped')}
        if any(stat[key] for key in ('failures','errors','skipped')):raise ValueError('Unexpected JUnit result: '+str(path))
        stats[str(path.relative_to(out))]=stat
    (out/'results.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(dict(checkout=str(ROOT),passed=True,junit=stats)))


if __name__=='__main__':main()
