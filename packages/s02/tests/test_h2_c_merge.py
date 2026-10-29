"""New bridges, contextual negatives and unknown holds through real handlers."""
from copy import deepcopy
import pytest

from h2_c_fixtures import ManyCase
from test_h2_c_stress import invariant, published
from dacn_s02.h2_service import H2Service


@pytest.mark.parametrize('completed', [2,4])
@pytest.mark.parametrize('blocking', [False,True])
def test_new_cross_source_relation_checks_retained_output_before_and_after_parts(tmp_path, completed, blocking):
    c = ManyCase(tmp_path)
    c.bootstrap()
    c.execute(*c.work(1), 'inspect U held')
    for step in range(2,completed+1):
        c.execute(*c.unit_work(step,1), f'V1 stage {step}')
    model = deepcopy(c.last['result']['model'])
    before = c.pair[:]
    outputs = deepcopy(c.meta['progress_by_unit'][c.v]['outputs'])
    target = c.handle('actions',1)
    if completed == 4:
        row = next(r for r in model['body']['mappings'] if r['source_ref']['input_pointer']=='/functional_requirements/1')
        target = next(h for h,x in c.aliases().items() if x['id']==row['parts'][0]['id'])

    def relation(candidate, analysis):
        candidate['proposals']['findings'] = [dict(
            handle='new-u-relation',kind='business',question='U fact still unknown',
            reason='Synthetic new relation to retained V1',trace=c.tr('/functional_requirements/0'),
            affected_refs=[dict(base_handle=target)],
            blocking_refs=[dict(base_handle=target)] if blocking else [],impact_known=True)]

    result = c.execute(*c.unit_work(2,2,change=relation), 'new relation')
    assert result['status'] == 'blocked'
    _, plan = published(c,result['command_id'])
    assert c.meta['progress_by_unit'][c.v]['outputs'] == outputs
    assert c.meta['progress_by_unit'][c.v]['work_completed_through'] == completed
    if blocking:
        assert result['result']['candidate_outcome']=='guard_only'
        assert c.pair[0]==before[0] and c.pair[1]!=before[1]
        assert c.last['result']['model']==model
        assert c.meta['progress_by_unit'][c.unit(2)]['work_completed_through']==1
        assert c.meta['progress_by_unit'][c.v]['assessment_state']=='needs_revalidation'
        assert not any(r['type'] in ('model','change') for r in plan['batch']['records'])
        # A real candidate was built and discarded, with physical blocker to a
        # retained action/Part. It is not the pre-admission proof=False shortcut.
        guard = next(iter(c.meta['guards'].values()))
        assert guard['failed_candidate_model'] is not None
        assert 'NEW_OUTPUT_HOLD' in guard['reason_codes']
        assert guard['failed_candidate_model']['id'] not in final_records(c,result['command_id'])
        old_command = result['command_id']
        c.execute(*c.unit_work(completed,1,mode='revalidate',goal='retained_output',guards=list(c.meta['guards'])), 'discard bridge, assess retained V1')
        assert c.last['result']['model']==model
        assert c.meta['progress_by_unit'][c.v]['outputs']==outputs
        assert c.meta['progress_by_unit'][c.v]['work_completed_through']==completed
        assert H2Service(c.repo).resume(old_command)['result']['candidate_outcome']=='guard_only'
        # Explicit NEW projection omits the rejected relation. Old raw is never
        # replayed, and no blocked candidate allocation becomes a domain Record.
        next_result=c.execute(*c.unit_work(2,2),'new V2 without bridge')
        assert next_result['result']['candidate_outcome']=='valid'
    else:
        assert result['result']['candidate_outcome']=='valid'
        assert c.meta['progress_by_unit'][c.unit(2)]['work_completed_through']==2
        assert c.meta['progress_by_unit'][c.v]['assessment_state']=='current'
        assert not c.meta['guards']


def final_records(case,command):
    from test_h2_checkpoint_processes import final
    return final(case,command)[0]['state']['records']


def test_unknown_selector_survives_empty_graph_and_all_new_units(tmp_path):
    c=ManyCase(tmp_path)
    c.bootstrap()
    def unknown(candidate,analysis):
        candidate['proposals']['findings'][0]['impact_known']=False
    c.execute(*c.work(1,change=unknown),'unknown applicability on empty graph')
    base=deepcopy(c.last['result']['model'])
    result=c.execute(*c.unit_work(2,6),'V6 cannot escape unknown global hold')
    assert result['result']['candidate_outcome']=='guard_only'
    assert c.last['result']['model']==base and not base['body']['actions']
    assert all(p['work_completed_through']==1 for p in c.meta['progress_by_unit'].values())
    result=c.execute(*c.unit_work(2,6,mode='revalidate',goal='admission',guards=list(c.meta['guards'])),
                     'independence claim cannot narrow unknown business hold')
    assert result['status']=='blocked'
    assert c.last['result']['model']==base
    assert c.meta['progress_by_unit'][c.unit(6)]['assessment_state']!='current'
    q=next(q for q in c.last['result']['issues'] if q['body']['kind']=='business')
    assert q['body']['status']=='open'
    assert c.meta['selectors'][q['body']['issue_key']]['kind']=='all_source_uses'


def test_shared_component_does_not_pull_six_family_context_into_new_scope(tmp_path):
    c=ManyCase(tmp_path)
    c.bootstrap()
    c.execute(*c.work(1),'inspect')
    for step in (2,3,4):c.execute(*c.unit_work(step,1),f'V1 stage {step}')
    old=deepcopy(c.last['result']['model'])
    progress=deepcopy(c.meta['progress_by_unit'])
    c.execute(*c.unit_work(2,2),'V2 action')
    def share(candidate,analysis):
        candidate['proposals']['components']=[]
        candidate['proposals']['responsibilities'][0]['component_id']=dict(base_handle=c.handle('components',1))
    result=c.execute(*c.unit_work(3,2,change=share),'V2 shares context only')
    assert result['result']['candidate_outcome']=='valid'
    assert len(c.last['result']['model']['body']['components'])==1
    assert len(c.last['result']['model']['body']['responsibilities'])==2
    assert c.meta['progress_by_unit'][c.v]['outputs']==progress[c.v]['outputs']
    assert c.meta['progress_by_unit'][c.v]['assessment_state']=='current'
    assert not c.meta['guards']
    assert c.last['result']['model']['body']['components']==old['body']['components']
