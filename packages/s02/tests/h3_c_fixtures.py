"""Detached synthetic C gates. No C writer or operational data is used here."""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
from dataclasses import asdict
from pathlib import Path
import os
from dacn_s02.codec_boundary import encode,decode
from dacn_s02.h3_limits import Budget,DEFAULTS,VERSION,digest
from dacn_s02.h3_history import HistoryData,ReviewRegistry,ReviewTrustContext
from dacn_s02.h3_contracts import REGISTRY
from dacn_s02.h1_store import profile_pins
from dacn_s02.service import staged,artifact
from dacn_s02.profiles import E1
from dacn_s02.h3_bindings import config_intent
from dacn_s02.h3_continuation_contracts import CONFIG,PLAN,HANDLER,POLICY,ANALYSIS,AUTHORITY
from dacn_s02.h3_continuation_inputs import binding,intent,refs
from dacn_s02.h3_continuation_checks import ContinuationVerifier
from dacn_s02.h3_continuation_plan import build,MESSAGE
from h3_fixtures import e1
from h3_b_fixtures import config_for as b_config,project as b_project

NOW='2026-11-02T00:00:00.000Z'


def graph_case(path,monkeypatch,branch='direct',target=False,third=False):
    mixed=branch=='mixed'
    if mixed:branch='incomplete'
    want_tasks=branch=='replacement_tasks'
    if want_tasks:branch='replacement'
    import helpers,p2_helpers,profile_fixtures,test_lifecycle
    original_issue=p2_helpers.issue
    def actor_issue(*args,**kwargs):
        kwargs.update(blocked=('Actor',),parts=());return original_issue(*args,**kwargs)
    from p2_helpers import Foundation
    original_source=helpers.source;original_model=helpers.model;application=profile_fixtures.application_batch
    def source():
        value=original_source();value['functional_requirements'].append(dict(id='V',text='Independent V work',priority='should',acceptance_criteria=[]))
        if third:value['functional_requirements'].append(dict(id='W',text='Independent W work',priority='should',acceptance_criteria=[]))
        return value
    def model(*args,**kw):
        value=original_model(*args,**kw)
        if branch=='actor_only':
            for group in ('actions','workflows','components','responsibilities'):value['body'][group]=[]
            for row in value['body']['mappings']:row.update(parts=[],assessment='not_assessed',issue_ids=['Q2'])
        sid=value['body']['actors'][0]['trace']['source_refs'][0]['snapshot_id']
        value['body']['mappings'].append(dict(id='RowV',source_ref=dict(snapshot_id=sid,input_pointer='/functional_requirements/1'),parts=[],assessment='not_assessed',issue_ids=['Q2']))
        if third:value['body']['mappings'].append(dict(id='RowW',source_ref=dict(snapshot_id=sid,input_pointer='/functional_requirements/2'),parts=[],assessment='not_assessed',issue_ids=['Q2']))
        return value
    def applied(*args):
        op,batch,events=application(*args)
        for r in batch:
            if r['type']=='change' and want_tasks:r['body']['reevaluate']=[dict(step=4,scope=dict(model_id='M2',element_ids=['A2'],mapping_part_ids=['P2']),reason='Synthetic previously completed task',status='completed',evidence_record_ids=['Q2-resolved'])]
            if r['type']=='model':
                for row in r['body']['mappings']:
                    if branch=='actor_only' or row['id'] in ('RowV','RowW'):row['issue_ids']=['Q2-resolved']
        return op,batch,events
    with monkeypatch.context() as patch:
        patch.setattr(helpers,'source',source);patch.setattr(helpers,'model',model);patch.setattr(p2_helpers,'model',model);patch.setattr(profile_fixtures,'application_batch',applied)
        if branch=='actor_only':
            patch.setattr(p2_helpers,'issue',actor_issue);patch.setattr(test_lifecycle,'issue',actor_issue)
        f=Foundation(path)
        if branch=='switch':
            g,_,observed=profile_fixtures.observed_graph(f,switch=True);g=e1(g);old_sid=g.snapshot;g.context='ObservedContext';g.snapshot=observed['snapshot']['snapshot_id']
            q=g.carry('applicable','human_review');q['body']['resolution_carry']['source_checks']=[dict(from_ref=dict(snapshot_id=sid,input_pointer='/functional_requirements/0'),to_ref=dict(snapshot_id=g.snapshot,input_pointer='/functional_requirements/0'),relation='equal_value',reason='Synthetic historical switch correspondence') for sid in (old_sid,g.snapshot)];g.review(q['id'])
        else:g=e1(profile_fixtures.graph(f))
    if branch in ('pending','carry','obsolete','replacement','incomplete'):
        g.carry('not_applicable' if branch in ('obsolete','replacement','incomplete') else 'undetermined' if branch=='pending' else 'applicable',method='human_review' if branch in ('obsolete','replacement','incomplete') else 'structural_check')
    if branch in ('replacement','incomplete'):g.replacement(complete=branch=='replacement',method='human_review')
    if branch=='source_only':
        from helpers import issue
        q=issue(g.records[g.model_id],'SourceOnly',key='SourceOnly',status='resolved',blocked=['A1'],parts=['P1'])
        q['body'].update(resolution='Existing checked source-only fact',resolution_carry=None,resolution_replacement=None,blocking=dict(model_id=g.model_id,element_ids=[],mapping_part_ids=[]))
        g.publish([q],[g.current_issue,q['id']])
    if mixed:
        from helpers import issue
        from dacn_s02.repository import record
        from dacn_s02.scope import make_scope
        m=g.records[g.model_id];pending=issue(m,'PendingAnswerIssue',key='PendingAnswerKey',status='answered_pending_application',blocked=['A1'],parts=['P1'])
        pending['body'].update(answer_ids=['PendingAnswer'],resolution_carry=None,resolution_replacement=None)
        answer=record('answer','PendingAnswer',dict(issue_id=pending['id'],supersedes_answer_id=None,respondent='SYNTHETIC',recorded_by='Fixture controller',text='Existing synthetic pending answer',interpretation='points_to_existing_source',existing_source_refs=deepcopy(pending['body']['trace']['source_refs'])))
        direct=issue(m,'MixedSourceOnly',key='SourceOnlyKey',status='resolved',blocked=['A1'],parts=['P1']);direct['body'].update(resolution='Existing source-only historical resolution',blocking=make_scope(g.model_id),resolution_carry=None,resolution_replacement=None)
        selected=list(g.records[g.set_id]['body']['issue_ids']);g.publish([pending,answer,direct],selected+[pending['id'],direct['id']])
    if target:
        from helpers import issue
        t=issue(g.records[g.model_id],'ExistingTarget',key='ExistingTarget',status='resolved',blocked=['A1','A2','W1','W2','C1','C2','RS1','RS2'],parts=['P1','P12','P2'])
        t['body'].update(resolution='Synthetic prior resolved target',resolution_carry=None,resolution_replacement=None,blocking=dict(model_id=g.model_id,element_ids=[],mapping_part_ids=[]))
        g.publish([t],[g.current_issue,t['id']])
    g.check();return f,g


