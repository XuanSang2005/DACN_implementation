"""H1 ref occurrences and assignment-gap holds, without changing audit oracles."""
from copy import deepcopy
from uuid import uuid4

import pytest

from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h1_candidates import parse
from dacn_s02.h1_limits import Budget,model_limits,ref_count
from dacn_s02.h1_service import H1Service
from dacn_s02.h1_store import WorkStore
from dacn_s02.repository import Repository
from h1_fixtures import Case


def finding(source,handle='f'):
    return dict(handle=handle,kind='verification',question='Inspect this synthetic draft',reason='Synthetic control only',
        trace=dict(origin='inferred',source_refs=[source],rationale='Test input',finding_handles=[]),
        affected_refs=[],blocking_refs=[],impact_known=True)


def through_operations(path):
    case=Case(path);case.advance('bootstrap');candidate=deepcopy(case.responses[0])
    candidate['proposals']['findings']=[finding(candidate['inspection'][0]['source_ref'])]
    assert case.advance(1,encode(candidate))['status']=='completed'
    before=case.advance(2);assert before['status']=='completed'
    return case,before


@pytest.mark.parametrize('value,expected',[
    (dict(handle='declared',id='declared',question='not a ref'),0),
    (dict(finding_handles=['f','f'],questions=['f','f'],finding_handle='f'),5),
    (dict(source_refs=[dict(snapshot_id='s',input_pointer='/a')]*2),2),
    (dict(actor_ids=[dict(base_handle='a')]*2,component_id='c',nested=dict(local_handle='x')),4),
    (dict(trace=dict(finding_handles=['f']*3,source_refs=[dict(snapshot_id='s',input_pointer='/a')])),4),
])
def test_ref_occurrences_include_links_exclude_declarations(value,expected):
    assert ref_count(value)==expected


@pytest.mark.parametrize('total',[50000,50001])
def test_step3_singular_finding_ref_tips_candidate_boundary(tmp_path,total):
    case,before=through_operations(tmp_path);candidate=deepcopy(case.responses[2])
    candidate['proposals']['unassigned_actions']=[dict(action=dict(base_handle='step2.read'),gap='An explicit assignment gap',finding_handle='step1.f')]
    # Six inspection rows: 12 source refs; two entity traces: 2; responsibility:
    # component/action/action/rule: 4; unassigned action + finding_handle: 2.
    assert ref_count(candidate)==20
    candidate['inspection'][0]['finding_handles']=['step1.f']*(total-20)
    def execute():return parse(encode(candidate),3,case.snapshot,before['result']['next_aliases'],lambda:str(uuid4()),Budget())
    if total==50000:execute()
    else:
        with pytest.raises(S02Error) as caught:execute()
        assert caught.value.error['code']=='LOCAL_LIMIT_EXCEEDED' and caught.value.error['details']['limit']=='refs'


def test_result_refs_include_current_issue_links_and_atomic_sources(tmp_path):
    case=Case(tmp_path);result=case.advance('bootstrap');body=deepcopy(result['result']['model']['body'])
    body['mappings']=[];source=dict(snapshot_id=case.snapshot['snapshot_id'],input_pointer='/actors/0')
    body['actors']=[dict(trace=dict(source_refs=[source],issue_ids=['q']*49995))]
    issues=[dict(body=dict(model_id=body['created_by_run_id'],answer_ids=['a']))]
    # Two body refs + one SourceRef + 49995 issue refs + two current-Issue refs.
    model_limits(body,issues)
    body['actors'][0]['trace']['issue_ids'].append('q')
    with pytest.raises(S02Error) as caught:model_limits(body,issues)
    assert caught.value.error['details']['limit']=='refs'


@pytest.mark.parametrize('total',[50000,50001])
def test_ref_limit_end_to_end_raw_head_and_reopen(tmp_path,total):
    case=Case(tmp_path);case.advance('bootstrap');candidate=deepcopy(case.responses[0])
    candidate['proposals']['findings']=[finding(candidate['inspection'][0]['source_ref'])]
    # Twelve inspection source occurrences plus the finding's trace source.
    candidate['inspection'][0]['finding_handles']=['f']*(total-13)
    raw=encode(candidate);head=case.repo.heads(case.intake['session_id']);cmd=case.prepare(1,raw)
    result=H1Service(case.repo).resume(cmd);reopened=Repository(case.repo.path)
    assert H1Service(reopened).resume(cmd)==result
    assert WorkStore(reopened).load(cmd)['raw']['bytes']==raw
    if total==50000:
        assert result['status']=='completed' and result['result']['result_pair']
        assert reopened.heads(case.intake['session_id'])[0]==head[0]
        assert reopened.heads(case.intake['session_id'])[1]!=head[1]
    else:
        assert result['status']=='rejected' and result['result']['result_pair'] is None
        assert result['errors'][0]['code']=='LOCAL_LIMIT_EXCEEDED' and result['errors'][0]['details']['limit']=='refs'
        assert reopened.heads(case.intake['session_id'])==head
    print('H1_REF_BOUNDARY '+encode(dict(total=total,status=result['status'],raw_preserved=True,
        head_before=list(head),head_after=list(reopened.heads(case.intake['session_id'])))).decode('ascii'))


