import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from dacn_s01.repository import Repository as S01Repository
from dacn_s01.service import Service as S01Service
from dacn_s01.codec import serialize_json
from dacn_s02.repository import Repository
from helpers import source,operation

def setup(tmp_path):
    one=tmp_path/'s01';one.mkdir();s1=S01Repository(one/'s01.sqlite3');s1.initialize()
    env=S01Service(s1).submit(serialize_json(source()),dict(mode='create',spec_id=None,base_revision=None))
    config=tmp_path/'config.toml';config.write_text('state_dir="s02-state"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    return config,env

def cli(config,*args):
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
    p=subprocess.run([sys.executable,'-B','-m','dacn_s02','--config',str(config),*args],cwd=config.parent,env=env,capture_output=True,timeout=30)
    return p,json.loads(p.stdout) if p.stdout else None

def test_cli_init_start_lookup_receipt(tmp_path):
    config,e=setup(tmp_path)
    p,out=cli(config,'init');assert p.returncode==0 and p.stderr==b''
    receipt=tmp_path/'receipt.json'
    p,out=cli(config,'start','--store-key','synthetic','--s01-run-id',e['run']['run_id'],'--expect-snapshot',e['snapshot']['snapshot_id'],'--receipt',str(receipt))
    assert p.returncode==0 and p.stderr==b'';assert out['result']['snapshot_id']==e['snapshot']['snapshot_id']
    command=out['command_id'];value=json.loads(receipt.read_bytes());assert value['command_id']==command
    p,lookup=cli(config,'show-command','--receipt',str(receipt));assert p.returncode==0;assert lookup['result']['state']=='finalized'
    assert lookup['result']['run']['body']['steps']==[] and lookup['result']['run']['body']['result_model_id'] is None
    p,record=cli(config,'show-record','--id',out['result']['source_context_id']);assert p.returncode==0 and record['result']['type']=='source_context'
    p,missing=cli(config,'show-record','--id','missing');assert p.returncode==4 and missing['status']=='not_found'
    p,_=cli(config,'start','--store-key','synthetic','--s01-run-id',e['run']['run_id'],'--receipt',str(receipt));assert p.returncode==3
    assert json.loads(receipt.read_bytes())==value

def test_cli_receipt_before_intake_failure(tmp_path):
    config,e=setup(tmp_path);cli(config,'init');receipt=tmp_path/'failed.json'
    p,out=cli(config,'start','--store-key','synthetic','--s01-run-id','missing','--receipt',str(receipt))
    assert p.returncode==2 and receipt.is_file();assert out['errors'][0]['code']=='SOURCE_NOT_FOUND'
    p,out=cli(config,'show-command','--receipt',str(receipt));assert p.returncode==4
    # No command in this checked store; this is not an automatic permission to retry.

def test_cli_prepared_receipt_lookup_after_interruption(tmp_path):
    config,e=setup(tmp_path);cli(config,'init');receipt=tmp_path/'receipt.json'
    p,out=cli(config,'start','--store-key','synthetic','--s01-run-id',e['run']['run_id'],'--receipt',str(receipt));assert p.returncode==0
    repo=Repository(tmp_path/'s02-state/s02.sqlite3');op=operation(out['result']['session_id'],out['result']['source_context_id']);repo.prepare(op)
    interrupted=tmp_path/'interrupted.json';interrupted.write_text(json.dumps(dict(receipt_version='s02/1',command_id=op['command_id'],state_dir=str((tmp_path/'s02-state').resolve()))))
    p,out=cli(config,'show-command','--receipt',str(interrupted));assert p.returncode==0 and out['result']['state']=='prepared'

@pytest.mark.parametrize('case',['s01','dataset','config','symlink','hardlink','sidecar','unknown_config'])
def test_path_protection(tmp_path,case):
    config,e=setup(tmp_path);target=tmp_path/'s02-state'
    if case=='s01': config.write_text('state_dir="s01"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n')
    elif case=='dataset':
        (tmp_path/'dataset').mkdir();config.write_text('state_dir="dataset/state"\ndataset_roots=["dataset"]\n')
    elif case=='config':config.write_text('state_dir="config.toml"\n')
    elif case=='unknown_config':config.write_text('state_dir="s02-state"\ncoerce=true\n')
    else:
        target.mkdir();victim=tmp_path/'victim';victim.write_bytes(b'protected')
        destination=target/('s02.sqlite3-journal' if case=='sidecar' else 's02.sqlite3')
        if case=='hardlink':os.link(victim,destination)
        else:destination.symlink_to(victim)
    p,out=cli(config,'init');assert p.returncode in (2,3)
    if (tmp_path/'victim').exists():assert (tmp_path/'victim').read_bytes()==b'protected'

def test_cli_usage_and_no_import_route(tmp_path):
    config,_=setup(tmp_path)
    for command in ('import','advance','answer','render','review'):
        p,out=cli(config,command);assert p.returncode==64 and out is None and p.stderr

def test_installed_cli_encoder_probe(tmp_path):
    config,e=setup(tmp_path);p,_=cli(config,'init');assert p.returncode==0
    observation=tmp_path/'encoder.json';receipt=tmp_path/'receipt.json'
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    command=[sys.executable,'-B',str(Path(__file__).with_name('cli_probe.py')),str(observation),'--config',str(config),'start','--store-key','synthetic','--s01-run-id',e['run']['run_id'],'--receipt',str(receipt)]
    p=subprocess.run(command,cwd=tmp_path,env=env,capture_output=True,timeout=30)
    assert p.returncode==0 and p.stderr==b'';assert json.loads(p.stdout)['status']=='completed'
    data=json.loads(observation.read_bytes());assert data['backend']==env['S02_TEST_CODEC_BACKEND']
    assert data['encoder_calls'][data['backend']]>0
    assert data['encoder_calls']['python' if data['backend']=='c' else 'c']==0
    from helpers import evidence
    evidence('installed_cli_backend',**data)
