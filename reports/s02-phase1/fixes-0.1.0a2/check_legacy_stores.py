"""Read copies of a1 audit evidence through the installed a2 checked lookup.

No mutation/migration of original audit databases. Synthetic evidence only.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from dacn_s02.repository import Repository
from dacn_s02.errors import S02Error
from dacn_s02.scope import permitted_scope, make_scope
from dacn_s02.validation import index_model

parser=argparse.ArgumentParser()
parser.add_argument('audit_evidence',type=Path)
parser.add_argument('valid_databases',type=Path)
args=parser.parse_args()
report=Path(__file__).parent
audit=json.loads(args.audit_evidence.read_bytes())
observations=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='dacn-s02-legacy-copies-') as tmp:
    for backend,data in audit['negative_tests'].items():
        for index,observation in enumerate(data['observations']):
            original=Path(observation['db']);before=sha(original)
            copy=Path(tmp)/f'{backend}-{index}.sqlite3';shutil.copy2(original,copy)
            repo=Repository(copy);expected_reject='unassessed_mapping' not in observation
            error=None
            try:repo.verify()
            except S02Error as exc:error=exc.error
            assert (error is not None)==expected_reject,(original,error)
            item=dict(backend=backend,original=str(original),sha256=before,expected_reject=expected_reject,error=error)
            if not expected_reject:
                model=repo.get_record('M1');elements,parts=index_model(model)
                gate=permitted_scope(model,make_scope('M1',parts=['P1']),make_scope('M1',elements,parts),current_analysis_set_id='AS1',reviewed_analysis_set_id='AS1',issues=[repo.get_record('Q-global')])
                assert not gate['allowed_scope']['mapping_part_ids'] and 'MAPPING_NOT_ASSESSED' in gate['reason_codes']
                item['gate']=gate
            else:assert error['code']=='PERSISTENCE_FAILED'
            assert sha(original)==before;observations.append(item)
    compatible=[]
    for index,original in enumerate(sorted(args.valid_databases.rglob('*.sqlite3'))):
        copy=Path(tmp)/f'valid-{index}.sqlite3';before=sha(original);shutil.copy2(original,copy)
        Repository(copy).verify();assert sha(original)==before
        compatible.append(dict(path=str(original),sha256=before,verified=True))
assert len(observations)==14 and len(compatible)==18
result=dict(scope='Synthetic a1 evidence copied to temporary stores; a2 installed package',negative_stores=observations,valid_a1_stores=compatible)
(report/'legacy-store-results.json').write_text(json.dumps(result,indent=2)+'\n')
print('12 bad histories rejected; 2 unfinished models readable but gated; 18 valid a1 stores readable')
