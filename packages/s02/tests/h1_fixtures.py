"""Synthetic input/candidates, never canonical Model/Issue imports."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from dacn_s01.repository import Repository as S01Repository
from dacn_s01.service import Service as S01Service
from dacn_s02.codec_boundary import encode
from dacn_s02.repository import Repository
from dacn_s02.service import Service
from dacn_s02.h1_service import H1Service
from dacn_s02.validation import inventory
from dacn_s02.h1_candidates import VERSION


def input_data():
    return dict(title='H1 SYNTHETIC',context='Software test only; not business confirmation',actors=['Operator'],
        functional_requirements=[dict(id='R1',text='Operator may create an item and retain its ID and status',priority=None,acceptance_criteria=['Retain the supplied ID','Retain the supplied status']),
            dict(id='R2',text='Operator may read item status',priority='should',acceptance_criteria=[])],
        non_functional_requirements=[dict(id='N1',text='Keep logical responsibilities reviewable',priority=None,acceptance_criteria=[])],
        constraints=[dict(id='C1',text='Keep processing local',priority='must',acceptance_criteria=[])],
        design_preferences=dict(metric_priorities=['response_time_p95','sustainable_throughput','cpu_utilisation','scaling_gain']),
        operating_conditions=dict.fromkeys(['critical_scenarios','expected_load','peak_load','data_volume','growth','resource_budget']))


def mocks(snapshot):
    sid=snapshot['snapshot_id']
    def src(p='/functional_requirements/0'):return dict(snapshot_id=sid,input_pointer=p)
    def tr(p='/functional_requirements/0'):return dict(origin='inferred',source_refs=[src(p)],rationale='Synthetic proposal only',finding_handles=[])
    def local(h):return dict(local_handle=h)
    def base(h):return dict(base_handle=h)
    def entity(h,**kw):return dict(handle=h,trace=tr(),state='draft',**kw)
    inspection=[dict(source_ref=src(p),read='inspected',verdict='usable',needed_facts=[],evidence_source_refs=[src(p)],finding_handles=[],reason='Enough for this synthetic draft; no quality or business acceptance') for p in sorted(inventory(snapshot))]
    def envelope(step,**kw):return dict(candidate_version=VERSION,step=step,proposals=dict(findings=[],**kw),questions=[],inspection=deepcopy(inspection),unrepresented_source_refs=[])
    candidates=[envelope(1)]
    actions=[]
    for h in ('create','read'):
        actions.append(entity(h,name=h,initiator='external',actor_ids=[base('supplied-actor.0')],permission_rule_ids=[local('permission')],
            read_data_ids=[local('item')] if h=='read' else [],write_data_ids=[local('item')] if h=='create' else [],rule_ids=[local('consistency')],workflow_ids=[local('flow')]))
    workflow=entity('flow',name='Synthetic item flow',entry_node_id=local('create-node'),
        nodes=[dict(handle='create-node',action_id=local('create'),kind='action',label='Create'),dict(handle='read-node',action_id=local('read'),kind='action',label='Read'),dict(handle='end-node',action_id=None,kind='end',label='End')],
        edges=[dict(handle='edge1',**{'from':local('create-node'),'to':local('read-node')},guard=None,trace=tr()),dict(handle='edge2',**{'from':local('read-node'),'to':local('end-node')},guard=None,trace=tr())],branch_points=[])
    candidates.append(envelope(2,actors=[],actions=actions,workflows=[workflow],data=[entity('item',name='Item',description='ID and status, proposed logical data')],
        rules=[entity('permission',statement='Operator may perform the explicit actions',kind='permission',action_ids=[local('create'),local('read')]),entity('consistency',statement='Retain ID and status',kind='consistency',action_ids=[local('create')])]))
    candidates.append(envelope(3,components=[entity('records',name='Records',purpose='Proposed item responsibilities',grouping_reason='Related logical operations and rules',alternatives=['Review another grouping'],uncertainties=['No business review performed'])],
        responsibilities=[entity('manage',component_id=local('records'),statement='Create and read items',action_ids=[base('step2.create'),base('step2.read')],rule_ids=[base('step2.consistency')])],unassigned_actions=[]))
    rows=[]
    for i,p in enumerate(sorted(inventory(snapshot))):
        system=p.startswith(('/non_functional_requirements/','/constraints/'))
        part=dict(handle='part'+str(i),obligation='Synthetic candidate for '+p,assignment='proposed',target='system' if system else 'components',
            action_ids=[] if system else [base('step2.read' if p=='/functional_requirements/1' else 'step2.create')],
            primary_responsibility_ids=[] if system else [base('step3.manage')],supporting_responsibility_ids=[],covered_portion='Mock proposal, no satisfaction claim',remaining_gap=None,finding_handles=[])
        rows.append(dict(source_ref=src(p),assessment='proposed',parts=[part],finding_handles=[]))
    candidates.append(envelope(4,mappings=rows))
    return candidates


class Case:
    def __init__(self,path,source=None):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True)
        (self.path/'s01').mkdir();(self.path/'s02').mkdir()
        self.s01=S01Repository(self.path/'s01/s01.sqlite3');self.s01.initialize()
        self.source=input_data() if source is None else source;self.raw=encode(self.source)
        self.envelope=S01Service(self.s01).submit(self.raw,dict(mode='create',spec_id=None,base_revision=None))
        assert self.envelope['status']=='validated'
        self.snapshot=self.envelope['snapshot'];self.repo=Repository(self.path/'s02/s02.sqlite3');self.repo.initialize()
        self.intake=Service(self.repo).start(self.s01.path,'synthetic',self.envelope['run']['run_id'],expected_snapshot_id=self.snapshot['snapshot_id'])
        self.parent=self.intake['command_id'];self.store_id=self.repo.store_info()['metadata']['store_id'];self.responses=mocks(self.snapshot)

    def prepare(self,step,raw=None,parent=None):
        command=str(uuid4());H1Service(self.repo).prepare(command,parent or self.parent,step,raw,self.store_id);return command

    def advance(self,step,raw=None):
        if raw is None and step!='bootstrap':raw=encode(self.responses[step-1])
        cmd=self.prepare(step,raw);result=H1Service(self.repo).resume(cmd);self.parent=cmd
        return result
