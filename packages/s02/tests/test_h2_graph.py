from copy import deepcopy
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.h2_graph import ModelContext, impact
from h2_fixtures import graph,context,part,trace,dependency,R0,R1,CR


def test_discovered_parts_expand_all_actions_to_fixed_point():
    m=graph();b=m['body']
    a3=deepcopy(b['actions'][1]);a3.update(id='A3',workflow_ids=[]);b['actions'].append(a3)
    r3=deepcopy(b['responsibilities'][1]);r3.update(id='RS3',action_ids=['A3']);b['responsibilities'].append(r3)
    b['mappings'][0]['parts'] += [part('P12',['A1','A2'],['RS1','RS2']),part('P23',['A2','A3'],['RS2','RS3'])]
    original=deepcopy(m);ctx=context(m);f=ctx.closure(parts=['P1'])
    assert f.actions=={'A1','A2','A3'}
    assert f.parts=={'P1','PCriterion','P2','P12','P23','PN','PC'}
    assert {'C1','C2','RS1','RS2','RS3','W1','W2'}<=f.elements
    assert m==original


def test_shared_component_responsibility_does_not_pull_other_actions():
    m=graph();m['body']['responsibilities'][0]['action_ids']=['A1','A2']
    m['body']['responsibilities'][1]['component_id']='C1'
    ctx=context(m)
    assert ctx.closure(parts=['P1']).actions=={'A1'}
    assert ctx.reverse_impact(['A1']).actions=={'A1'}
    assert ctx.reverse_impact(['C1']).actions=={'A1','A2'}


@pytest.mark.parametrize('required,expected,reasons',[(['A1'],{'A1','A2'},()),([],{'A2'},()),(None,{'A2'},('SCOPE_UNDETERMINED',))])
def test_actual_support_and_unknown(required,expected,reasons):
    m=graph();m['body']['dependencies']=[dependency(required=required)]
    f=context(m).closure(elements=['A2'])
    assert f.actions==expected
    assert f.reasons==reasons


def test_reverse_impact_through_support():
    m=graph();m['body']['dependencies']=[dependency(required=['A1'])]
    assert context(m).reverse_impact(['A1']).actions=={'A1','A2'}


def test_workflow_all_reachable_branches_and_cycle():
    m=graph();b=m['body'];w=b['workflows'][0]
    w['nodes'].append(dict(id='N12',action_id='A2',kind='action',label='Other action'))
    w['edges'] += [dict(id='Branch',**{'from':'N1','to':'N12'},guard='Alternative',trace=trace('SNAP',R1)),dict(id='Loop',**{'from':'N12','to':'N1'},guard=None,trace=trace('SNAP',R1))]
    w['branch_points']=[dict(node_id='N1',mode='exclusive',trace=trace('SNAP'))]
    assert context(m).closure(parts=['P1']).actions=={'A1','A2'}


@pytest.mark.parametrize('mutation',[lambda b:b['mappings'][0].update(source_ref=deepcopy(b['mappings'][2]['source_ref'])) ,lambda b:b['actions'][0].update(rule_ids=['Missing'])])
def test_invalid_inventory_or_ref_rejected(mutation):
    m=graph();mutation(m['body'])
    with pytest.raises(S02Error):context(m)


def test_source_swap_same_parts_and_aggregate_sources_changes_identity():
    m=graph();after=deepcopy(m);a=after['body']['mappings'];a[0]['source_ref'],a[2]['source_ref']=a[2]['source_ref'],a[0]['source_ref'];after['id']='M2'
    base=context(m);new=ModelContext(after,base.source,base.budget);d=impact(base,new)
    assert d.changed_parts=={'P1','P2'}
    assert d.changed_rows=={'Map0','Map2'}
    assert d.before.actions=={'A1','A2'} and d.after.actions=={'A1','A2'}


def test_move_part_rows_and_membership_not_just_part_payload():
    m=graph();after=deepcopy(m);a=after['body']['mappings'];a[1]['parts'].append(a[0]['parts'].pop());after['id']='M2'
    a[0].update(assessment='not_assessed',issue_ids=['Q'])
    base=context(m);new=ModelContext(after,base.source,base.budget);d=impact(base,new)
    assert d.changed_parts=={'P1','PCriterion'}
    assert d.changed_rows=={'Map0','Map1'}
    assert new.part_rows['P1']['id']=='Map1'


def test_set_order_and_revision_pin_are_not_semantic_edits():
    m=graph();after=deepcopy(m);after.update(id='M2',created_at='2026-10-25T00:00:00.000Z');after['body'].update(revision=2,parent_model_id='M1',change_id='Change')
    after['body']['mappings'].reverse();after['body']['actions'].reverse();after['body']['components'].reverse()
    base=context(m);new=ModelContext(after,base.source,base.budget);d=impact(base,new)
    assert not d.changed_elements and not d.changed_parts and not d.changed_rows
    assert not d.before.elements and not d.after.elements


def test_workflow_array_order_is_preserved_in_context_identity():
    m=graph();after=deepcopy(m);after['body']['workflows'][0]['nodes'].reverse()
    base=context(m);new=ModelContext(after,base.source,base.budget)
    assert impact(base,new).changed_elements=={'W1'}


def test_removal_uses_old_graph_as_well_as_new():
    m=graph();m['body']['dependencies']=[dependency(required=['A1'])]
    after=deepcopy(m);after['body']['dependencies']=[]
    base=context(m);new=ModelContext(after,base.source,base.budget);d=impact(base,new)
    assert d.changed_elements=={'D21'}
    assert d.before.actions=={'A1','A2'}
    assert d.after.elements==frozenset()


def test_context_and_source_are_detached_from_original_inputs():
    from h2_fixtures import snapshot
    s=snapshot();m=graph();ctx=context(m,snap=s)
    s['input']['functional_requirements'][0]['text']='Caller changed after construction'
    m['body']['actions'][0]['name']='Mutation'
    assert ctx.elements['A1']['name']=='Action 1'
    assert ctx.source._input['functional_requirements'][0]['text']!='Caller changed after construction'


def test_source_criterion_order_is_not_a_semantic_set_even_with_same_ids():
    from h2_fixtures import snapshot,HASH
    from dacn_s02.h2_contracts import SourceInventory
    s=snapshot();s['input']['functional_requirements'][0]['acceptance_criteria']=['First','Second']
    m=graph();row=deepcopy(m['body']['mappings'][1]);row.update(id='Criterion2',source_ref=dict(snapshot_id='SNAP',input_pointer=R0+'/acceptance_criteria/1'))
    row['parts'][0]['id']='CriterionPart2';m['body']['mappings'].append(row)
    base=context(m,snap=s);new_source=deepcopy(s);new_source['input']['functional_requirements'][0]['acceptance_criteria'].reverse()
    after=ModelContext(m,SourceInventory(new_source,'SRC',HASH,base.budget),base.budget)
    assert impact(base,after).source_changed


def test_unknown_branch_retains_all_reachable_actions_but_is_undetermined():
    m=graph();w=m['body']['workflows'][0]
    w['edges'].append(dict(id='Alternative',**{'from':'N1','to':'E1'},guard='Unknown alternative',trace=trace('SNAP')))
    w['branch_points']=[dict(node_id='N1',mode='unknown',trace=trace('SNAP'))]
    f=context(m).closure(parts=['P1'])
    assert f.actions=={'A1'} and 'SCOPE_UNDETERMINED' in f.reasons
