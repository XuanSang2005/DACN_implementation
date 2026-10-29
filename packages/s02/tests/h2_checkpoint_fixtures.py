"""Test-only synthetic approvals and independently chosen U/V projections."""
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
from hashlib import sha256
from h1_fixtures import Case,input_data
from dacn_s02.codec_boundary import encode
from dacn_s02.h2_service import H2Service
from dacn_s02.h2_contracts import ANALYSIS,POLICY
from dacn_s02.h2_candidates import VERSION,scope_request_hash
from dacn_s02.h2_authority import FORMAT,LocalSyntheticAuthority


class ScopedCase(Case):
    def __init__(self,path):
        source=input_data();source['functional_requirements'][1]['acceptance_criteria']=['Keep full criteria','Keep order']
        super().__init__(path,source)
        self.service=H2Service(self.repo);self.last=None;self.authorities={}

    def bootstrap(self):
        cmd=str(uuid4());self.service.prepare(cmd,self.parent,mode='bootstrap',store_id=self.store_id)
        self.last=self.service.resume(cmd);assert self.last['status']=='completed',self.last
        self.parent=cmd;self.refresh();return self.last

    def refresh(self):
        self.last=H2Service(self.repo).report(self.parent,progress=True)
        self.pair=self.last['result']['result_pair'];self.meta=self.last['result']['last_checked_eligibility']
        self.units={row['source_refs'][0]['input_pointer']:row['unit_id'] for row in self.meta['inventory']}
        self.u=self.units['/functional_requirements/0'];self.v=self.units['/functional_requirements/1']

    def src(self,p):return dict(snapshot_id=self.snapshot['snapshot_id'],input_pointer=p)
    def tr(self,p='/functional_requirements/1'):return dict(origin='inferred',source_refs=[self.src(p)],rationale='Synthetic independent read family',finding_handles=[])
    def aliases(self):return self.last['result']['next_aliases']
    def alias(self,kind):return next(h for h,x in self.aliases().items() if x['kind']==kind)

    def work(self,step,*,units=None,mode='step',goal='build',guards=(),proof=True,change=None,decision='allow'):
        units=list(units or (self.meta['progress_by_unit'] if step==1 else [self.v]))
        service=H2Service(self.repo)
        _,source,binding=service.intent(self.parent,mode=mode,step=step,unit_ids=units,expected_pair=self.pair,goal=goal,guard_keys=guards,provider_id='test-controller')
        inspections=[];candidate_inspection=[]
        for ptr in sorted(source.obligations):
            held=ptr.startswith('/functional_requirements/0')
            inspections.append(dict(source_ref=self.src(ptr),read='inspected',verdict='held' if held else 'usable',basis_source_refs=[self.src(ptr)],needed_facts=['Unknown U permission'] if held else [],reason='Synthetic inspected source'))
            candidate_inspection.append(dict(source_ref=self.src(ptr),read='inspected',verdict='held' if held else 'usable',needed_facts=['Unknown U permission'] if held else [],evidence_source_refs=[self.src(ptr)],finding_handles=[],reason='Synthetic inspected source'))
        independence=[]
        for key in self.meta['selectors']:
            for unit in source.units:
                independence.append(dict(issue_key=key,unit_id=unit,verdict=('held' if unit==self.u else 'independent') if proof else 'unknown',basis_source_refs=[self.src(p) for p in sorted(source.obligations)],reason='Explicit independent synthetic scopes; U remains held'))
        analysis=dict(version=ANALYSIS,id='analysis.synthetic',source_context_id=binding['source_context_id'],snapshot_id=self.snapshot['snapshot_id'],base_model_id=self.pair[0],base_analysis_set_id=self.pair[1],step=step,unit_ids=units,selectors_sha256=binding['current_selectors_sha256'],policy_version=POLICY,inspections=inspections,independence=independence)
        candidate=None
        if mode=='step':
            p=dict(findings=[])
            if step==1:
                p['findings']=[dict(handle='u-hold',kind='business',question='Who may cancel U?',reason='U permission is unknown',trace=self.tr('/functional_requirements/0'),affected_refs=[],blocking_refs=[],impact_known=True)]
            if step==2:p.update(actors=[],actions=[dict(handle='view',name='Read independent V',initiator='external',actor_ids=[dict(base_handle='supplied-actor.0')],permission_rule_ids=[],read_data_ids=[],write_data_ids=[],rule_ids=[],workflow_ids=[],state='draft',trace=self.tr())],workflows=[],data=[],rules=[])
            if step==3:p.update(components=[dict(handle='viewer',name='Viewer',purpose='Independent V read',grouping_reason='V responsibility',alternatives=['Review later'],uncertainties=['Synthetic only'],state='draft',trace=self.tr())],responsibilities=[dict(handle='view-responsibility',component_id=dict(local_handle='viewer'),statement='Read V',action_ids=[dict(base_handle=self.alias('Action'))],rule_ids=[],state='draft',trace=self.tr())],unassigned_actions=[])
            if step==4:
                p['mappings']=[dict(source_ref=self.src(ptr),assessment='proposed',finding_handles=[],parts=[dict(handle='part.'+str(i),obligation='Retain '+ptr,assignment='proposed',target='components',action_ids=[dict(base_handle=self.alias('Action'))],primary_responsibility_ids=[dict(base_handle=self.alias('Responsibility'))],supporting_responsibility_ids=[],covered_portion='Synthetic V proposal',remaining_gap=None,finding_handles=[])]) for i,ptr in enumerate(sorted(source.selected(units)))]
            candidate=dict(candidate_version=VERSION,step=step,unit_ids=units,scope_request_sha256=scope_request_hash(binding),proposals=p,questions=['u-hold'] if step==1 else [],inspection=candidate_inspection,unrepresented_source_refs=[self.src(p) for p in sorted(source.obligations) if p.startswith('/functional_requirements/0')])
        if change:change(candidate,analysis)
        raw=encode(candidate) if candidate else None;araw=encode(analysis)
        _,_,binding=service.intent(self.parent,mode=mode,step=step,unit_ids=units,expected_pair=self.pair,goal=goal,guard_keys=guards,provider_id='test-controller',candidate=raw,analysis=araw)
        control=dict(format=FORMAT,provider_id='test-controller',provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=binding,decision=decision,reason='Explicit synthetic test approval')])
        path=self.path/('authority-'+str(uuid4())+'.json');data=encode(control);path.write_bytes(data)
        authority=LocalSyntheticAuthority(path,sha256(data).hexdigest())
        return dict(mode=mode,step=step,unit_ids=units,expected_pair=self.pair,goal=goal,guard_keys=list(guards),candidate=raw,analysis=araw),authority

    def advance(self,step,**kw):
        work,authority=self.work(step,**kw);cmd=str(uuid4());service=H2Service(self.repo,authority=authority)
        service.prepare(cmd,self.parent,store_id=self.store_id,**work);result=service.resume(cmd)
        self.authorities[cmd]=authority
        if result['result'].get('result_pair'):self.parent=cmd;self.refresh()
        return result