@pytest.mark.parametrize('reference',['local','base','pending-mapping'])
@pytest.mark.parametrize('empty_components',[False,True])
def test_assignment_gap_has_independent_hold_and_preserves_issues(tmp_path,reference,empty_components):
    case,before=through_operations(tmp_path);old={q['id']:encode(q) for q in before['result']['issues']}
    candidate=deepcopy(case.responses[2]);p=candidate['proposals']
    if empty_components:p.update(components=[],responsibilities=[])
    else:p['responsibilities'][0]['action_ids']=[dict(base_handle='step2.create')]
    if reference=='local':
        p['findings']=[finding(candidate['inspection'][0]['source_ref'],'gap')];handle='gap'
    else:handle='step1.f' if reference=='base' else 'pending-mapping'
    handles=['create','read'] if empty_components else ['read']
    p['unassigned_actions']=[dict(action=dict(base_handle='step2.'+h),gap='Unassigned '+h,finding_handle=handle) for h in handles]
    result=case.advance(3,encode(candidate));assert result['status']=='blocked',result
    actual=H1Service(Repository(case.repo.path)).resume(case.parent);assert actual==result
    assert actual['result']['next_step'] is None
    model=actual['result']['model'];issues=actual['result']['issues']
    mapping_task=next(q for q in issues if q['id']==actual['result']['next_aliases']['pending-mapping']['id'])
    gap_holds=[q for q in issues if q['body']['reason'] in {'Unassigned '+h for h in handles}]
    assert len(gap_holds)==len(handles)
    for q in gap_holds:
        assert q['body']['status']=='open' and q['body']['kind']=='analysis_omission'
        assert q['body']['issue_key']!=mapping_task['body']['issue_key']
        assert q['id'] in actual['result']['holds'] and q['body']['blocking']['element_ids']
        assert len(q['body']['trace']['issue_ids'])==1
    for identity,raw in old.items():assert encode(case.repo.get_record(identity))==raw
    for prior in before['result']['issues']:
        current=next(q for q in issues if q['body']['issue_key']==prior['body']['issue_key'])
        if empty_components:assert current==prior
        else:assert current['body']['supersedes_id']==prior['id'] and current['id']!=prior['id']
    assert (model['id']==before['result']['model']['id'])==empty_components
    head=case.repo.heads(case.intake['session_id'])
    with pytest.raises(S02Error):case.prepare(4,encode(case.responses[3]))
    assert case.repo.heads(case.intake['session_id'])==head


def test_fully_assigned_control_keeps_nonblocking_issue_and_completes(tmp_path):
    case,before=through_operations(tmp_path);old={q['id']:encode(q) for q in before['result']['issues']}
    assert case.advance(3)['status']=='completed'
    result=case.advance(4);assert result['status']=='completed' and result['result']['next_step'] is None
    verification=next(q for q in result['result']['issues'] if q['id']==result['result']['next_aliases']['step1.f']['id'])
    assert verification['body']['status']=='open' and not verification['body']['blocking']['element_ids']
    assert result['result']['holds']==[]
    for identity,raw in old.items():assert encode(case.repo.get_record(identity))==raw


def test_two_gaps_share_mapping_task_but_keep_distinct_holds(tmp_path):
    case,before=through_operations(tmp_path);candidate=deepcopy(case.responses[2])
    p=candidate['proposals'];p['components']=[];p['responsibilities']=[]
    p['unassigned_actions']=[dict(action=dict(base_handle='step2.'+h),gap='Unassigned '+h,finding_handle='pending-mapping') for h in ('read','create')]
    result=case.advance(3,encode(candidate));assert result['status']=='blocked'
    gaps=[q for q in result['result']['issues'] if q['body']['reason'].startswith('Unassigned ')]
    assert len(gaps)==2 and len({q['body']['issue_key'] for q in gaps})==2
    for h in ('read','create'):
        aid=result['result']['next_aliases']['step2.'+h]['id']
        assert any(aid in q['body']['blocking']['element_ids'] for q in gaps)
