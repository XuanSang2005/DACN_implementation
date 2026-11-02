"""Synthetic B controls. Projected graph setup is not a production writer.

IDs, stages and event sequences here are explicitly chosen by the test controller.
No trusted historical review decision is inferred by the production adapters.
"""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
from dacn_s02.codec_boundary import encode,decode
from dacn_s02.h3_history import HistoryData,ReviewRegistry,ReviewTrustContext
from dacn_s02.h3_contracts import REGISTRY
from dacn_s02.h3_checkpoint_contracts import CONFIG,PLAN,HANDLER,ADMISSION,POLICY,ANALYSIS
from dacn_s02.h3_checkpoint_checks import seed,binding,CheckpointVerifier,admission,issue_changes,aliases_for,normalized_aliases
from dacn_s02.h3_bindings import config_intent
from dacn_s02.h3_limits import Budget,DEFAULTS,VERSION,digest
from dacn_s02.h1_store import profile_pins
from dacn_s02.repository import record
from dacn_s02.service import artifact,staged
from dacn_s02.profiles import E1
from h2_checkpoint_fixtures import ScopedCase

NOW='2026-10-31T00:00:00.000Z'


def state_of(repo):
    with repo._read() as c:
        records,blobs,commands,events,stages=repo._check(c)
        return dict(records=records,blobs=blobs,commands=commands,events=events,stages=stages,
            owners={x['id']:x['session_id'] for x in c.execute('SELECT id,session_id FROM records')},
            record_profiles={x['id']:x['profile_id'] for x in c.execute('SELECT id,profile_id FROM records')},
            operation_profiles={x['command_id']:x['profile_id'] for x in c.execute('SELECT command_id,profile_id FROM operations')})


def empty_registry(store,budget,path='synthetic-control.json'):
    raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='BReviews',store_id=store,required_issue_ids=[],reviews=[]))
    return ReviewRegistry.parse(raw,ReviewTrustContext(str(path),sha256(raw).hexdigest(),'BReviews',store),budget)


def history(state,store,budget=None,registry=None):
    budget=budget or Budget();registry=registry or empty_registry(store,budget)
    return HistoryData(**state,registry=registry,store_id=store,budget=budget)


def setup_history(path,*,stage=2,guard=False):
    c=ScopedCase(path);c.bootstrap()
    if stage>=1:c.advance(1)
    if stage>=2:c.advance(2)
    if guard:c.advance(3,proof=False)
    h=history(state_of(c.repo),c.store_id)
    return c,h.view(h._state['commands'][c.parent]['session_id'],c.pair,c.pair)


def anchor_for(case,view):
    from dacn_s02.h3_bindings import _published
    from dacn_s02.h3_contracts import ANCHOR
    plan,cfg,pair,aid=_published(case.parent,view);state=view.history._state;outs=[]
    for unit,p in plan['admission']['progress_by_unit'].items():
        for step,row in p['outputs'].items():
            origin=next(cid for cid,op in state['commands'].items() if op['reserved_run_id']==row['origin_run_id']) if 'origin_run_id' in row else None
            if origin is None:
                # Origin is the unique introducing semantic step publication.
                for cid,op in state['commands'].items():
                    rb=state['records'].get(op['reserved_run_id'],{}).get('body',{});blob=state['blobs'].get(rb.get('config_artifact_id'))
                    if blob is None:continue
                    x=decode(blob)
                    if type(x) is dict and x.get('mode')=='step' and int(x.get('step',0))==int(step) and unit in x.get('unit_ids',[]) and x['inputs']['candidate']['sha256']==row['raw_sha256']:origin=cid;break
            assert origin is not None
            outs.append(dict(unit_id=unit,step=int(step),origin_command_id=origin,output_ids=row['local_ids'],raw_sha256=row['raw_sha256'],source_refs=row['source_refs'],aliases=normalized_aliases(row['aliases'])))
    return dict(version=ANCHOR,command_id=case.parent,plan_artifact_id=aid,plan_sha256=state['records'][aid]['body']['sha256'],published_pair=pair,
        source_context_id=view.context.source.context_id,snapshot_id=view.context.source.snapshot_id,transitions=[],transition_hashes=[],outputs=outs)


