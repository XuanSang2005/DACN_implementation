"""P1 a2: independent task/target scopes and operation identities.

All review decisions and business graphs here are synthetic test inputs.
"""
from copy import deepcopy
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.profiles import E1, L1
from dacn_s02.repository import record
from dacn_s02.scope import make_scope
from helpers import operation, issue, allscope
from profile_fixtures import graph, fullfoot, scope_proof
from test_repository import validation


def prepared(g, profile=E1):
    op=operation(g.session,g.context,(g.model_id,g.set_id));cmd=op['command_id']
    g.commands[cmd]=op;g.operation_profiles[cmd]=profile
    g.events[cmd,'prep']=dict(event_id='prep',command_id=cmd,ordinal=1,kind='prepared',payload=dict(stage_refs=[],attempt_id=None))
    return op


@pytest.mark.parametrize('profile',[L1,E1])
@pytest.mark.parametrize('collision',['published','prepared','identity'])
def test_operation_identity_before_dispatch(foundation,profile,collision):
    g=graph(foundation);first=prepared(g,profile);second=prepared(g,profile);g.check()
    if collision=='identity':
        second['command_id']='DifferentIdentity';code='graph_operation_identity'
    else:
        second['reserved_run_id']=first['reserved_run_id'] if collision=='prepared' else g.records['M2']['body']['created_by_run_id']
        code='graph_reserved_run_unique'
    # An unknown profile must not mask contradictory operation identities.
    g.operation_profiles[next(iter(g.commands))]='unknown-profile'
    with pytest.raises(S02Error,match=code):g.check()


def task_graph(foundation, task_elements, evidence_elements, *, old=False):
    g=graph(foundation)
    task=dict(step=1,scope=make_scope('M2',task_elements),reason='Synthetic scoped reanalysis',status='pending',evidence_record_ids=[])
    g.records['CH1']['body']['reevaluate']=[task]
    if old==2:g.carry(new_model=True)
    carry=g.carry('not_applicable','human_review',new_model=bool(old))
    q,target=g.replacement(True)
    e=issue(g.records[g.model_id],'TaskEvidence',key='ScopedTask',status='resolved',blocked=evidence_elements,parts=[])
    e['body'].update(kind='verification',resolution='Synthetic task evidence',blocking=make_scope(g.model_id),resolution_carry=None,resolution_replacement=None)
    g.add(e);s=g.records[g.set_id];s['body']['issue_ids'].append(e['id']);s['body']['changed_record_ids'].append(e['id'])
    v=validation(g.records[g.model_id],s,'TaskValidation')
    v['body']['completed_change_tasks']=[dict(change_id='CH1',task_index=0,evidence_record_ids=[e['id']])];g.add(v)
    q['body']['resolution_replacement']['evaluation']['evidence_record_ids'].append(v['id'])
    g.review(q['id']);return g,carry,q,e


@pytest.mark.parametrize('old',[False,True,2])
@pytest.mark.parametrize('task,evidence,valid',[
    (['A1'],['A1'],True),(['A2'],['A2'],True),
    (['A1','A2'],['A1'],False),(['A1','Actor'],['A1'],False),
])
def test_attestation_covers_task_not_replacement(foundation,old,task,evidence,valid):
    g,_,_,_=task_graph(foundation,task,evidence,old=old)
    before=deepcopy(g.kwargs())
    if valid:g.check()
    else:
        with pytest.raises(S02Error,match='replacement_task_(scope|correspondence)'):g.check()
    assert g.kwargs()==before


@pytest.mark.parametrize('mutation',['missing','removed','unrelated'])
def test_old_task_requires_explicit_correspondence(foundation,mutation):
    g,c,q,e=task_graph(foundation,['A1'],['A1'],old=True);g.check()
    pairs=c['body']['resolution_carry']['scope_check']['element_pairs']
    pair=next(p for p in pairs if p['from']['element_id']=='A1')
    if mutation=='missing':pairs.remove(pair)
    elif mutation=='removed':pair.update(to=None,relation='removed')
    else:
        # Task outside the declared proof cannot be inferred from same-ID evidence.
        g.records['CH1']['body']['reevaluate'][0]['scope']['element_ids'].append('Actor')
        e['body']['affected']['element_ids'].append('Actor')
    for identity in list(g.reviews):g.review(identity)
    with pytest.raises(S02Error,match='replacement_task_correspondence'):g.check()


