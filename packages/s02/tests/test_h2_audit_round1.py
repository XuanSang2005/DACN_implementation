"""Independent handwritten expectations for H2-A audit round 1 regressions."""
from copy import deepcopy
from dataclasses import replace
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.h2_graph import ModelContext, impact
from dacn_s02.h2_limits import Budget, Limits, references
from dacn_s02.h2_policy import assess_union
from h2_fixtures import (graph, context, work, decide, unit, current_issue,
                         dependency, part, trace, R0, R1)


@pytest.mark.parametrize('target', ['action', 'workflow', 'support'])
@pytest.mark.parametrize('state', ['needs_clarification', 'needs_reanalysis'])
def test_pre_build_attributes_held_scope_failure_to_its_own_unit(target, state):
    m=graph()
    if target == 'support':
        d=dependency(required=None, action='A1');d['trace']=trace('SNAP',R0)
        d.update(consumer_component_id='C1',provider_component_id='C2')
        d['support'][0]['provider_responsibility_ids']=['RS2']
        m['body']['dependencies']=[d]
    else:
        m['body']['actions' if target=='action' else 'workflows'][0]['state']=state
    ctx=context(m);w=work(ctx,selected=(R0,R1));r=decide(w)
    assert r.allowed_units == (unit(ctx,R1),)
    assert r.blocked_units == (unit(ctx,R0),) and r.global_blocked
    assert dict(r.unit_reasons)[unit(ctx,R1)] == ()
    assert r.footprint.actions == {'A1','A2'}  # preserve full request for inspection
    assert 'OBLIGATION_HELD' in dict(r.unit_reasons)[unit(ctx,R0)]


def merged(base, m, w):
    m['id']='M2';m['body'].update(parent_model_id=base.id,revision=2,change_id='Change2')
    after=ModelContext(m,base.source,base.budget)
    return after,assess_union(base,after,w.aset,w.issues,w.selectors,w.binding,
        w.evidence,w.grant,candidate_raw=w.candidate,authority_context=w.authority_context)


@pytest.mark.parametrize('kind',['rule','responsibility'])
@pytest.mark.parametrize('action,allowed',[('A1',False),('A2',True)])
def test_new_membership_is_meaningful_impact_not_read_permission(kind, action, allowed):
    base=context();w=work(base,step=2 if kind=='rule' else 3);m=base.model()
    if kind=='rule':
        new=dict(id='NewRule',trace=trace('SNAP',R1),state='draft',kind='business',statement='Synthetic',action_ids=[action])
        m['body']['rules'].append(new)
    else:
        new=deepcopy(m['body']['responsibilities'][1]);new.update(id='NewRS',trace=trace('SNAP',R1),action_ids=[action])
        m['body']['responsibilities'].append(new)
    after,r=merged(base,m,w)
    assert impact(base,after).after.actions == {action}
    if allowed:
        assert r.allowed_units == (unit(base,R1),) and r.global_blocked
    else:
        assert not r.allowed_units and r.outcome=='rejected'
        assert 'IMPACT_OUTSIDE_WRITE_SCOPE' in r.reason_codes
        assert 'IMPACT_BLOCKING_USE' in r.reason_codes


def test_new_part_cannot_authorize_its_own_bridge_and_whole_candidate_stays_held():
    m=graph();m['body']['mappings'][2].update(parts=[],assessment='not_assessed',issue_ids=['Q'])
    base=context(m);w=work(base,step=4);m=base.model()
    m['body']['mappings'][2].update(assessment='proposed',parts=[part('Bridge',['A1','A2'],['RS1','RS2'])])
    assert decide(w).allowed_units == (unit(base,R1),)
    after,r=merged(base,m,w)
    assert r.footprint.actions=={'A1','A2'}
    assert not r.allowed_units and r.blocked_units==(unit(base,R1),)
    assert r.outcome in ('rejected','guard_required')


def test_post_build_does_not_truncate_independent_unit_when_other_selected_unit_fails():
    base=context();w=work(base,selected=(R0,R1));m=base.model()
    _,r=merged(base,m,w)
    assert r.allowed_units==() and set(r.blocked_units)=={unit(base,R0),unit(base,R1)}
    assert r.outcome=='guard_required'


def test_new_responsibility_context_does_not_pull_other_actions_via_shared_component():
    m=graph();m['body']['responsibilities'][1]['component_id']='C1'
    base=context(m);w=work(base,step=3);m=base.model()
    n=deepcopy(m['body']['responsibilities'][1]);n['id']='NewRS';m['body']['responsibilities'].append(n)
    after,r=merged(base,m,w)
    assert impact(base,after).after.actions=={'A2'}
    assert r.allowed_units==(unit(base,R1),)
    assert base.reverse_impact(['A2']).actions=={'A2'}


@pytest.mark.parametrize('cap,accepted',[(190,False),(204,True)])
def test_result_refs_aggregate_includes_every_current_issue(cap,accepted):
    base=context(budget=Budget(limits=replace(Limits(),refs=cap)))
    issues=[current_issue(base.model(),identity='Q'+str(i),key='K'+str(i)) for i in range(4)]
    for q in issues:
        q['body']['affected']=deepcopy(q['body']['affected'])
        q['body']['affected']['element_ids']=list(base.elements)
    w=work(base,issues=issues,step=3);m=base.model()
    for i in range(20):
        c=deepcopy(m['body']['components'][1]);c['id']='NewC'+str(i)
        c['trace']['issue_ids']=[q['id'] for q in issues];m['body']['components'].append(c)
    m['id']='M2';m['body'].update(parent_model_id=base.id,revision=2,change_id='Change2')
    assert references(dict(model=m,current_issues=issues))==204
    inputs=base.budget.input_refs
    if accepted:
        _,r=merged(base,m,w);assert r.allowed_units==(unit(base,R1),)
    else:
        with pytest.raises(S02Error) as exc:merged(base,m,w)
        assert exc.value.error['code']=='H2_LOCAL_LIMIT'
    assert base.budget.input_refs==inputs  # result checking never resets/charges input
