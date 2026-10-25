"""H1 uses S01 services and the production handlers; no canonical shortcuts."""
import json
from copy import deepcopy
from pathlib import Path

from dacn_s02.codec_boundary import encode
from dacn_s02.repository import Repository
from dacn_s02.h1_service import H1Service
from h1_fixtures import Case


def test_four_mock_handlers_checkpoint_reopen(tmp_path):
    case=Case(tmp_path);s01_before=case.s01.path.read_bytes()
    boot=case.advance('bootstrap');assert boot['status']=='completed',boot
    for step in range(1,5):
        output=case.advance(step);assert output['status']=='completed',output
        reopened=H1Service(Repository(case.repo.path)).resume(case.parent)
        assert output==reopened
    result=output['result'];model=result['model']['body']
    assert len(model['actions'])==2 and len(model['components'])==1
    assert len(model['mappings'])==6 and all(m['parts'] for m in model['mappings'])
    assert all(q['body']['status']=='resolved' for q in result['issues'])
    assert model['actors'][0]['name']=='Operator' and model['actors'][0]['kind']=='supplied'
    assert result['completed_steps']==[1,2,3,4] and result['next_step'] is None
    assert case.s01.path.read_bytes()==s01_before
    print('H1_FLOW '+encode(dict(run_id=result['run_id'],result_pair=result['result_pair'],steps=result['completed_steps'],mappings=len(model['mappings']),origin=result['execution_origin'])).decode('ascii'))


def test_blocked_checkpoint_retains_hold(tmp_path):
    case=Case(tmp_path);case.advance('bootstrap');candidate=deepcopy(case.responses[0])
    candidate['inspection'][0].update(verdict='held',needed_facts=['Unknown permission scope'])
    result=case.advance(1,encode(candidate));assert result['status']=='blocked',result
    again=H1Service(Repository(case.repo.path)).resume(case.parent)
    assert again==result and result['result']['holds']
    assert all(q['body']['status']=='open' for q in result['result']['issues'])
