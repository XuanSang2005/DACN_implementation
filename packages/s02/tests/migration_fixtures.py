"""Generate synthetic DB1 using the separately installed accepted a3 wheel."""
from pathlib import Path
import json,os,subprocess
from dacn_s02.local_io import Settings
from dacn_s02.migration import Migration

def make_migration(tmp,extra='',*,empty=False,initial=True):
    tmp=Path(tmp).resolve();source=tmp/'source';source.mkdir();info=tmp/'fixture.json'
    code="""import sys,json
sys.path.insert(0,sys.argv[1])
from helpers import Foundation,run
from dacn_s02.repository import Repository
if sys.argv[4]=='empty':
 Repository(sys.argv[2]+'/s02.sqlite3').initialize();info={}
else:
 f=Foundation(sys.argv[2])
 if sys.argv[6]=='initial':m,a=f.initial(True)
 info=dict(command_id=f.result['command_id'],session=f.session,context=f.context,config=f.config,snapshot=f.snapshot)
 exec(sys.argv[5])
open(sys.argv[3],'w').write(json.dumps(info))
"""
    subprocess.run([os.environ['DACN_LEGACY_PYTHON'],'-B','-c',code,os.environ['DACN_BASELINE_HELPERS'],str(source),str(info),'empty' if empty else 'full',extra,'initial' if initial else 'blank'],check=True,cwd=tmp)
    s=Settings(tmp/'config.toml',tmp/'target',{},(),200)
    return Migration(s,source),tmp/'migration.json',json.loads(info.read_text())
