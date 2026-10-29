import os,subprocess,sys
from uuid import uuid4
from pathlib import Path
from hashlib import sha256
from dacn_s02.codec_boundary import decode
from dacn_s02.local_io import settings,write_receipt
from h2_checkpoint_fixtures import ScopedCase


from test_h1_cli import cli  # Test-only process probe and encoder evidence.


def test_scoped_cli_authority_receipts_exit_codes(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap()
    config=tmp_path/'s02.toml';config.write_text('state_dir="s02"\n[s01_stores]\nsynthetic="s01/s01.sqlite3"\n');s=settings(config)
    parent=tmp_path/'parent.json';write_receipt(s,parent,case.parent,store_id=case.store_id)
    work,authority=case.work(1);candidate=tmp_path/'candidate.json';candidate.write_bytes(work['candidate']);analysis=tmp_path/'analysis.json';analysis.write_bytes(work['analysis'])
    receipt=tmp_path/'work.json';cmd=str(uuid4());write_receipt(s,receipt,cmd,store_id=case.store_id)
    p,r=cli(config,'scoped-resume','--receipt',receipt);assert p.returncode==5,(p.stderr,r)
    fields=['--from-receipt',parent,'--step','1','--expect-model',case.pair[0],'--expect-analysis-set',case.pair[1],'--mock-response',candidate,'--expect-sha256',sha256(work['candidate']).hexdigest(),'--analysis',analysis,'--expect-analysis-sha256',sha256(work['analysis']).hexdigest()]
    for unit in work['unit_ids']:fields += ['--unit',unit]
    new=tmp_path/'unavailable.json'
    p,r=cli(config,'scoped-step',*fields,'--receipt',new);assert p.returncode==3 and not new.exists(),(p.stderr,r)
    flags=['--h2-authority-file',authority.path,'--expect-h2-authority-sha256',authority.expected_sha256]
    p,r=cli(config,*flags,'prepare-scope-work','--mode','step',*fields,'--receipt',receipt);assert p.returncode==0,(p.stderr,r)
    p,r=cli(config,*flags,'scoped-resume','--receipt',receipt);assert p.returncode==2 and r['status']=='blocked',(p.stderr,r)
    authority.path.unlink()
    p,r=cli(config,'scoped-progress','--receipt',receipt);assert p.returncode==0 and r['result']['eligibility_authorized_in_process'] is False,(p.stderr,r)
    p,r=cli(config,'scoped-resume','--receipt',receipt);assert p.returncode==2 and r['status']=='blocked',(p.stderr,r)
    p,r=cli(config,'scoped-resume','--receipt',receipt,'--analysis',analysis);assert p.returncode==64
    p,r=cli(config,'--h2-authority-file',authority.path,'scoped-resume','--receipt',receipt);assert p.returncode==64
    p,r=cli(config,'scoped-progress','--receipt',tmp_path/'missing.json');assert p.returncode==4
