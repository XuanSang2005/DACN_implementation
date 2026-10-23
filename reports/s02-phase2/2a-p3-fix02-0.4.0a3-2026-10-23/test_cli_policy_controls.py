"""Additional CLI controls with actual subprocess codec instrumentation.

The four independent oracle files stay untouched. This suite invokes the
existing cli_probe test harness before calling the installed CLI entry point.
"""
from dataclasses import replace
import json,os,subprocess,sys
from pathlib import Path
import pytest
import process_worker
from dacn_s02 import reservation
from dacn_s02.migration import Migration
from helpers import evidence
from migration_fixtures import make_migration
from test_reservation_path_policy import inventory,prepare


def cli(m,receipt,tmp_path,*,resume):
    counts=tmp_path/'cli-encoder-counts.json'
    args=[sys.executable,'-B',str(Path(process_worker.__file__).with_name('cli_probe.py')),
        str(counts),'--config',str(m.settings.path),'migration-copy','--source-state-dir',str(m.source),
        '--migration-receipt',str(receipt),'--offline-confirmed']
    if resume:args.append('--resume')
    result=subprocess.run(args,cwd=tmp_path,capture_output=True,text=True)
    observed=json.loads(counts.read_text())
    mode=os.environ['S02_TEST_CODEC_BACKEND']
    assert observed['backend']==mode and observed['encoder_calls'][mode]>0
    assert observed['encoder_calls']['python' if mode=='c' else 'c']==0
    evidence('reservation_cli_policy',argv=args,cwd=str(tmp_path),exit_code=result.returncode,
        stdout=result.stdout,stderr=result.stderr,**observed)
    return result,counts


@pytest.mark.parametrize('phase',['fresh','receipt_only','committed'])
@pytest.mark.parametrize('kind',['dataset_roots','protected_roots','s01_stores','checkout'])
def test_cli_refusal_on_new_copy_and_resume_with_observed_backend(tmp_path,phase,kind):
    m,receipt=prepare(tmp_path,phase)
    space=reservation.namespace(m.destination);space.mkdir(exist_ok=True)
    text='state_dir = '+json.dumps(str(m.destination))+'\n'
    if kind in ('dataset_roots','protected_roots'):text+=kind+' = ['+json.dumps(str(space))+']\n'
    elif kind=='s01_stores':text+='[s01_stores]\nsynthetic = '+json.dumps(str(space/'s01.sqlite3'))+'\n'
    else:
        (space/'AGENTS.md').write_text('Synthetic checkout\n')
        (space/'pyproject.toml').write_text('[tool.synthetic]\n')
    m.settings.path.write_text(text)
    before=inventory(tmp_path)
    result,counts=cli(m,receipt,tmp_path,resume=phase!='fresh')
    # Only the external harness's encoder observation is a new file.
    after=inventory(tmp_path);after.pop(counts.name)
    assert result.returncode!=0 and after==before


@pytest.mark.parametrize('name,alias',[('CaseTarget','casetarget'),('caf\u00e9','cafe\u0301')])
def test_cli_permitted_name_alias_resume_with_observed_backend(tmp_path,name,alias):
    old,receipt,_=make_migration(tmp_path,empty=True)
    m=Migration(replace(old.settings,state=old.destination.with_name(name)),old.source)
    first=m.copy(receipt,offline=True)
    assert reservation.marker(m.destination.with_name(alias)).samefile(reservation.marker(m.destination))
    m.settings.path.write_text('state_dir = '+json.dumps(str(m.destination))+'\n')
    before=inventory(tmp_path)
    result,counts=cli(m,receipt,tmp_path,resume=True)
    after=inventory(tmp_path);after.pop(counts.name)
    assert result.returncode==0 and after==before
    output=json.loads(result.stdout)
    assert output['result']['status']==first['status']
