"""Typed projections fail closed and preserve unknown/source data."""
from copy import deepcopy
import pytest

from dacn_s02.codec_boundary import encode
from dacn_s02.h1_service import H1Service
from dacn_s02.h1_store import WorkStore
from h1_fixtures import Case


@pytest.mark.parametrize('bad',['extra','duplicate_key','duplicate_handle','foreign_actor','wrong_type','snapshot','criterion','inventory','bool_step','whitespace','canonical_id','supplied','workflow_node','surrogate'])
def test_candidate_rejected_raw_preserved_no_publication(tmp_path,bad):
    case=Case(tmp_path);case.advance('bootstrap');case.advance(1);candidate=deepcopy(case.responses[1])
    if bad=='extra':candidate['unknown']='x'
    if bad=='duplicate_handle':candidate['proposals']['actions'][1]['handle']='create'
    if bad=='foreign_actor':candidate['proposals']['actions'][0]['actor_ids']=[dict(base_handle='foreign')]
    if bad=='wrong_type':candidate['proposals']['actions'][0]['actor_ids']=[dict(base_handle='pending-mapping')]
    if bad=='snapshot':candidate['proposals']['actions'][0]['trace']['source_refs'][0]['snapshot_id']='foreign'
    if bad=='criterion':candidate['proposals']['actions'][0]['trace']['source_refs'][0]['input_pointer']='/functional_requirements/0/acceptance_criteria/99'
    if bad=='inventory':candidate['inspection'].pop()
    if bad=='bool_step':candidate['step']=True
    if bad=='whitespace':candidate['proposals']['actions'][0]['name']='\u2003'
    if bad=='canonical_id':candidate['proposals']['actions'][0]['id']='injected'
    if bad=='supplied':candidate['proposals']['actors']=[dict(candidate['proposals']['data'][0],kind='supplied')]
    if bad=='workflow_node':candidate['proposals']['workflows'][0]['entry_node_id']=dict(local_handle='item')
    raw=b'{"duplicate":1,"duplicate":2}' if bad=='duplicate_key' else b'{"bad":"\\ud800"}' if bad=='surrogate' else encode(candidate)
    head=case.repo.heads(case.intake['session_id']);cmd=case.prepare(2,raw);result=H1Service(case.repo).resume(cmd)
    assert result['status']=='rejected',result
    assert result['result']['result_pair'] is None and case.repo.heads(case.intake['session_id'])==head
    assert WorkStore(case.repo).load(cmd)['raw']['bytes']==raw


def test_unknown_initiator_is_held_without_guess(tmp_path):
    case=Case(tmp_path);case.advance('bootstrap');case.advance(1);c=deepcopy(case.responses[1])
    c['proposals']['actions'][0].update(initiator='unknown',actor_ids=[],permission_rule_ids=[])
    output=case.advance(2,encode(c));assert output['status']=='blocked'
    action=output['result']['model']['body']['actions'][0]
    assert action['initiator']=='unknown' and action['actor_ids']==[] and action['permission_rule_ids']==[]
    assert action['state']=='needs_clarification' and output['result']['holds']
    assert any(q['body']['kind']=='analysis_omission' for q in output['result']['issues'])
    assert output['result']['questions']==[]  # Code does not claim the fact is absent from S01.
    assert output['result']['next_step'] is None


def test_step4_each_criterion_required_and_gap_cannot_disappear(tmp_path):
    case=Case(tmp_path)
    for step in ('bootstrap',1,2,3):case.advance(step)
    c=deepcopy(case.responses[3]);c['proposals']['mappings'].pop()
    head=case.repo.heads(case.intake['session_id']);cmd=case.prepare(4,encode(c));result=H1Service(case.repo).resume(cmd)
    assert result['status']=='rejected' and case.repo.heads(case.intake['session_id'])==head
    c=deepcopy(case.responses[3]);row=c['proposals']['mappings'][0]
    row['parts'][0].update(assignment='unassigned',remaining_gap='No candidate responsibility for this obligation')
    cmd=case.prepare(4,encode(c));result=H1Service(case.repo).resume(cmd);assert result['status']=='rejected'
    c['unrepresented_source_refs']=[row['source_ref']]
    cmd=case.prepare(4,encode(c));result=H1Service(case.repo).resume(cmd)
    assert result['status']=='blocked' and result['result']['holds']


def test_whole_part_actions_preserved_and_max_handle_supported(tmp_path):
    case=Case(tmp_path)
    for step in ('bootstrap',1,2,3):case.advance(step)
    c=deepcopy(case.responses[3]);row=next(r for r in c['proposals']['mappings'] if r['source_ref']['input_pointer']=='/functional_requirements/0');part=row['parts'][0]
    part['handle']='h'*128;part['action_ids']=[dict(base_handle='step2.create'),dict(base_handle='step2.read')]
    result=case.advance(4,encode(c));assert result['status']=='completed',result
    actual=next(r for r in result['result']['mappings'] if r['source_ref']==row['source_ref'])['parts'][0]
    assert len(actual['action_ids'])==2
    aliases=result['result']['next_aliases'];assert any(x['id']==actual['id'] for x in aliases.values())
    assert all(len(h)<=128 for h in aliases)


def test_array_order_nonsemantic_and_source_unknowns_not_rewritten(tmp_path):
    case=Case(tmp_path);case.advance('bootstrap');case.advance(1)
    c=deepcopy(case.responses[1]);c['inspection'].reverse();c['proposals']['actions'].reverse()
    result=case.advance(2,encode(c));assert result['status']=='completed'
    assert case.s01.get_snapshot(case.snapshot['snapshot_id'])==case.snapshot
    assert case.snapshot['input']['functional_requirements'][0]['priority'] is None
    assert case.snapshot['input']['operating_conditions']==dict.fromkeys(case.snapshot['input']['operating_conditions'])
    assert case.snapshot['input']['functional_requirements'][0]['acceptance_criteria']==['Retain the supplied ID','Retain the supplied status']


def test_unknown_coverage_remains_a_reported_gap(tmp_path):
    case=Case(tmp_path)
    for step in ('bootstrap',1,2,3):case.advance(step)
    c=deepcopy(case.responses[3]);row=c['proposals']['mappings'][0];row['parts'][0]['covered_portion']=None
    cmd=case.prepare(4,encode(c));rejected=H1Service(case.repo).resume(cmd);assert rejected['status']=='rejected'
    c['unrepresented_source_refs']=[row['source_ref']]
    cmd=case.prepare(4,encode(c));blocked=H1Service(case.repo).resume(cmd)
    assert blocked['status']=='blocked' and blocked['result']['holds']
    assert blocked['result']['mappings'][0]['parts'][0]['covered_portion'] is None
