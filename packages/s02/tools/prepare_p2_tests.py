"""Create a distinct DB2/E1 test lane without editing historical assertions.

Input hashes and every text change are emitted for review. This is test tooling,
not a production profile converter, writer, or migration entry point.
"""
from pathlib import Path
import argparse,difflib,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
def prepare(destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    source=ROOT/'packages/s02/tests';changes={};hashes={}
    for p in sorted(source.glob('*.py')):
        old=p.read_text();new=old
        if p.name=='helpers.py':
            new=new.replace('resolution_event_refs=[],resolution=None)',
                'resolution_event_refs=[],resolution=None,resolution_carry=None,resolution_replacement=None)')
        if p.name=='test_lifecycle.py':
            new=new.replace('consent_event=None,s01_observation_event=None,change_id=',
                'consent_event=None,s01_observation_event=None,observed_source_context_id=None,change_id=')
        if p.name=='profile_fixtures.py':
            new=new.replace('    return Graph(records,{i:L1', '''    # In-memory L1 root projection for the unchanged pure-validator oracle.
    # DB2 writes above used explicit E1; no L1 storage writer is exposed.
    for r in records.values():
        if r['type']=='issue':
            r['body'].pop('resolution_carry');r['body'].pop('resolution_replacement')
    for e in events.values():
        if e['kind']=='application_applied':e['payload'].pop('observed_source_context_id')
    return Graph(records,{i:L1''')
        if p.name=='test_profiles.py':
            new=new.replace('def test_repository_cannot_write_e1_issue','def test_repository_cannot_write_l1_issue')
            new=new.replace("    s=aset(m,'AS-E1'", "    del q['body']['resolution_carry'];del q['body']['resolution_replacement']\n    s=aset(m,'AS-E1'")
        if p.name=='test_cli.py':
            new=new.replace("record['result']['type']", "record['result']['record']['type']")
            new=new.replace("receipt_version='s02/1',command_id=op['command_id']", "receipt_version='s02/2',store_id=repo.store_info()['metadata']['store_id'],command_id=op['command_id']")
        if p.name=='test_contract_artifacts.py':
            new=new.replace('Path(__file__).resolve().parents[3]',repr(ROOT).replace('PosixPath','Path'))
        if p.name=='test_config_pin.py':
            new=new.replace("b'{\"synthetic_config\":\"T0\"}'", "f.repo.get_blob(f.config)[:-1]+b',\"synthetic_config\":\"T0\"}'")
            new=new.replace("'dacn_s02.events.validate_operations'","'dacn_s02.profile_graph.validate_operations'")
        if p.name=='test_audit_guards.py':
            new=new.replace("        fake.setattr('dacn_s02.repository.validate_record',lambda *a,**k:None)\n        fake.setattr('dacn_s02.events.validate_operations',lambda *a,**k:None)",'''        # Deliberate corrupt fixture at the new graph gate, restored on reopen.
        from dacn_s02.s01_adapter import verify_archive
        def fixture_snapshots(**kw):
            return {r['body']['snapshot_id']:verify_archive(r,kw['records'],kw['blobs'])
                    for r in kw['records'].values() if r['type']=='source_context'}
        fake.setattr('dacn_s02.repository.validate_graph',fixture_snapshots)''')
        (destination/p.name).write_text(new)
        hashes[p.name]=dict(input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(new.encode()).hexdigest())
        if new!=old:changes[p.name]=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+p.name,tofile='p2/'+p.name))
    (destination/'ADAPTER.json').write_text(json.dumps(dict(input_root=str(source),files=hashes,changes=changes),indent=2)+'\n')
    return destination
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    prepare(parser.parse_args().destination)