def raw_analysis(base,rows,units,*,held_u=True,unknown=False):
    source=base.context.source;refs=lambda ps:[dict(snapshot_id=source.snapshot_id,input_pointer=p) for p in sorted(ps)]
    return encode(dict(version=ANALYSIS,source_context_id=source.context_id,snapshot_id=source.snapshot_id,base_pair=base.pair,
        selectors_sha256=digest(sorted(rows.values(),key=lambda x:x['issue_key'])),unit_ids=units,
        inspections=[dict(source_ref=refs([p])[0],read='inspected',verdict='held' if held_u and p.startswith('/functional_requirements/0') else 'usable',
            basis_source_refs=refs([p]),needed_facts=['Unknown permission U'] if held_u and p.startswith('/functional_requirements/0') else [],reason='Explicit synthetic source inspection') for p in sorted(source.obligations)],
        independence=[dict(issue_key=q['body']['issue_key'],unit_id=u,verdict='unknown' if unknown else 'held' if held_u and min(source.units[u].obligations).startswith('/functional_requirements/0') else 'independent',
            basis_source_refs=refs(source.obligations),reason='Handwritten U held / V independent topology') for q in base.issues for u in source.units]))


def config_for(base,*,command='BCommand1',anchor=None,parent=None,unknown=False,step=None,goal='admission',unit_ids=None):
    verifier=CheckpointVerifier(base.history);mode='revalidate' if parent is not None else 'adopt'
    meta=parent.plan()['admission'] if parent else None
    rows=meta['selectors'] if meta else verifier.selector_seed(base)[0];units=sorted(base.context.source.units if unit_ids is None else unit_ids)
    step=(1 if parent else 0) if step is None else step
    raw=raw_analysis(base,rows,units,unknown=unknown);aliases={}
    if parent:aliases=parent.plan()['allocation']['aliases']
    elif anchor:aliases=aliases_for(anchor,base)
    source=base.context.source
    bb=binding(base,provider_id='BTestController',mode=mode,step=step,units=units,goal=goal,aliases=aliases,rows=rows,
        progress=meta['progress_by_unit'] if meta else None,anchor=anchor,raw=raw)
    cfg=dict(**profile_pins(),marker=CONFIG,config_version=CONFIG,handler_version=HANDLER,policy_version=POLICY,limits_version=VERSION,limits=dict(vars(DEFAULTS)),
        store_id=base.history.store_id,session_id=base.session_id,command_id=command,parent_command_id=base.parent_command_id,reserved_run_id=command+'.Run',started_at=NOW,
        mode=mode,step=step,unit_ids=units,goal=goal,source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,
        base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],base_model_sha256=digest(base.context.model()),base_analysis_set_sha256=digest(base.analysis_set),
        anchor=anchor,parent_metadata=meta,aliases=aliases,inputs=dict(candidate=None,analysis=dict(stage_ref=dict(command_id=command,blob_id=command+'.Analysis'),sha256=sha256(raw).hexdigest(),byte_length=len(raw),media_type='application/json')),
        historical_reviews_pin=base.history.registry.pin(),history_binding=base.history.binding(base),authority_binding=bb,intent_sha256='0'*64)
    cfg['intent_sha256']=digest(config_intent(cfg));verifier.config(cfg,base,raw,parent)
    return cfg,raw


