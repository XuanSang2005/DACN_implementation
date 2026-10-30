from copy import deepcopy
from dataclasses import replace
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_limits import Budget
from dacn_s02.h3_contracts import Contract
from dacn_s02.h3_history import project_current_refs
from dacn_s02.h3_policy import transition,admit,unassessed_progress,retained_output
from h3_fixtures import setup,view,data,selector_rows,bind_work


def test_direct_to_carry_projection_preserves_root_and_current_refs(foundation):
    g=setup(foundation);b=Budget();before=view(g,b);root=deepcopy(g.records['Q2-resolved']);apps=deepcopy(g.events)
    g.carry(new_model=True);after=view(g,b)
    decision=transition(before,after,step=2,unit_ids=list(before.context.source.units))
    assert decision[0]['branch']=='CARRY' and decision[0]['origin_issue_id']=='Q2-resolved'
    assert decision[0]['from_issue_id']=='Q2-resolved' and decision[0]['status']=='resolved'
    assert not decision[0]['blocks'] and g.records['Q2-resolved']==root
    assert all(g.events[k]==e for k,e in apps.items())
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1


@pytest.mark.parametrize('assessment',['applicable','undetermined'])
def test_carry_multihop_and_pending_resolution_holds(foundation,assessment):
    g=setup(foundation);g.carry(assessment);b=Budget();before=view(g,b);old=g.current_issue
    g.carry(assessment,new_model=True);after=view(g,b)
    p=transition(before,after,step=2,unit_ids=list(before.context.source.units))[0]
    assert p['origin_issue_id']=='Q2-resolved' and p['from_issue_id']==old
    assert p['blocks']==(assessment=='undetermined')
    assert set(p['footprint']['element_ids'])=={'A1','A2','W1','W2','C1','C2','RS1','RS2'}
    assert set(p['footprint']['mapping_part_ids'])=={'P1','P12','P2'}


def test_missing_coverage_pending_is_legal_but_false_release_is_invalid(foundation):
    g=setup(foundation);q=g.carry('undetermined');q['body']['resolution_carry']['source_checks']=[];q['body']['resolution_carry']['scope_check']['element_pairs']=[]
    v=view(g);assert v.projection('Question2')['blocks']
    q['body']['resolution_carry']['assessment']='applicable';q['body']['status']='resolved';q['body']['blocking']['element_ids']=[];q['body']['blocking']['mapping_part_ids']=[]
    with pytest.raises(S02Error):data(g)


@pytest.mark.parametrize('mutation',['from','origin','root_event','source','scope','cycle','current_ref'])
def test_invalid_proof_never_becomes_undetermined(foundation,mutation):
    g=setup(foundation);q=g.carry('undetermined');p=q['body']['resolution_carry']
    if mutation=='from':p['from_issue_id']='Q2'
    if mutation=='origin':p['origin_issue_id']='Q2'
    if mutation=='root_event':
        e=q['body']['resolution_event_refs'][0];g.events[e['command_id'],e['event_id']]['payload']['resolved_issue_id']=q['id']
    if mutation=='source':p['source_checks'][0]['from_ref']['snapshot_id']='unknown'
    if mutation=='scope':p['scope_check']['to_scope']['element_ids'].remove('A2')
    if mutation=='cycle':q['body']['supersedes_id']=q['id'];p['from_issue_id']=q['id']
    if mutation=='current_ref':q['body']['trace']['issue_ids']=['Q2-resolved']
    with pytest.raises(S02Error):data(g)


def test_typed_projection_keeps_all_history_fields(foundation):
    g=setup(foundation);g.carry();q=deepcopy(g.records[g.current_issue]);q['body']['trace']['issue_ids']=[q['id']]
    old=deepcopy(q);projected=project_current_refs(q,'NextModel',{q['id']:'NextIssue'},Budget())
    assert projected['model_id']=='NextModel' and projected['affected']['model_id']=='NextModel'
    assert projected['trace']['issue_ids']==['NextIssue']
    assert projected['supersedes_id']=='Q2-resolved'
    assert projected['resolution_carry']['origin_issue_id']==old['body']['resolution_carry']['origin_issue_id']
    assert projected['resolution_carry']['from_issue_id']==old['body']['resolution_carry']['from_issue_id']
    assert projected['resolution_carry']['base_analysis_set_id']==old['body']['resolution_carry']['base_analysis_set_id']
    assert projected['resolution_carry']['scope_check']['from_scope']==old['body']['resolution_carry']['scope_check']['from_scope']
    assert projected['resolution_carry']['scope_check']['to_scope']['model_id']=='NextModel'
    assert projected['resolution_carry']['source_checks']==old['body']['resolution_carry']['source_checks']
    assert projected['answer_ids']==old['body']['answer_ids'] and projected['resolution_event_refs']==old['body']['resolution_event_refs']
    assert q==old


def test_not_applicable_cannot_be_carried_or_flipped_by_structural_code(foundation):
    g=setup(foundation);g.carry('not_applicable','human_review');v=view(g)
    assert v.projection('Question2')['assessment']=='not_applicable' and v.projection('Question2')['blocks']
    g.carry('undetermined')
    with pytest.raises(S02Error,match='carry_obsolete_requires_replacement'):data(g)


