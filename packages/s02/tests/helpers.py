"""Handwritten synthetic fixtures; not clinic data or business approval."""
from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4
from dacn_s01.repository import Repository as S01Repository
from dacn_s01.service import Service as S01Service
from dacn_s01.codec import serialize_json
from dacn_s02.repository import Repository,record,timestamp
from dacn_s02.service import Service,artifact,staged
from dacn_s02.scope import make_scope
from dacn_s02.validation import index_model

def uid(): return str(uuid4())
def source():
    return dict(title='Synthetic',context='Unknown facts',actors=['Operator'],functional_requirements=[dict(id='R1',text='  Do the requested work  ',priority=None,acceptance_criteria=[])],non_functional_requirements=[],constraints=[],design_preferences=dict(metric_priorities=['response_time_p95','sustainable_throughput','cpu_utilisation','scaling_gain']),operating_conditions=dict.fromkeys(['critical_scenarios','expected_load','peak_load','data_volume','growth','resource_budget']))

def trace(snapshot,pointer='/functional_requirements/0'):
    return dict(origin='inferred',source_refs=[dict(snapshot_id=snapshot,input_pointer=pointer)],answer_refs=[],rationale='Synthetic relation for structural testing',issue_ids=[])

def model(context,snapshot,runid,mid='M1'):
    def ent(i,**kw): return dict(id=i,trace=trace(snapshot),state='ready',**kw)
    actor=ent('Actor',name='Operator',kind='supplied');actor['trace']=trace(snapshot,'/actors/0')
    actions=[ent('A'+n,name='Action '+n,initiator='unknown',actor_ids=[],permission_rule_ids=[],read_data_ids=[],write_data_ids=[],rule_ids=[],workflow_ids=['W'+n]) for n in ('1','2')]
    workflows=[ent('W'+n,name='Workflow '+n,entry_node_id='N'+n,nodes=[dict(id='N'+n,action_id='A'+n,kind='action',label='Work'),dict(id='E'+n,action_id=None,kind='end',label='End')],edges=[dict(id='Edge'+n,**{'from':'N'+n,'to':'E'+n},guard=None,trace=trace(snapshot))],branch_points=[]) for n in ('1','2')]
    components=[ent('C'+n,name='Component '+n,purpose='Synthetic grouping',grouping_reason='Test only',alternatives=[],uncertainties=[]) for n in ('1','2')]
    responsibilities=[ent('RS'+n,component_id='C'+n,statement='Perform action',action_ids=['A'+n],rule_ids=[]) for n in ('1','2')]
    parts=[part('P1',['A1'],['RS1']),part('P12',['A1','A2'],['RS1','RS2']),part('P2',['A2'],['RS2'])]
    return record('model',mid,dict(revision=1,parent_model_id=None,source_context_id=context,created_by_run_id=runid,change_id=None,actors=[actor],actions=actions,workflows=workflows,data=[],rules=[],components=components,responsibilities=responsibilities,interfaces=[],dependencies=[],mappings=[dict(id='Map1',source_ref=dict(snapshot_id=snapshot,input_pointer='/functional_requirements/0'),parts=parts,assessment='proposed',issue_ids=[])]))

def part(i,actions,responsibilities):
    return dict(id=i,obligation='Synthetic obligation '+i,assignment='proposed',target='components',action_ids=actions,primary_responsibility_ids=responsibilities,supporting_responsibility_ids=[],covered_portion='Proposed only',remaining_gap=None,issue_ids=[])

def allscope(m):
    es,ps=index_model(m);return make_scope(m['id'],es,ps)

def aset(m,identity='AS1',parent=None,issues=(),scenarios=(),characteristics=(),changed=None):
    selected=list(issues)+list(scenarios)+list(characteristics)
    return record('analysis_set',identity,dict(model_id=m['id'],revision=1 if parent is None else int(parent['body']['revision'])+1,parent_set_id=parent['id'] if parent else None,scenario_ids=list(scenarios),characteristic_ids=list(characteristics),issue_ids=list(issues),changed_record_ids=selected if changed is None else list(changed),affected=allscope(m)))

def issue(m,identity='Q2',key='Question2',blocked=('A2',),parts=('P2',),status='open',parent=None):
    snap=m['body']['actors'][0]['trace']['source_refs'][0]['snapshot_id'];scope=make_scope(m['id'],blocked,parts)
    return record('issue',identity,dict(issue_key=key,supersedes_id=parent,model_id=m['id'],detected_step=1,kind='business',question='Who may do this?',reason='Unknown fact',trace=trace(snap),affected=scope,blocking=scope,status=status,answer_ids=[],resolution_event_refs=[],resolution=None))

def run(operation,context,config,*,model_id=None,set_id=None,status='completed',attempts=(),errors=()):
    now=timestamp();r=operation['request']
    return record('run',operation['reserved_run_id'],dict(mode='replay',source_context_id=context,config_artifact_id=config,base_model_id=r.get('base_model_id'),base_analysis_set_id=r.get('base_analysis_set_id'),command_id=operation['command_id'],result_analysis_set_id=set_id,steps=[],status=status,result_model_id=model_id,started_at=now,completed_at=now,attempts=list(attempts),errors=list(errors)),now)

def operation(session,context,base=(None,None),*,kind='work',answer_id=None,issue_key=None,parent=None):
    request=dict(kind=kind,base_model_id=base[0],base_analysis_set_id=base[1],source_context_id=context)
    if kind=='work': request.update(scope=None,config_artifact_id=None)
    else: request.update(answer_id=answer_id,issue_key=issue_key)
    return dict(command_id=uid(),session_id=session,parent_command_id=parent,reserved_run_id=uid(),request=request)

class Foundation:
    def __init__(self,tmp):
        self.tmp=Path(tmp);self.s01=S01Repository(self.tmp/'s01.sqlite3');self.s01.initialize()
        self.raw=serialize_json(source());self.s01env=S01Service(self.s01).submit(self.raw,dict(mode='create',spec_id=None,base_revision=None))
        assert self.s01env['status']=='validated',self.s01env
        self.repo=Repository(self.tmp/'s02.sqlite3');self.repo.initialize()
        self.result=Service(self.repo).start(self.s01.path,'synthetic',self.s01env['run']['run_id'])
        self.session=self.result['session_id'];self.context=self.result['source_context_id'];self.snapshot=self.result['snapshot_id']
        self.config=self.repo.get_record(self.result['run_id'])['body']['config_artifact_id']
    def operation(self,base=None,**kwargs):
        return operation(self.session,self.context,self.repo.heads(self.session) if base is None else base,**kwargs)
    def initial(self,with_issue=False):
        op=self.operation();self.repo.prepare(op);m=model(self.context,self.snapshot,op['reserved_run_id'])
        q=issue(m) if with_issue else None;a=aset(m,issues=[q['id']] if q else [])
        rr=run(op,self.context,self.config,model_id=m['id'],set_id=a['id'])
        self.repo.finalize(op['command_id'],[m,a,rr]+([q] if q else []),head=(m['id'],a['id']))
        return m,a

def evidence(kind,**kw): print('S02_EVIDENCE '+json.dumps(dict(kind=kind,**kw),sort_keys=True))
