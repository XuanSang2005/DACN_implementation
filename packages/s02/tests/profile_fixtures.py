"""Canonical synthetic graphs for E1; no E1 persistence or real user decision.

L1 root is produced by the unchanged a3 fixture/application path. E1 records
are then constructed explicitly in memory. These are not documentation JSON.
"""
from copy import deepcopy
from dataclasses import dataclass,field
from dacn_s02.repository import record
from dacn_s02.profiles import L1,E1
from dacn_s02.profile_graph import validate_graph
from dacn_s02.resolution import HumanReviewEvidence,review_digest
from dacn_s02.scope import make_scope
from dacn_s02.s01_adapter import verify_archive
from helpers import operation,run,aset,issue,allscope
from test_lifecycle import add_answer,application_batch

ELEMENTS=['A1','A2','W1','W2','C1','C2','RS1','RS2']
PARTS=['P1','P12','P2']
def fullfoot(mid):return make_scope(mid,ELEMENTS,PARTS)
def source_ref(sid):return dict(snapshot_id=sid,input_pointer='/functional_requirements/0')
def scope_proof(old,new):
    return dict(from_scope=fullfoot(old),to_scope=fullfoot(new),element_pairs=[dict(**{'from':dict(model_id=old,element_id=i),'to':dict(model_id=new,element_id=i)},relation='unchanged',reason='Synthetic exact unchanged element') for i in ELEMENTS+PARTS],reason='Synthetic complete footprint, including shared multi-action Part')