def history_graph(g,budget=None,store='Store'):
    budget=budget or Budget();entries=[dict(issue_id=i,reviewer=d.reviewer,assessment=d.assessment,dependency_sha256=d.dependency_sha256) for i,d in sorted(g.reviews.items())]
    raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='CReviews',store_id=store,required_issue_ids=[e['issue_id'] for e in entries],reviews=entries))
    registry=ReviewRegistry.parse(raw,ReviewTrustContext('synthetic-controller.json',sha256(raw).hexdigest(),'CReviews',store),budget)
    return HistoryData(**{k:v for k,v in g.kwargs().items() if k!='reviews'},registry=registry,store_id=store,budget=budget)


def b_parent(path,monkeypatch,branch='direct',target=False,third=False):
    f,g=graph_case(path,monkeypatch,branch,target,third);h=history_graph(g);base=h.view(g.session,[g.model_id,g.set_id],[g.model_id,g.set_id]);cfg,raw=b_config(base,command='CBase.BAdopt')
    h,before,result,plan=b_project(base,cfg,raw);ContinuationVerifier(h).published(cfg['command_id']);return f,g,result


def units(base):
    return {f.pointer:u for u,f in base.context.source.units.items()}


def request(base,*,step=1,mode='step',command=None,mutate=None,unknown=False,unit_ids=None):
    parent=ContinuationVerifier(base.history).published(base.parent_command_id);meta=parent.plan()['admission'];aliases=parent.plan()['allocation']['aliases'];source=base.context.source
    selected=sorted(unit_ids) if unit_ids is not None else [units(base)['/functional_requirements/1']];uid=selected[0];command=command or 'CCommand.'+str(uuid4());goal='build' if mode=='step' else 'admission'
    readwrite=intent(base,meta,mode=mode,step=step,units=selected,goal=goal,aliases=aliases)
    allrefs=refs(source,source.obligations)
    held_sources={r['input_pointer'] for q in base.issues if q['body']['status'] in ('open','answered_pending_application','resolution_pending_revalidation') and q['body']['issue_key'] not in meta['guards'] and q['body']['issue_key'] not in meta['tasks'] for r in q['body']['trace']['source_refs'] if r['snapshot_id']==source.snapshot_id}
    held_sources={p for f in source.families if f.obligations&held_sources for p in f.obligations}
    analysis=dict(version=ANALYSIS,source_context_id=source.context_id,snapshot_id=source.snapshot_id,base_pair=base.pair,selectors_sha256=digest(sorted(meta['selectors'].values(),key=lambda x:x['issue_key'])),unit_ids=selected,
        inspections=[dict(source_ref=r,read='inspected',verdict='held' if r['input_pointer'] in held_sources else 'usable',basis_source_refs=[r],needed_facts=['Synthetic U remains unresolved'] if r['input_pointer'] in held_sources else [],reason='Explicit synthetic inspection') for r in allrefs],
        independence=[dict(issue_key=q['body']['issue_key'],unit_id=u,verdict='unknown' if unknown else 'held' if bool(f.obligations&held_sources) else 'independent',basis_source_refs=allrefs,reason='Handwritten independent U/V source topology') for q in base.issues for u,f in source.units.items()])
    value=None
    if mode=='step':
        from dacn_s02.h2_candidates import VERSION as CANDIDATE
        tr=dict(origin='inferred',source_refs=refs(source,source.units[uid].obligations),rationale='Synthetic V proposal',finding_handles=[])
        p=dict(findings=[])
        if step==2:p.update(actors=[],actions=[dict(handle='v-action',name='Independent V action',initiator='internal',actor_ids=[],permission_rule_ids=[],read_data_ids=[],write_data_ids=[],rule_ids=[],workflow_ids=[],state='draft',trace=deepcopy(tr))],workflows=[],data=[],rules=[])
        if step==3:
            action=next(k for k,v in aliases.items() if v['kind']=='Action' and v['id'] not in ('A1','A2') and source.refs(base.context.elements[v['id']]['trace']['source_refs'])&source.selected(selected))
            p.update(components=[dict(handle='v-component',name='V component',purpose='Perform V',grouping_reason='Independent V responsibility',alternatives=[],uncertainties=['Synthetic only'],state='draft',trace=deepcopy(tr))],responsibilities=[dict(handle='v-responsibility',component_id=dict(local_handle='v-component'),statement='Perform V',action_ids=[dict(base_handle=action)],rule_ids=[],state='draft',trace=deepcopy(tr))],unassigned_actions=[])
        if step==4:
            action=next(k for k,v in aliases.items() if v['kind']=='Action' and v['id'] not in ('A1','A2') and source.refs(base.context.elements[v['id']]['trace']['source_refs'])&source.selected(selected));resp=next(k for k,v in aliases.items() if v['kind']=='Responsibility' and v['id'] not in ('RS1','RS2') and source.refs(base.context.elements[v['id']]['trace']['source_refs'])&source.selected(selected))
            p['mappings']=[dict(source_ref=r,assessment='proposed',finding_handles=[],parts=[dict(handle='v-part.'+str(i),obligation='Represent V obligation',assignment='proposed',target='components',action_ids=[dict(base_handle=action)],primary_responsibility_ids=[dict(base_handle=resp)],supporting_responsibility_ids=[],covered_portion='Synthetic full V',remaining_gap=None,finding_handles=[])]) for i,r in enumerate(refs(source,source.units[uid].obligations))]
        value=dict(candidate_version=CANDIDATE,step=step,unit_ids=selected,scope_request_sha256=digest(readwrite),proposals=p,questions=[],inspection=[dict(source_ref=r['source_ref'],read=r['read'],verdict=r['verdict'],needed_facts=r['needed_facts'],evidence_source_refs=[r['source_ref']],finding_handles=[],reason=r['reason']) for r in analysis['inspections']],unrepresented_source_refs=[])
    if mutate:mutate(value,analysis)
    raw=dict(candidate=encode(value) if value is not None else None,analysis=encode(analysis))
    bb=binding(base,meta,provider_id='CTestController',mode=mode,step=step,units=selected,goal=goal,aliases=aliases,**raw)
    cfg=dict(**profile_pins(),marker=CONFIG,config_version=CONFIG,handler_version=HANDLER,policy_version=POLICY,limits_version=VERSION,limits=asdict(DEFAULTS),store_id=base.history.store_id,session_id=base.session_id,command_id=command,parent_command_id=base.parent_command_id,reserved_run_id=command+'.Run',started_at=NOW,
        mode=mode,step=step,unit_ids=selected,goal=goal,source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],base_model_sha256=digest(base.context.model()),base_analysis_set_sha256=digest(base.analysis_set),anchor=None,parent_metadata=meta,aliases=aliases,
        inputs={lane:dict(stage_ref=dict(command_id=command,blob_id=command+'.'+lane),sha256=sha256(data).hexdigest(),byte_length=len(data),media_type='application/json') if data is not None else None for lane,data in raw.items()},historical_reviews_pin=base.history.registry.pin(),history_binding=base.history.binding(base),authority_binding=bb,intent_sha256='0'*64)
    cfg['intent_sha256']=digest(config_intent(cfg));ContinuationVerifier(base.history).config(cfg,base,raw,parent)
    return cfg,raw


