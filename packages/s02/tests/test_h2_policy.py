from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import pytest
from helpers import trace
from dacn_s02.errors import S02Error
from dacn_s02.codec_boundary import encode
from dacn_s02.h2_graph import ModelContext
from dacn_s02.h2_policy import admit,assess_union,materialize
from dacn_s02.h2_contracts import ConstructionPermit,AuthorityContext
from h2_fixtures import graph,context,work,decide,unit,current_issue,dependency,part,R0,R1,CR,HASH


def test_independent_v_advances_u_keeps_hold_and_input_immutable():
    ctx=context();w=work(ctx);original=deepcopy((ctx.model(),w.aset,w.issues))
    result=decide(w)
    assert result.allowed_units==(unit(ctx,R1),) and not result.blocked_units
    assert result.global_blocked and result.footprint.actions=={'A2'}
    assert (ctx.model(),w.aset,w.issues)==original


def test_held_u_can_be_selected_without_blocking_independent_v():
    ctx=context();w=work(ctx,selected=(R0,R1));result=decide(w)
    assert result.allowed_units==(unit(ctx,R1),)
    assert result.blocked_units==(unit(ctx,R0),)
    assert 'OBLIGATION_HELD' in dict(result.unit_reasons)[unit(ctx,R0)]


def test_empty_graph_is_not_independence_proof():
    ctx=context(graph(skeleton=True));w=work(ctx,all_source=True)
    r=decide(w)
    assert not r.allowed_units and 'UNKNOWN_GLOBAL_HOLD' in r.reason_codes
    assert not r.footprint.actions and r.global_blocked
    assert materialize(ctx,w.selectors[0],w.issues[0]).elements=={'Actor'}


def test_pre_parts_positive_needs_full_source_basis_and_external_grant():
    ctx=context(graph(skeleton=True));w=work(ctx)
    assert decide(w).allowed_units==(unit(ctx,R1),)
    result=admit(ctx,w.aset,w.issues,w.selectors,w.binding,w.evidence,None,candidate_raw=w.candidate,authority_context=w.authority_context)
    assert not result.allowed_units and result.reason_codes==('AUTHORITY_REQUIRED',)


@pytest.mark.parametrize('change',[
 lambda e:e['independence'].clear(),
 lambda e:e['independence'][0].update(verdict='unknown'),
 lambda e:e['independence'][0].update(basis_source_refs=[dict(snapshot_id='SNAP',input_pointer=R1)]),
 lambda e:e['inspections'][0].update(read='not_inspected',verdict='held'),
])
def test_missing_semantic_basis_never_inferred_from_disjoint_graph(change):
    w=work(context(),evidence_change=change);r=decide(w)
    assert not r.allowed_units
    assert set(r.reason_codes)&{'INDEPENDENCE_NOT_PROVED','INDEPENDENCE_INVENTORY_UNINSPECTED'}


@pytest.mark.parametrize('change,reason',[
 (lambda b:b.update(base_analysis_set_sha256='2'*64),'ANALYSIS_STALE'),
 (lambda b:b.update(base_model_sha256='2'*64),'ANALYSIS_STALE'),
 (lambda b:b.update(current_selectors_sha256='2'*64),'ANALYSIS_STALE'),
 (lambda b:b.update(analysis_sha256='2'*64),'ANALYSIS_STALE'),
 (lambda b:b.update(candidate_sha256='2'*64),'RAW_BINDING_MISMATCH'),
])
def test_stale_pins_reject_even_new_grant_for_bad_tuple(change,reason):
    w=work(context(),binding_change=change)
    assert decide(w).reason_codes==(reason,)


@pytest.mark.parametrize('field,value',[('binding_key','3'*64),('provider_id','other'),('provider_version','local-synthetic/0'),('control_sha256','3'*64),('decision','deny'),('decision','unavailable')])
def test_authority_tuple_and_external_process_context(field,value):
    w=work(context());g=replace(w.grant,**{field:value})
    assert not decide(w,grant=g).allowed_units
    assert not decide(w,authority_context={}).allowed_units


def test_payload_trusted_flag_is_not_an_authority_contract():
    w=work(context())
    assert decide(w,grant={'trusted':True,'binding_key':w.binding.key}).reason_codes==('AUTHORITY_REQUIRED',)