@pytest.mark.parametrize('complete',[False,True])
def test_replacement_current_target_and_old_key_preserved(foundation,complete):
    g=setup(foundation);obsolete=g.carry('not_applicable','human_review')['id'];q,t=g.replacement(complete);v=view(g)
    p=v.projection('Question2')
    assert p['branch']=='REPLACEMENT' and p['obsolete_issue_id']==obsolete and p['replacement_issue_id']==t['id']
    assert p['blocks']==(not complete)
    assert {x['body']['issue_key'] for x in v.issues}=={'Question2','NewDecision'}
    g.records[g.current_issue]['body']['resolution_replacement']['replacement_issue_id']='Q2-resolved'
    with pytest.raises(S02Error):data(g)


def test_replacement_structural_continuation_and_rehold(foundation):
    g=setup(foundation);g.carry('not_applicable','human_review');old,t=g.replacement(True)
    b=Budget();before=view(g,b);q=deepcopy(old);q['id']='ReplacementNext';q['body']['supersedes_id']=old['id'];p=q['body']['resolution_replacement']
    p.update(from_issue_id=old['id'],base_analysis_set_id=g.set_id);p['evaluation'].update(method='structural_check',evaluator='H3 pure code')
    g.publish([q],[q['id'],t['id']]);g.current_issue=q['id'];after=view(g,b)
    result=transition(before,after)
    assert next(x for x in result if x['issue_key']=='Question2')['status']=='resolution_replaced'
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1


def test_no_anchor_never_infers_stage_or_deletes_existing_outputs(foundation):
    g=setup(foundation);v=view(g);before=deepcopy(g.kwargs());progress=unassessed_progress(v)
    assert all(p['work_completed_through']==0 and p['outputs']==[] for p in progress.values())
    assert any(p['actual_output_ids'] and p['assessment_state']=='needs_revalidation' for p in progress.values())
    assert g.kwargs()==before


def test_resolved_history_existing_outputs_without_anchor_cannot_build(foundation):
    g=setup(foundation);g.carry();v=view(g);rows=selector_rows(v);work=bind_work(v,rows)
    result=admit(v,rows,*work[:4],candidate_raw=work[4])
    assert result.allowed_units==() and result.blocked_units==tuple(sorted(v.context.source.units))
    assert result.global_blocked and result.eligibility_authorized_in_process is False
    assert result.reason_codes==('PROGRESS_PROOF_REQUIRED',)


@pytest.mark.parametrize('status',['undetermined','not_applicable'])
def test_all_pending_revalidation_states_block(foundation,status):
    g=setup(foundation);g.carry(status,'human_review' if status=='not_applicable' else 'structural_check');v=view(g);rows=selector_rows(v);work=bind_work(v,rows)
    result=admit(v,rows,*work[:4],candidate_raw=work[4])
    assert not result.allowed_units and result.global_blocked
    assert 'BLOCKING_USE' in result.reason_codes


def test_unknown_hold_cannot_shrink_to_an_empty_current_scope(foundation):
    g=setup(foundation);g.carry('undetermined');v=view(g);rows=selector_rows(v,unknown=True);work=bind_work(v,rows)
    result=admit(v,rows,*work[:4],candidate_raw=work[4])
    assert result.reason_codes==('PROGRESS_PROOF_REQUIRED','UNKNOWN_GLOBAL_HOLD')
    assert set(result.materialized_holds[0][1].actions)=={'A1','A2'}


@pytest.mark.parametrize('change',['model','set','history','registry','raw'])
def test_stale_binding_and_source_identity_do_not_authorize_work(foundation,change):
    g=setup(foundation);g.carry();v=view(g);rows=selector_rows(v)
    def mutate(payload):
        if change=='model':payload['base_model_sha256']='0'*64
        if change=='set':payload['base_analysis_set_sha256']='0'*64
        if change=='history':payload['history_sha256']='0'*64
        if change=='registry':payload['historical_reviews_pin']['raw_sha256']='0'*64
        if change=='raw':payload['candidate_sha256']='0'*64
    work=bind_work(v,rows,binding_change=mutate)
    result=admit(v,rows,*work[:4],candidate_raw=work[4]);assert not result.allowed_units
    assert 'BINDING_STALE' in result.reason_codes


def test_current_pair_does_not_follow_a_new_head_silently(foundation):
    g=setup(foundation);h=data(g)
    with pytest.raises(S02Error,match='history_pair_stale'):h.view(g.session,[g.model_id,g.set_id],[g.model_id,'DifferentAS'])


def test_missing_semantic_authority_is_not_filled_from_historical_registry(foundation):
    g=setup(foundation);g.carry('applicable','human_review');v=view(g);rows=selector_rows(v);b,e,grant,t,raw=bind_work(v,rows)
    result=admit(v,rows,b,e,{'trusted':True},t,candidate_raw=raw)
    assert result.allowed_units==() and result.reason_codes==('PROGRESS_PROOF_REQUIRED','SEMANTIC_AUTHORITY_REQUIRED')
