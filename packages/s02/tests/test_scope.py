from copy import deepcopy
import pytest
from dacn_s02.scope import closure,permitted_scope,make_scope,reverse_impact
from dacn_s02.errors import S02Error
from helpers import model,part,issue,allscope,trace

def graph(): return model('CTX','SNAP','RUN')
def decide(m,**kw):
    return permitted_scope(m,make_scope(m['id'],parts=['P1']),allscope(m),current_analysis_set_id='AS',reviewed_analysis_set_id='AS',**kw)
def parts(m): return m['body']['mappings'][0]['parts']
def split(m):
    parts(m)[:]=[part('P1',['A1'],['RS1']),part('P12-A1',['A1'],['RS1']),part('P12-A2',['A2'],['RS2']),part('P2',['A2'],['RS2'])]

def test_f04_discovered_multi_action_blocked():
    m=graph();c=closure(m,make_scope('M1',parts=['P1']))
    assert c.action_ids=={'A1','A2'}
    assert set(c.scope['mapping_part_ids'])=={'P1','P12','P2'}
    d=decide(m,issues=[issue(m)])
    assert d['allowed_scope']==make_scope('M1')
    assert d['blocked_scope']==make_scope('M1',['A1','A2'],['P1','P12','P2'])
    assert 'BLOCKED_SCOPE' in d['reason_codes']
    assert d['closures'][0]['seed']=='P1'
    assert set(d['closures'][0]['scope']['element_ids'])=={'A1','A2','W1','W2','RS1','RS2','C1','C2'}

def test_f04_complete_union():
    m=graph();d=decide(m)
    assert set(d['allowed_scope']['element_ids'])=={'A1','A2','W1','W2','RS1','RS2','C1','C2'}
    assert set(d['allowed_scope']['mapping_part_ids'])=={'P1','P12','P2'}
    assert d['reason_codes']==[]
    assert d['blocked_scope']==make_scope('M1')
    # Every discovered part's full actions are retained, never an A1-only P12.
    assert all(set(p['action_ids'])<=set(d['allowed_scope']['element_ids']) for p in parts(m))

def test_f04_split_requires_new_review():
    old=graph();m=deepcopy(old);m['id']='M2';split(m)
    stale=permitted_scope(m,make_scope('M2',parts=['P1']),allscope(old),current_analysis_set_id='AS2',reviewed_analysis_set_id='AS1')
    assert stale['allowed_scope']==make_scope('M2') and stale['reason_codes']==['ANALYSIS_STALE']
    d=decide(m,issues=[issue(m)])
    assert set(d['allowed_scope']['element_ids'])=={'A1','W1','RS1','C1'}
    assert set(d['allowed_scope']['mapping_part_ids'])=={'P1','P12-A1'}
    assert d['blocked_scope']==make_scope('M2',['A2'],['P2','P12-A2'])

def test_unreviewed_discovered_part_blocks_entire_seed():
    m=graph();accepted=allscope(m);accepted['mapping_part_ids']=['P1']
    d=permitted_scope(m,make_scope('M1',parts=['P1']),accepted,current_analysis_set_id='AS',reviewed_analysis_set_id='AS')
    assert not d['allowed_scope']['mapping_part_ids'];assert 'UNREVIEWED_SCOPE' in d['reason_codes']

def test_workflow_prerequisite_and_cycle():
    m=graph();split(m);b=m['body'];w=b['workflows'][0]
    w['entry_node_id']='Before';w['nodes'].append(dict(id='Before',kind='action',action_id='A2',label='Before'))
    w['edges'] += [dict(id='before',**{'from':'Before','to':'N1'},guard=None,trace=trace('SNAP')),dict(id='loop',**{'from':'E1','to':'Before'},guard=None,trace=trace('SNAP'))]
    c=closure(m,make_scope('M1',parts=['P1']));assert c.action_ids=={'A1','A2'}
    assert not decide(m,issues=[issue(m)])['allowed_scope']['mapping_part_ids']

def branched(mode):
    m=graph();split(m);w=m['body']['workflows'][0]
    w['entry_node_id']='Choice';w['nodes'].extend([dict(id='Choice',kind='decision',action_id=None,label='Which'),dict(id='Other',kind='action',action_id='A2',label='Other')])
    w['edges'].extend([dict(id='left',**{'from':'Choice','to':'N1'},guard='A1 guard',trace=trace('SNAP')),dict(id='right',**{'from':'Choice','to':'Other'},guard='A2 guard',trace=trace('SNAP'))])
    w['branch_points']=[dict(node_id='Choice',mode=mode,trace=trace('SNAP'))]
    choice=dict(workflow_id='W1',node_id='Choice',edge_id='left',independence_evidence='Synthetic reviewed independence, not a business claim')
    return m,choice