def test_shared_unchanged_component_not_a_blocker_but_explicit_component_is():
    m=graph();m['body']['responsibilities'][1]['component_id']='C1'
    ctx=context(m);w=work(ctx)
    assert decide(w).allowed_units==(unit(ctx,R1),)
    q=current_issue(m,elements=('C1',),parts=())
    w=work(context(m),issues=[q]);assert not decide(w).allowed_units


@pytest.mark.parametrize('required',[['A1'],None])
def test_real_support_bridge_or_unknown_blocks_independent_claim(required):
    m=graph();m['body']['dependencies']=[dependency(required=required)]
    w=work(context(m));assert not decide(w).allowed_units


def test_source_selector_survives_graph_growth():
    base=context(graph(skeleton=True));w=work(base,all_source=True)
    m=graph();m.update(id='M2');after=ModelContext(m,base.source,base.budget)
    held=materialize(after,w.selectors[0],w.issues[0])
    assert held.actions=={'A1','A2'}
    assert held.parts=={'P1','PCriterion','P2','PN','PC'}


def test_current_inventory_missing_selector_or_stale_issue_rejected():
    w=work(context())
    with pytest.raises(S02Error):admit(w.ctx,w.aset,w.issues,[],w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    w.issues[0]['body']['model_id']='Old'
    with pytest.raises(S02Error):decide(w)


def test_missing_criterion_cannot_be_hidden_by_a_requirement_part():
    def omit(e):e['inspections']=[row for row in e['inspections'] if row['source_ref']['input_pointer']!=CR]
    with pytest.raises(S02Error):work(context(),evidence_change=omit)


def test_current_blocker_cannot_be_narrowed_by_selector_payload():
    with pytest.raises(S02Error):
        decide(work(context(),selector_change=lambda s:s.update(element_ids=[])))


def test_unassigned_action_not_waived_by_old_issue_or_pending_role():
    m=graph();m['body']['responsibilities'][1]['action_ids']=[]
    w=work(context(m),step=3,selector_change=lambda s:s.update(code_task_role='await_builder'))
    assert 'UNASSIGNED_ACTION' in decide(w,phase='post').reason_codes


def test_real_gap_does_not_borrow_construction_exemption():
    ctx=context();q=current_issue(ctx.model(),elements=('A2',),parts=('P2',),kind='analysis_omission')
    w=work(ctx,issues=[q],selector_change=lambda s:s.update(code_task_role='await_builder'))
    fake=ConstructionPermit(q['id'],q['body']['issue_key'],'Cmd','Run',HASH,frozenset([unit(ctx,R1)]),3,'await_builder')
    assert not decide(w,permits=[fake]).allowed_units


def test_only_checked_code_construction_permit_waives_build_not_global_hold():
    ctx=context();u=unit(ctx,R1);key='h2.construct.'+sha256(encode(['Cmd',[u],3,'await_builder'])).hexdigest()
    q=current_issue(ctx.model(),elements=('A2',),parts=('P2',),key=key,kind='verification');q['body']['trace']=trace('SNAP',R1)
    def inspection(e):
        for row in e['inspections']:row.update(verdict='usable',needed_facts=[])
    def selector(s):s.update(source_refs=[dict(snapshot_id='SNAP',input_pointer=R1)],target_step=3,code_task_role='await_builder')
    w=work(ctx,issues=[q],step=3,evidence_change=inspection,selector_change=selector)
    p=ConstructionPermit(q['id'],key,'Cmd','Run',HASH,frozenset([u]),3,'await_builder')
    assert not decide(w).allowed_units
    r=decide(w,permits=[p]);assert r.allowed_units==(u,) and r.global_blocked
    assert q['body']['status']=='open'  # no Issue resolution/publication


def test_union_recomputes_new_part_bridge_and_never_truncates_candidate():
    m=graph();m['body']['mappings'][2].update(parts=[],assessment='not_assessed',issue_ids=['Q'])
    base=context(m);w=work(base,step=4)
    candidate=deepcopy(m);candidate.update(id='M2');candidate['body']['mappings'][2].update(parts=[part('P12',['A1','A2'],['RS1','RS2'])],assessment='proposed')
    candidate['body'].update(parent_model_id=base.id,revision=base.body['revision']+1,change_id='Change2')
    after=ModelContext(candidate,base.source,base.budget)
    assert decide(w).allowed_units==(unit(base,R1),)
    r=assess_union(base,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    assert r.outcome=='guard_required' and not r.allowed_units
    assert r.footprint.actions=={'A1','A2'}
    assert 'BLOCKING_USE' in r.reason_codes


def test_valid_append_mapping_positive_control():
    m=graph();m['body']['mappings'][2].update(parts=[],assessment='not_assessed',issue_ids=['Q'])
    base=context(m);w=work(base,step=4);candidate=deepcopy(m);candidate['id']='M2'
    candidate['body']['mappings'][2].update(parts=[part('P2',['A2'],['RS2'])],assessment='proposed')
    candidate['body'].update(parent_model_id=base.id,revision=base.body['revision']+1,change_id='Change2')
    after=ModelContext(candidate,base.source,base.budget)
    r=assess_union(base,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    assert r.outcome=='assessed' and r.allowed_units==(unit(base,R1),) and r.global_blocked


@pytest.mark.parametrize('change',[
 lambda b:b['actions'][0].update(name='Edited'),
 lambda b:b['mappings'][0].update(source_ref=deepcopy(b['mappings'][2]['source_ref'])),
 lambda b:b['mappings'][0]['parts'].append(b['mappings'][1]['parts'].pop()),
])
def test_existing_output_or_row_relation_cannot_be_changed(change):
    base=context();w=work(base,step=4);candidate=base.model();candidate['id']='M2';change(candidate['body'])
    # Keep inventory/empty-row structure valid for relation edits.
    if candidate['body']['mappings'][0]['source_ref']==candidate['body']['mappings'][2]['source_ref']:
        candidate['body']['mappings'][2]['source_ref']=dict(snapshot_id='SNAP',input_pointer=R0)
    for row in candidate['body']['mappings']:
        if not row['parts']:row.update(assessment='not_assessed',issue_ids=['Q'])
    candidate['body'].update(parent_model_id=base.id,revision=base.body['revision']+1,change_id='Change2')
    after=ModelContext(candidate,base.source,base.budget)
    r=assess_union(base,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    assert r.outcome=='rejected' and not r.allowed_units


def test_unblocked_positive_control_is_still_not_business_acceptance():
    ctx=context();w=work(ctx,issues=[],step=4)
    r=decide(w,phase='post')
    assert r.allowed_units==(unit(ctx,R1),) and not r.global_blocked
    assert r.outcome=='assessed' and not hasattr(r,'accepted_scope')


def test_explicit_actor_blocker_cannot_be_waived_by_source_independence():
    m=graph();m['body']['actions'][1].update(initiator='external',actor_ids=['Actor'])
    ctx=context(m);q=current_issue(m,elements=('Actor',),parts=())
    r=decide(work(ctx,issues=[q]))
    assert not r.allowed_units and 'BLOCKING_USE' in r.reason_codes


def test_successor_identity_is_required_even_when_body_mapping_is_valid():
    base=context();w=work(base,step=4);m=base.model();m['id']='M2'
    after=ModelContext(m,base.source,base.budget)
    r=assess_union(base,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)
    assert r.outcome=='rejected' and r.reason_codes==('MODEL_SUCCESSOR_PIN',)


@pytest.mark.parametrize('decision',['unavailable','invalid'])
def test_failed_authority_decision_can_have_unread_identity_without_grant(decision):
    from dacn_s02.h2_contracts import AuthorityGrant
    w=work(context());g=AuthorityGrant(w.binding.key,None,None,None,decision,'External caller reports failure')
    assert decide(w,grant=g).reason_codes==('AUTHORITY_'+decision.upper(),)


def test_existing_part_gap_cannot_borrow_unrelated_issue_even_before_step4():
    m=graph();m['body']['mappings'][2]['parts'][0].update(assignment='blocked',remaining_gap='Unknown',issue_ids=['Q'])
    w=work(context(m),step=2)
    assert 'PART_GAP' in decide(w).reason_codes and not decide(w).allowed_units


def test_existing_unknown_initiator_stays_held_even_before_extraction():
    m=graph();m['body']['actions'][1]['initiator']='unknown'
    w=work(context(m),step=2)
    assert 'INITIATOR_UNKNOWN' in decide(w).reason_codes and not decide(w).allowed_units
