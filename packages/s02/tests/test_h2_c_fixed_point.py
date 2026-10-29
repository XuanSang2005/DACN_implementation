"""Handwritten graph topologies; expected sets never call a scope algorithm.

These are pure synthetic graph controls, separately labelled from handler
traces. Support/dependencies are not injected into the step 1-4 writer.
"""
from copy import deepcopy
import pytest
from h2_fixtures import graph,context,part,trace,dependency,work,decide,R0,R1
from dacn_s02.h2_graph import ModelContext,impact
from dacn_s02.h2_policy import assess_union


def chain(*,parts=True):
    model=graph()
    body=model['body']
    body['workflows']=[]
    template=deepcopy(body['actions'][1])
    body['actions']=[]
    for i in range(1,13):
        action=deepcopy(template)
        action.update(id=f'A{i}',name=f'Action {i}',workflow_ids=[],trace=trace('SNAP',R0 if i==1 else R1))
        body['actions'].append(action)
    body['responsibilities'][0]['action_ids']=['A1']
    body['responsibilities'][1]['action_ids']=[f'A{i}' for i in range(2,13)]
    if parts:
        body['mappings'][2]['parts'] += [part(f'Bridge{i}',[f'A{i}',f'A{i+1}'],['RS1','RS2']) for i in range(1,12)]
    else:
        for row in body['mappings']:row.update(parts=[],assessment='not_assessed',issue_ids=['Q'])
        w=dict(id='Wchain',name='Ordered chain',state='draft',trace=trace('SNAP',R1),
               entry_node_id='N1',nodes=[dict(id=f'N{i}',action_id=f'A{i}',kind='action',label=f'{i}') for i in range(1,13)],
               edges=[dict(id=f'E{i}',**{'from':f'N{i}','to':f'N{i+1}'},guard=None,trace=trace('SNAP',R1)) for i in range(1,12)],branch_points=[])
        body['workflows']=[w]
        for action in body['actions']:action['workflow_ids']=['Wchain']
    return model


@pytest.mark.parametrize('parts',[False,True])
def test_twelve_actions_fixed_point_before_and_after_parts(parts):
    model=chain(parts=parts)
    ctx=context(model)
    before=deepcopy(model)
    footprint=ctx.closure(elements=['A1'])
    assert footprint.actions=={'A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12'}
    if parts:
        assert footprint.parts=={'P1','PCriterion','P2','PN','PC','Bridge1','Bridge2','Bridge3','Bridge4',
                                 'Bridge5','Bridge6','Bridge7','Bridge8','Bridge9','Bridge10','Bridge11'}
        assert not footprint.reasons
    else:
        assert footprint.parts==set() and footprint.reasons==('ACTION_WITHOUT_PART',)
    assert ctx.reverse_impact(['A12']).actions==footprint.actions
    assert model==before


def test_new_last_bridge_recomputes_union_and_both_reverse_sides():
    model=chain()
    # Initially two connected groups {A1..A6}, {A7..A12}. U holds A1.
    model['body']['mappings'][2]['parts']=[p for p in model['body']['mappings'][2]['parts'] if p['id']!='Bridge6']
    before=context(model)
    assert before.closure(elements=['A12']).actions=={'A7','A8','A9','A10','A11','A12'}
    after_model=deepcopy(model)
    after_model['id']='M-joined'
    after_model['body'].update(parent_model_id=model['id'],revision=model['body']['revision']+1,change_id='Change-joined')
    after_model['body']['mappings'][2]['parts'].append(part('Bridge6',['A6','A7'],['RS2']))
    after=ModelContext(after_model,before.source,before.budget)
    delta=impact(before,after)
    # Adding membership changes context for every Part in Map2, including
    # Parts in BOTH old groups. Their payloads alone were unchanged.
    assert delta.changed_parts=={'P2','Bridge1','Bridge2','Bridge3','Bridge4','Bridge5',
                                 'Bridge6','Bridge7','Bridge8','Bridge9','Bridge10','Bridge11'}
    assert delta.changed_rows=={'Map2'}
    assert delta.before.actions=={'A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12'}
    assert delta.after.actions=={'A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12'}
    reverse=impact(after,before)
    assert reverse.before.actions==delta.after.actions and reverse.after.actions==delta.before.actions
    # Existing proposed row mutation is outside append rights, even if the
    # caller claims independence. This pure control does not authorize a writer.
    w=work(before,step=4)
    result=assess_union(before,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,
                        candidate_raw=w.candidate,authority_context=w.authority_context)
    assert result.outcome=='rejected' and not result.allowed_units