@dataclass
class Graph:
    records:dict
    record_profiles:dict
    owners:dict
    commands:dict
    operation_profiles:dict
    events:dict
    stages:dict
    blobs:dict
    session:str
    context:str
    config:str
    snapshot:str
    model_id:str='M2'
    set_id:str='AS-M2'
    current_issue:str='Q2-resolved'
    reviews:dict=field(default_factory=dict)

    def kwargs(self):return {k:getattr(self,k) for k in ('records','record_profiles','owners','commands','operation_profiles','events','stages','blobs','reviews')}
    def check(self):return validate_graph(**self.kwargs())
    def snapshots(self):
        return {r['body']['snapshot_id']:verify_archive(r,self.records,self.blobs) for r in self.records.values() if r['type']=='source_context'}
    def add(self,r,profile=E1):
        self.records[r['id']]=r;self.record_profiles[r['id']]=profile;self.owners[r['id']]=self.session
    def review(self,identity):
        q=self.records[identity];p=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        self.reviews[identity]=HumanReviewEvidence(p['evaluation']['evaluator'],review_digest(q,self.records,self.snapshots(),self.record_profiles),p['assessment'])
    def publish(self,items,selected,*,new_model=None):
        old=self.records[self.set_id];m=new_model or self.records[self.model_id]
        op=operation(self.session,self.context,(self.model_id,self.set_id))
        if new_model is not None:
            m['body']['created_by_run_id']=op['reserved_run_id']
        newset=aset(m,'AS-'+str(len(self.records)),None if new_model else old,issues=selected,changed=[r['id'] for r in items if r['type']=='issue'])
        rr=run(op,self.context,self.config,model_id=m['id'] if new_model else None,set_id=newset['id'])
        for r in items+[newset,rr]+([m] if new_model else []):self.add(r)
        cmd=op['command_id'];self.commands[cmd]=op;self.operation_profiles[cmd]=E1
        self.events[cmd,'prep']=dict(event_id='prep',command_id=cmd,ordinal=1,kind='prepared',payload=dict(stage_refs=[],attempt_id=None))
        self.events[cmd,'final']=dict(event_id='final',command_id=cmd,ordinal=2,kind='finalized',payload=dict(run_id=rr['id'],promotions=[]))
        self.model_id=m['id'];self.set_id=newset['id'];return op,newset
    def carry(self,assessment='applicable',method='structural_check',*,new_model=False):
        old=self.records[self.current_issue];mid=self.model_id
        m=deepcopy(self.records[mid]) if new_model else None
        if m:
            m['id']='M'+str(m['body']['revision']+1);m['body'].update(revision=m['body']['revision']+1,parent_model_id=mid,change_id='CH-'+m['id'])
        newmid=m['id'] if m else mid;identity='Carry-'+str(len(self.records))
        q=deepcopy(old);q['id']=identity;b=q['body'];b.update(model_id=newmid,supersedes_id=old['id'],affected=fullfoot(newmid),blocking=make_scope(newmid) if assessment=='applicable' else fullfoot(newmid),status='resolved' if assessment=='applicable' else 'resolution_pending_revalidation',resolution_replacement=None)
        origin=old['body'].get('resolution_carry',{});origin=origin['origin_issue_id'] if origin else old['id']
        b['resolution_carry']=dict(origin_issue_id=origin,from_issue_id=old['id'],base_analysis_set_id=self.set_id,change_id=m['body']['change_id'] if m else None,assessment=assessment,source_checks=[dict(from_ref=source_ref(self.snapshot),to_ref=source_ref(self.snapshot),relation='equal_value',reason='Synthetic checked requirement')],scope_check=scope_proof(mid,newmid),evaluation=dict(method=method,evaluator='SYNTHETIC REVIEWER' if method=='human_review' else 'dacn-s02/0.2.0a1',rule_version='s02-rules/a1a2-v1',evidence_record_ids=[newmid],reason='Synthetic test decision; not actual user approval'))
        items=[q]
        if m:items.append(record('change',m['body']['change_id'],dict(base_model_id=mid,new_model_id=newmid,kind='analysis_edit',old_source_context_id=self.context,new_source_context_id=self.context,reason='Synthetic independent revision',source_record_ids=[old['id']],application_event_refs=[],operations=[],affected=allscope(m),reused=[],reevaluate=[],invalidated_bundle_ids=[])))
        self.publish(items,[q['id']],new_model=m);self.current_issue=q['id']
        if method=='human_review':self.review(q['id'])
        return q
    def replacement(self,complete=False,method='human_review',*,target_status='resolved'):
        previous=self.records[self.current_issue];pb=previous['body'];cp=pb['resolution_carry'] or pb['resolution_replacement'];mid=self.model_id
        target=issue(self.records[mid],'Target-'+str(len(self.records)),key='NewDecision',status=target_status,blocked=ELEMENTS,parts=PARTS)
        target['body'].update(kind='analysis_omission',resolution='Synthetic current source resolves the new obligation' if target_status=='resolved' else None,resolution_carry=None,resolution_replacement=None,blocking=make_scope(mid) if target_status=='resolved' else fullfoot(mid))
        q=deepcopy(previous);q['id']='Replacement-'+str(len(self.records));q['body'].update(supersedes_id=previous['id'],status='resolution_replaced' if complete else 'resolution_pending_revalidation',blocking=make_scope(mid) if complete else fullfoot(mid),resolution_carry=None)
        q['body']['resolution_replacement']=dict(origin_issue_id=cp['origin_issue_id'],obsolete_issue_id=previous['id'] if pb['resolution_carry'] else cp['obsolete_issue_id'],from_issue_id=previous['id'],base_analysis_set_id=self.set_id,change_id=None,replacement_issue_id=target['id'],assessment='complete' if complete else 'incomplete',obligation_checks=[dict(old_ref=source_ref(self.snapshot),current_ref=source_ref(self.snapshot),disposition='replaced',evidence_record_ids=[target['id']],reason='Synthetic coverage of entire requirement')],scope_check=scope_proof(mid,mid),evaluation=dict(method=method,evaluator='SYNTHETIC REVIEWER' if method=='human_review' else 'dacn-s02/0.2.0a1',rule_version='s02-rules/a1a2-v1',evidence_record_ids=[target['id']],reason='Synthetic replacement review; not business approval'))
        self.publish([q,target],[q['id'],target['id']]);self.current_issue=q['id']
        if method=='human_review':self.review(q['id'])
        return q,target

def graph(f):
    m,a,answer=add_answer(f);op,batch,events=application_batch(f,m,a,answer)
    f.repo.finalize(op['command_id'],batch,head=('M2','AS-M2'),application_events=events)
    # Read-only checked fixture extraction. Repository still writes only L1 DB1.
    with f.repo._read() as c:
        records,blobs,commands,events,stages=f.repo._check(c)
    return Graph(records,{i:L1 for i in records},{i:f.session for i in records},commands,{c:L1 for c in commands},events,stages,blobs,f.session,f.context,f.config,f.snapshot)