def project(base,cfg,raw,parent=None):
    """Explicit immutable proposed publication, without a B repository adapter."""
    state=deepcopy(base.history._state);cmd=cfg['command_id'];rid=cfg['reserved_run_id'];session=cfg['session_id'];mid=base.pair[0]
    now=cfg['started_at'];records=[];blobs={}
    rows,guards=(cfg['parent_metadata']['selectors'],cfg['parent_metadata']['guards']) if parent else CheckpointVerifier(base.history).selector_seed(base)
    selected=[]
    changed=issue_changes(cfg,base,rows,guards,raw)
    for q in base.issues:
        key=q['body']['issue_key']
        if key in changed:
            q=record('issue',cmd+'.Guard.'+str(len(records)),changed[key],now);records.append(q)
        selected.append(q['id'])
    aset=deepcopy(base.analysis_set);aset.update(id=cmd+'.AS',created_at=now)
    aset['body'].update(revision=int(aset['body']['revision'])+1,parent_set_id=base.pair[1],issue_ids=selected,changed_record_ids=[r['id'] for r in records])
    records.append(aset)
    stages=[staged(cmd,cmd+'.Primary','config',encode(cfg)),staged(cmd,cfg['inputs']['analysis']['stage_ref']['blob_id'],'llm_response',raw)]
    sources=[]
    for meta,data in stages:
        a=artifact(cmd+'.Artifact.'+meta['purpose'],meta['purpose'],data,rid,now);records.append(a);blobs[a['id']]=data;sources.append(dict(artifact_id=a['id'],stage_ref=dict(command_id=cmd,blob_id=meta['blob_id'])))
    rr=record('run',rid,dict(mode='replay',source_context_id=cfg['source_context_id'],config_artifact_id=sources[0]['artifact_id'],base_model_id=mid,base_analysis_set_id=base.pair[1],command_id=cmd,
        result_model_id=None,result_analysis_set_id=aset['id'],steps=[] if cfg['mode']=='adopt' else [1],status='blocked',started_at=now,completed_at=now,attempts=[],errors=[]),now);records.append(rr)
    state['commands'][cmd]=dict(command_id=cmd,session_id=session,parent_command_id=cfg['parent_command_id'],reserved_run_id=rid,request=dict(kind='work',source_context_id=cfg['source_context_id'],base_model_id=mid,base_analysis_set_id=base.pair[1],scope=None,config_artifact_id=None));state['operation_profiles'][cmd]=E1
    for r in records:state['records'][r['id']]=r;state['record_profiles'][r['id']]=E1;state['owners'][r['id']]=session
    state['blobs'].update(blobs)
    for meta,data in stages:state['stages'][cmd,meta['blob_id']]={**meta,'bytes':data}
    for ordinal,kind,payload in [(1,'prepared',dict(stage_refs=[x['stage_ref'] for x in sources],attempt_id=None)),(2,'log',dict(message='H3-B immutable work plan sealed')),(3,'finalized',dict(run_id=rid,promotions=sources))]:
        eid=cmd+'.'+kind;state['events'][cmd,eid]=dict(event_id=eid,command_id=cmd,ordinal=ordinal,kind=kind,payload=payload)
    budget=Budget();h=history(state,base.history.store_id,budget,base.history.registry);before=h.view(session,base.pair,base.pair);after=h.view(session,[mid,aset['id']],[mid,aset['id']]);verifier=CheckpointVerifier(h)
    if parent:parent=verifier.published(parent.command_id)
    stage,rows,guards=verifier.config(cfg,before,raw,parent);ad=admission(cfg,before,after,stage,rows,guards,raw)
    blocked=bool(ad['full_hold_reasons'] or any(p['unresolved_keys'] or p['assessment_state']!='current' for p in ad['progress_by_unit'].values()));rr['body']['status']='blocked' if blocked else 'completed'
    plan=dict(**profile_pins(),marker=PLAN,plan_version=PLAN,bindings=dict(command_id=cmd,session_id=session,parent_command_id=cfg['parent_command_id'],reserved_run_id=rid,
        primary_config_sha256=digest(cfg),primary_config_stage_ref=sources[0]['stage_ref'],intent_sha256=cfg['intent_sha256'],base_pair=base.pair,history_sha256=digest(cfg['history_binding']),anchor_sha256=digest(cfg['anchor']) if cfg['anchor'] else None,authority_binding_sha256=digest(cfg['authority_binding']),historical_reviews_pin=cfg['historical_reviews_pin'],handler_version=HANDLER),
        allocation=dict(plan_blob_id=cmd+'.Plan',plan_artifact_id=cmd+'.PlanArtifact',created_at=now,aliases=cfg['aliases']),batch=dict(records=records,artifact_sources=sources,head=[mid,aset['id']]),
        promotions=sources+[dict(artifact_id=cmd+'.PlanArtifact',stage_ref=dict(command_id=cmd,blob_id=cmd+'.Plan'))],admission=ad,candidate_outcome='adopted' if cfg['mode']=='adopt' else 'revalidated',diagnostics=[])
    data=encode(plan);meta,_=staged(cmd,cmd+'.Plan','config',data);state['stages'][cmd,meta['blob_id']]={**meta,'bytes':data};a=artifact(cmd+'.PlanArtifact','config',data,rid,now);state['records'][a['id']]=a;state['record_profiles'][a['id']]=E1;state['owners'][a['id']]=session;state['blobs'][a['id']]=data
    state['events'][cmd,cmd+'.finalized']['payload']['promotions']=plan['promotions']
    h=history(state,base.history.store_id,Budget(),base.history.registry)
    return h,h.view(session,base.pair,base.pair),h.view(session,[mid,aset['id']],[mid,aset['id']]),plan
