"""Actual installed CLI, real receipts, pinned mock bytes and encoder factories."""
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from dacn_s02.codec_boundary import encode
from dacn_s02.repository import digest
from dacn_s02.local_io import settings,write_receipt
from h1_fixtures import Case


def cli(config,*args):
    evidence=Path(os.environ.get('S02_TEST_EVIDENCE_DIR',str(config.parent/'evidence')));evidence.mkdir(parents=True,exist_ok=True)
    token=str(uuid4());counts=evidence/(token+'.encoders.json')
    argv=[sys.executable,'-B',str(Path(__file__).with_name('cli_probe.py')),str(counts),'--config',str(config),*map(str,args)]
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run(argv,cwd=config.parent,env=env,capture_output=True,timeout=45)
    (evidence/(token+'.stdout.log')).write_bytes(result.stdout);(evidence/(token+'.stderr.log')).write_bytes(result.stderr)
    (evidence/(token+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(config.parent),exit_code=result.returncode)))
    if counts.exists():
        observed=json.loads(counts.read_text());selected=os.environ.get('S02_TEST_CODEC_BACKEND','c')
        assert observed['backend']==selected
        assert observed['encoder_calls'][selected]>0 and observed['encoder_calls']['python' if selected=='c' else 'c']==0
    return result,json.loads(result.stdout) if result.stdout else None


def test_actual_cli_s01_four_mocks_and_resume(tmp_path):
    case=Case(tmp_path);config=tmp_path/'cli.toml'
    config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    parent=tmp_path/'intake.receipt.json'
    proc,intake=cli(config,'start','--store-key','synthetic','--s01-run-id',case.envelope['run']['run_id'],'--expect-snapshot',case.snapshot['snapshot_id'],'--receipt',parent)
    assert proc.returncode==0 and intake['result']['snapshot_id']==case.snapshot['snapshot_id']
    boot=tmp_path/'bootstrap.receipt.json'
    proc,out=cli(config,'bootstrap','--from-receipt',parent,'--receipt',boot)
    assert proc.returncode==0 and out['result']['model']['body']['revision']==1,(proc.stderr,out)
    parent=boot
    for step,candidate in enumerate(case.responses,1):
        response=tmp_path/('step'+str(step)+'.json');response.write_bytes(encode(candidate));receipt=tmp_path/('step'+str(step)+'.receipt.json')
        proc,out=cli(config,'analyze-step','--from-receipt',parent,'--step',str(step),'--mock-response',response,'--expect-sha256',digest(response.read_bytes()),'--receipt',receipt)
        assert proc.returncode==0,(proc.stderr,out)
        response.unlink()  # Successful resume must never reopen the mock file.
        proc,again=cli(config,'resume','--receipt',receipt);assert proc.returncode==0 and again==out
        parent=receipt
    proc,progress=cli(config,'progress','--receipt',parent)
    assert proc.returncode==0 and len(progress['result']['mappings'])==6
    assert progress['result']['semantic_status']=='synthetic_draft_not_reviewed'


def test_receipt_only_explicit_prepare_work_and_conflicts(tmp_path):
    case=Case(tmp_path);config=tmp_path/'cli.toml';config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    parent=tmp_path/'parent.receipt';write_receipt(settings(config),parent,case.parent,store_id=case.store_id)
    receipt=tmp_path/'bootstrap.receipt';cmd=str(uuid4());write_receipt(settings(config),receipt,cmd,store_id=case.store_id);before=receipt.read_bytes()
    proc,out=cli(config,'resume','--receipt',receipt);assert proc.returncode==5 and out['status']=='not_prepared'
    proc,out=cli(config,'prepare-work','--receipt',receipt,'--from-receipt',parent,'--step','bootstrap');assert proc.returncode==0 and out['status']=='prepared'
    reserved=out['result']['reserved_run_id']
    proc,out=cli(config,'prepare-work','--receipt',receipt,'--from-receipt',parent,'--step','bootstrap');assert proc.returncode==0 and out['result']['reserved_run_id']==reserved
    proc,out=cli(config,'resume','--receipt',receipt);assert proc.returncode==0 and out['result']['run_id']==reserved
    assert receipt.read_bytes()==before
    proc,out=cli(config,'prepare-work','--receipt',receipt,'--from-receipt',parent,'--step','bootstrap','--mock-response','forbidden')
    assert proc.returncode==64


def test_cli_lookup_unavailable_is_not_absence(tmp_path):
    case=Case(tmp_path);config=tmp_path/'cli.toml';config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    receipt=tmp_path/'pending.receipt';cmd=str(uuid4());write_receipt(settings(config),receipt,cmd,store_id=case.store_id)
    moved=case.repo.path.with_suffix('.offline');case.repo.path.rename(moved)
    proc,out=cli(config,'resume','--receipt',receipt)
    assert proc.returncode==3 and out['status']=='failed' and out['result']['reconciliation']=='unknown'
    moved.rename(case.repo.path);assert case.repo.get_command(cmd) is None