def test_branch_choice_not_guard_inference():
    m,choice=branched('exclusive');assert closure(m,make_scope('M1',parts=['P1'])).action_ids=={'A1','A2'}
    assert closure(m,make_scope('M1',parts=['P1']),[choice]).action_ids=={'A1'}
    assert set(decide(m,choices=[choice],issues=[issue(m)])['allowed_scope']['mapping_part_ids'])=={'P1','P12-A1'}
    unknown,_=branched('unknown')
    with pytest.raises(S02Error) as e: closure(unknown,make_scope('M1',parts=['P1']),[choice])
    assert e.value.error['code']=='SCOPE_UNDETERMINED'

def dependency(i,consumer,provider,action,required,responsibility):
    return dict(id=i,trace=trace('SNAP'),state='ready',kind='uses_component',consumer_component_id=consumer,provider_component_id=provider,interface_id=None,capability='Synthetic support',action_ids=[action],workflow_ids=[],reason='Test relation',support=[dict(action_id=action,provider_responsibility_ids=[responsibility],required_action_ids=required)])

def test_multihop_dependency_cycle_and_unknown():
    m=graph();split(m);b=m['body']
    a3=deepcopy(b['actions'][1]);a3.update(id='A3',workflow_ids=[]);b['actions'].append(a3)
    c3=deepcopy(b['components'][1]);c3['id']='C3';b['components'].append(c3)
    r3=deepcopy(b['responsibilities'][1]);r3.update(id='RS3',component_id='C3',action_ids=['A3']);b['responsibilities'].append(r3)
    parts(m).append(part('P3',['A3'],['RS3']))
    b['dependencies']=[dependency('D12','C1','C2','A1',['A2'],'RS2'),dependency('D23','C2','C3','A2',['A3'],'RS3'),dependency('D31','C3','C1','A3',['A1'],'RS1')]
    c=closure(m,make_scope('M1',parts=['P1']));assert c.action_ids=={'A1','A2','A3'}
    assert set(c.scope['mapping_part_ids'])=={'P1','P12-A1','P12-A2','P2','P3'}
    b['dependencies'][1]['support'][0]['required_action_ids']=None
    assert 'SCOPE_UNDETERMINED' in closure(m,make_scope('M1',parts=['P1'])).reasons
    assert not decide(m)['allowed_scope']['mapping_part_ids']

def test_shared_context_no_all_actions_expansion():
    m=graph();split(m);b=m['body']
    b['responsibilities'][0]['action_ids']=['A1','A2']
    b['responsibilities'][1]['component_id']='C1'
    assert closure(m,make_scope('M1',parts=['P1'])).action_ids=={'A1'}
    assert decide(m,issues=[issue(m)])['allowed_scope']['mapping_part_ids']==['P1','P12-A1']
    shared=issue(m,blocked=('C1',),parts=())
    assert not decide(m,issues=[shared])['allowed_scope']['mapping_part_ids']

def test_system_part_and_pending_task_condition():
    m=graph();p=part('Global',[],[]);p['target']='system';parts(m).append(p)
    c=closure(m,make_scope('M1',parts=['P1']));assert 'Global' in c.scope['mapping_part_ids']
    accepted=allscope(m);accepted['mapping_part_ids'].remove('Global')
    d=permitted_scope(m,make_scope('M1',parts=['P1']),accepted,current_analysis_set_id='AS',reviewed_analysis_set_id='AS')
    assert not d['allowed_scope']['mapping_part_ids']
    assert not decide(m,pending_tasks=[dict(scope=make_scope('M1',['A2']),status='pending')])['allowed_scope']['mapping_part_ids']
    assert not decide(m,conditions=[dict(scope=make_scope('M1',parts=['Global']),blocking=True)])['allowed_scope']['mapping_part_ids']

def test_union_does_not_leak_blocked_part():
    m=graph();requested=make_scope('M1',parts=['P1','P2'])
    d=permitted_scope(m,requested,allscope(m),current_analysis_set_id='AS',reviewed_analysis_set_id='AS',issues=[issue(m)])
    assert not d['allowed_scope']['mapping_part_ids']
    assert len(d['closures'])==2
    impact=reverse_impact(m,['A2'],[])
    assert set(impact['mapping_part_ids'])=={'P1','P12','P2'}