def test_new_mapping_bridge_expands_twelve_actions_and_requires_guard():
    model=chain()
    model['body']['mappings'][2].update(parts=[],assessment='not_assessed',issue_ids=['Q'])
    before=context(model)
    w=work(before,step=4)
    assert decide(w).allowed_units==tuple(w.binding.payload()['unit_ids'])
    candidate=deepcopy(model)
    candidate['id']='M-new-parts'
    candidate['body'].update(parent_model_id=model['id'],revision=model['body']['revision']+1,change_id='Change-new-parts')
    candidate['body']['mappings'][2].update(assessment='proposed',issue_ids=[],parts=[
        part(f'NewBridge{i}',[f'A{i}',f'A{i+1}'],['RS1','RS2']) for i in range(1,12)])
    after=ModelContext(candidate,before.source,before.budget)
    result=assess_union(before,after,w.aset,w.issues,w.selectors,w.binding,w.evidence,w.grant,
                        candidate_raw=w.candidate,authority_context=w.authority_context)
    assert result.outcome=='guard_required' and not result.allowed_units
    assert 'BLOCKING_USE' in result.reason_codes
    assert result.footprint.actions=={'A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12'}
    assert before.model()==model


@pytest.mark.parametrize('required',[['A1'],None,[]])
def test_support_actual_required_actions_and_unknown_are_distinct(required):
    model=graph()
    model['body']['dependencies']=[dependency(required=required)]
    ctx=context(model)
    footprint=ctx.closure(elements=['A2'])
    assert footprint.actions==({'A1','A2'} if required==['A1'] else {'A2'})
    assert ('SCOPE_UNDETERMINED' in footprint.reasons)==(required is None)
    result=decide(work(ctx))
    assert bool(result.allowed_units)==(required==[])


@pytest.mark.parametrize('edit',['swap_sources','reparent'])
def test_same_part_payload_and_total_sources_do_not_prove_reuse(edit):
    base=context()
    model=base.model()
    rows=model['body']['mappings']
    if edit=='swap_sources':rows[0]['source_ref'],rows[2]['source_ref']=rows[2]['source_ref'],rows[0]['source_ref']
    else:rows[0]['parts'],rows[2]['parts']=rows[2]['parts'],rows[0]['parts']
    after=context(model)
    assert base.parts==after.parts
    assert {r['source_ref']['input_pointer'] for r in base.rows.values()}=={r['source_ref']['input_pointer'] for r in after.rows.values()}
    delta=impact(base,after)
    assert {'P1','P2'}<=delta.changed_parts
    assert delta.before.actions==delta.after.actions=={'A1','A2'}


def test_reorder_sets_and_revision_metadata_have_no_meaningful_impact():
    base=context()
    model=base.model()
    model['id']='M-reordered'
    model['body'].update(revision=2,parent_model_id=base.id,change_id='Change',created_by_run_id='Run2')
    for key in ('actions','components','responsibilities','mappings'):
        model['body'][key].reverse()
    after=context(model)
    delta=impact(base,after)
    assert not delta.source_changed
    assert delta.changed_elements==delta.changed_parts==delta.changed_rows==set()
    assert delta.before.actions==delta.after.actions==set()