def replacement_successor(g, old, target, *, new_model=False):
    mid=g.model_id;m=deepcopy(g.records[mid]) if new_model else None
    if m:m['id']='M-next';m['body'].update(parent_model_id=mid,revision=m['body']['revision']+1,change_id='CH-next')
    newmid=m['id'] if m else mid
    q=deepcopy(old);q['id']='Replacement-next';q['body'].update(model_id=newmid,supersedes_id=old['id'],affected=fullfoot(newmid),blocking=make_scope(newmid))
    nt=deepcopy(target);nt['id']='Target-next';nt['body'].update(model_id=newmid,supersedes_id=target['id'])
    for field in ('affected','blocking'):nt['body'][field]['model_id']=newmid
    p=q['body']['resolution_replacement'];p.update(from_issue_id=old['id'],base_analysis_set_id=g.set_id,replacement_issue_id=nt['id'],change_id=m['body']['change_id'] if m else None,scope_check=scope_proof(mid,newmid))
    p['evaluation'].update(method='structural_check',evaluator='synthetic-code',evidence_record_ids=[nt['id']])
    for check in p['obligation_checks']:check['evidence_record_ids']=[nt['id']]
    items=[q,nt]
    if m:items.append(record('change','CH-next',dict(base_model_id=mid,new_model_id=newmid,kind='analysis_edit',old_source_context_id=g.context,new_source_context_id=g.context,reason='Synthetic independent revision',source_record_ids=[old['id']],application_event_refs=[],operations=[],affected=allscope(m),reused=[],reevaluate=[],invalidated_bundle_ids=[])))
    return q,nt,m,items


@pytest.mark.parametrize('new_model',[False,True])
@pytest.mark.parametrize('mode',['unchanged','expanded','reordered','hold','review','stale_review'])
def test_target_footprint_has_own_continuation_gate(foundation,new_model,mode):
    g=graph(foundation);g.carry('not_applicable','human_review');old,t=g.replacement(True);g.check()
    q,nt,m,items=replacement_successor(g,old,t,new_model=new_model)
    p=q['body']['resolution_replacement']
    if mode in ('expanded','hold','review','stale_review'):nt['body']['affected']['element_ids'].append('Actor')
    if mode=='reordered':nt['body']['affected']['element_ids'].reverse()
    if mode=='hold':p['assessment']='incomplete';q['body'].update(status='resolution_pending_revalidation',blocking=fullfoot(q['body']['model_id']))
    if mode in ('review','stale_review'):p['evaluation'].update(method='human_review',evaluator='SYNTHETIC REVIEWER')
    g.publish(items,[q['id'],nt['id']],new_model=m)
    if mode=='review':g.review(q['id'])
    if mode=='stale_review':g.reviews[q['id']]=g.reviews[old['id']]
    if mode in ('expanded','stale_review'):
        with pytest.raises(S02Error,match='replacement_target_footprint|resolution_human_evidence_binding'):g.check()
    else:g.check()


def test_target_impact_values_outside_replacement_require_review(foundation):
    g=graph(foundation);g.carry('not_applicable','human_review');old,t=g.replacement(True)
    t['body']['affected']['element_ids'].append('Actor');g.review(old['id']);g.check()
    q,nt,m,items=replacement_successor(g,old,t,new_model=True)
    actor=next(e for e in m['body']['actors'] if e['id']=='Actor');actor['name']='Changed actor description'
    g.publish(items,[q['id'],nt['id']],new_model=m)
    with pytest.raises(S02Error,match='replacement_target_footprint'):g.check()


@pytest.mark.parametrize('covered',[False,True])
def test_task_part_coverage_is_not_action_coverage(foundation,covered):
    g,_,q,e=task_graph(foundation,['A1'],['A1'])
    g.records['CH1']['body']['reevaluate'][0]['scope']['mapping_part_ids']=['P1']
    if covered:e['body']['affected']['mapping_part_ids']=['P1']
    for identity in list(g.reviews):g.review(identity)
    if covered:g.check()
    else:
        with pytest.raises(S02Error,match='replacement_task_scope'):g.check()


def test_modified_old_task_requires_current_evidence_with_reviewed_pairs(foundation):
    g,c,q,e=task_graph(foundation,['A1'],['A1'],old=True)
    g.records[g.model_id]['body']['actions'][0]['name']='Reanalysed action'
    pair=next(p for p in c['body']['resolution_carry']['scope_check']['element_pairs'] if p['from']['element_id']=='A1')
    pair['relation']='modified'
    for identity in list(g.reviews):g.review(identity)
    before=deepcopy(g.records['CH1']);g.check();assert g.records['CH1']==before