def observed_graph(f,*,switch=False,change_text=False):
    """Real S01 local checked run; synthetic consent/events assembled in memory."""
    from dacn_s01.service import Service as S01Service
    from dacn_s01.codec import serialize_json
    from dacn_s02.s01_adapter import intake
    from dacn_s02.service import artifact,staged
    g=graph(f);value=deepcopy(f.s01env['snapshot']['input']);spec=f.s01env['snapshot']['spec_id'];revision=1
    if switch:
        value['context']='Synthetic updated context'
        if change_text:value['functional_requirements'][0]['text']='A different synthetic obligation'
        changed=S01Service(f.s01).submit(serialize_json(value),dict(mode='update',spec_id=spec,base_revision=1))
        assert changed['result_kind']=='new_revision';revision=2
    # Deliberately different raw bytes, same normalized selected head.
    raw=b'\n '+serialize_json(value)+b'\n'
    observed=S01Service(f.s01).submit(raw,dict(mode='update',spec_id=spec,base_revision=revision))
    assert observed['result_kind']=='unchanged'
    archived=intake(f.s01.path,observed['run']['run_id'])
    arts=[]
    for identity,purpose,data in [('ObsEnvelope','s01_envelope',archived.envelope_bytes),('ObsRaw','s01_run_source',archived.run_source),('ObsOrigin','s01_origin_source',archived.origin_source),('ObsSchema','schema',archived.schema)]:
        r=artifact(identity,purpose,data);g.add(r);g.blobs[identity]=data;arts.append(r)
    context=record('source_context','ObservedContext',dict(store_key='synthetic',s01_run_id=observed['run']['run_id'],snapshot_id=observed['snapshot']['snapshot_id'],envelope_artifact_id='ObsEnvelope',run_source_artifact_id='ObsRaw',origin_source_artifact_id='ObsOrigin',schema_artifact_id='ObsSchema'));g.add(context)
    app=next(e for e in g.events.values() if e['kind']=='application_applied');cmd=app['command_id'];g.operation_profiles[cmd]=E1
    selected_ref=app['payload']['interpretation_event'];selected=g.events[selected_ref['command_id'],selected_ref['event_id']]
    request=dict(mode='update',spec_id=spec,base_revision=revision)
    sr=dict(command_id=cmd,blob_id='FullInput');s,data=staged(cmd,'FullInput','requirement_update_input',raw);g.stages[cmd,'FullInput']={**s,'bytes':data}
    selected['payload'].update(interpretation='changes_requirements',proposed_input=sr,s01_request=request,existing_source_refs=[])
    def add(kind,payload,ordinal):
        e=dict(event_id=kind,command_id=cmd,ordinal=ordinal,kind=kind,payload=payload);g.events[cmd,kind]=e;return dict(command_id=cmd,event_id=kind)
    consent=add('consent_recorded',dict(answer_id='Answer1',interpretation_event=selected_ref,respondent='SYNTHETIC',text='Synthetic full input consent',approved_input_sha256=s['sha256']),3)
    dispatch=add('s01_dispatch_intent',dict(answer_id='Answer1',consent_event=consent,s01_store_key='synthetic',s01_run_id=observed['run']['run_id'],s01_request=request,input_stage_ref=sr),4)
    observation=add('s01_result_observed',dict(answer_id='Answer1',dispatch_event=dispatch,s01_run_id=observed['run']['run_id'],lookup_status='validated',snapshot_id=observed['snapshot']['snapshot_id']),5)
    app['ordinal']=6
    final=next(e for e in g.events.values() if e['kind']=='finalized' and e['command_id']==cmd);final['ordinal']=7
    app['payload'].update(consent_event=consent,s01_observation_event=observation,observed_source_context_id=context['id'])
    q=g.records['Q2-resolved'];q['body'].update(resolution_carry=None,resolution_replacement=None)
    application_profiles(g,cmd)
    if switch:
        g.records['M2']['body']['source_context_id']='ObservedContext';g.records['CH1']['body'].update(kind='requirements_switch',new_source_context_id='ObservedContext');app['payload']['new_source_context_id']='ObservedContext'
        def rebind(v):
            if type(v) is dict:
                if set(v)=={'snapshot_id','input_pointer'}:v['snapshot_id']=observed['snapshot']['snapshot_id']
                else:
                    for x in v.values():rebind(x)
            elif type(v) is list:
                for x in v:rebind(x)
        rebind(g.records['M2']);rebind(q)
    return g,app,observed


def application_profiles(g,cmd):
    """Explicit E1 fixture allocation for the entire synthetic application T3."""
    run=g.records[g.commands[cmd]['reserved_run_id']];b=run['body']
    for identity in [run['id'],b['result_model_id'],b['result_analysis_set_id'],g.records[b['result_model_id']]['body']['change_id'],*g.records[b['result_analysis_set_id']]['body']['changed_record_ids']]:
        g.record_profiles[identity]=E1