def projected(base,cfg,raw):
    state=base.history.payload();cid=cfg['command_id'];session=cfg['session_id']
    state['commands'][cid]=dict(command_id=cid,session_id=session,parent_command_id=cfg['parent_command_id'],reserved_run_id=cfg['reserved_run_id'],request=dict(kind='work',source_context_id=cfg['source_context_id'],base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],scope=None,config_artifact_id=None));state['operation_profiles'][cid]=E1
    stages=[staged(cid,cid+'.primary','config',encode(cfg))]+[staged(cid,cfg['inputs'][lane]['stage_ref']['blob_id'],'llm_response',raw[lane]) for lane in ('candidate','analysis') if raw[lane] is not None]
    for meta,data in stages:state['stages'][cid,meta['blob_id']]={**meta,'bytes':data}
    state['events'][cid,cid+'.prepared']=dict(event_id=cid+'.prepared',command_id=cid,ordinal=1,kind='prepared',payload=dict(stage_refs=[dict(command_id=cid,blob_id=m['blob_id']) for m,d in stages],attempt_id=None))
    h=HistoryData(**state,registry=base.history.registry,store_id=base.history.store_id,budget=Budget());before=h.view(session,base.pair,base.pair);primary=h._state['stages'][cid,cid+'.primary']
    ContinuationVerifier(h).config(cfg,before,raw);plan=build(cfg,before,primary,raw,NOW);state=h.payload()
    for r in plan['batch']['records']:state['records'][r['id']]=r;state['record_profiles'][r['id']]=E1;state['owners'][r['id']]=session
    for promotion in plan['batch']['artifact_sources']:
        ref=promotion['stage_ref'];state['blobs'][promotion['artifact_id']]=state['stages'][cid,ref['blob_id']]['bytes']
    data=encode(plan);a=plan['allocation'];meta,_=staged(cid,a['plan_blob_id'],'config',data);state['stages'][cid,meta['blob_id']]={**meta,'bytes':data};r=artifact(a['plan_artifact_id'],'config',data,cfg['reserved_run_id'],NOW);state['records'][r['id']]=r;state['record_profiles'][r['id']]=E1;state['owners'][r['id']]=session;state['blobs'][r['id']]=data
    for ordinal,kind,payload in [(2,'log',dict(message=MESSAGE)),(3,'finalized',dict(run_id=cfg['reserved_run_id'],promotions=plan['promotions']))]:
        eid=cid+'.'+kind;state['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=ordinal,kind=kind,payload=payload)
    h=HistoryData(**state,registry=base.history.registry,store_id=base.history.store_id,budget=Budget());before=h.view(session,base.pair,base.pair);result=h.view(session,plan['batch']['head'],plan['batch']['head']) if plan['batch']['head'] else None
    verifier=ContinuationVerifier(h);verifier.result(cfg,plan,before,result)
    if result:assert verifier.published(cid).plan()==plan
    evidence=Path(os.environ.get('S02_TEST_EVIDENCE_DIR','/tmp/dacn-C-pure-evidence'));evidence.mkdir(parents=True,exist_ok=True)
    (evidence/('detached-'+cid+'.json')).write_bytes(encode(dict(config=cfg,plan=plan,base_pair=before.pair,result_pair=result.pair if result else None,scope='Pure detached projection, not C DB writer')))
    return h,before,result,plan
