"""Pure C plan construction over a frozen T0 witness. No writer or I/O.

Domain allocations are code-derived from the committed command/reserved Run and
role/counter. A seal selects exact times/bytes; rebuilding is never a resume path.
The result checker independently reconstructs these same bytes from pinned raw.
"""
from copy import deepcopy
from .codec_boundary import encode
from .errors import S02Error
from .profiles import E1
from .repository import record
from .service import artifact,staged
from .scope import make_scope
from .h1_store import profile_pins
from .h1_builders import allscope
from .h2_graph import ModelContext,impact
from .h3_history import HistoryData
from .h3_policy import _append_only
from .h3_limits import need,digest
from .h3_continuation_contracts import PLAN,GUARD,PREDICATE,validate
from .h3_continuation_inputs import refs
from .h3_continuation_builders import candidate,project,successors,domain_records,GuardNeeded,guard_key,effective_selectors,materialized_body
from .h3_continuation_policy import check_union,admission,guard_can_resolve

MESSAGE='H3-C immutable work plan sealed'


def frozen_state(cfg,history):
    s=history._state;cid=cfg['command_id'];pin=cfg['history_binding'];ids={p['record_id'] for p in pin['records']};evs={(p['command_id'],p['event_id']) for p in pin['events']};commands={c for c,e in evs}|{cid}
    events={k:deepcopy(v) for k,v in s['events'].items() if k in evs or k[0]==cid and v['kind']!='finalized'};refs_used=set()
    def walk(v):
        if type(v) is list:
            for x in v:walk(x)
        elif type(v) is dict:
            if set(v)=={'command_id','blob_id'}:refs_used.add((v['command_id'],v['blob_id']))
            else:
                for x in v.values():walk(x)
    for e in events.values():walk(e['payload'])
    refs_used.update(k for k in s['stages'] if k[0]==cid)
    result=dict(records={i:deepcopy(r) for i,r in s['records'].items() if i in ids},record_profiles={i:p for i,p in s['record_profiles'].items() if i in ids},owners={i:o for i,o in s['owners'].items() if i in ids},
        commands={c:deepcopy(v) for c,v in s['commands'].items() if c in commands},operation_profiles={c:p for c,p in s['operation_profiles'].items() if c in commands},events=events,
        stages={k:deepcopy(v) for k,v in s['stages'].items() if k in refs_used},blobs={i:b for i,b in s['blobs'].items() if i in ids})
    need(ids<=result['records'].keys() and evs<=result['events'].keys(),'c_full_T0_witness');return result


class Allocator:
    def __init__(self,cfg,base):
        self.cfg=cfg;self.counter=0;self.ids=set();s=frozen_state(cfg,base.history);self.used={p['record_id'] for p in cfg['history_binding']['records']}|set(s['commands'])|{cfg['command_id'],cfg['reserved_run_id']}
        for i in tuple(self.used):
            r=s['records'].get(i)
            if r and r['type']=='model':
                from .validation import index_model
                es,ps=index_model(r);self.used.update(es);self.used.update(ps);self.used.update(row['id'] for row in r['body']['mappings'])
                self.used.update(m['id'] for w in r['body']['workflows'] for group in ('nodes','edges') for m in w[group])
        oldcommands={e['command_id'] for e in cfg['history_binding']['events']}
        self.used.update(eid for cid,eid in s['events'] if cid in oldcommands)
        ownrefs={r['blob_id'] for (cid,eid),e in s['events'].items() if cid==cfg['command_id'] and e['kind']=='prepared' for r in e['payload']['stage_refs']}
        self.used.update(bid for cid,bid in s['stages'] if cid in oldcommands or cid==cfg['command_id'] and bid in ownrefs)
    def key(self,role):
        identity='h3c.'+digest([self.cfg['command_id'],self.cfg['reserved_run_id'],role])
        need(identity not in self.used and identity not in self.ids,'c_allocation_collision');self.ids.add(identity);return identity
    def fresh(self):
        self.counter+=1;return self.key('allocation.'+str(self.counter))


def bindings(cfg,primary):
    return dict(command_id=cfg['command_id'],session_id=cfg['session_id'],parent_command_id=cfg['parent_command_id'],reserved_run_id=cfg['reserved_run_id'],
        primary_config_sha256=primary['sha256'],primary_config_stage_ref=dict(command_id=cfg['command_id'],blob_id=primary['blob_id']),intent_sha256=cfg['intent_sha256'],base_pair=[cfg['base_model_id'],cfg['base_analysis_set_id']],
        history_sha256=digest(cfg['history_binding']),anchor_sha256=None,authority_binding_sha256=digest(cfg['authority_binding']),historical_reviews_pin=cfg['historical_reviews_pin'],handler_version=cfg['handler_version'])


def inherited_guards(base,cfg):
    guards=deepcopy(cfg['parent_metadata']['guards'])
    for g in guards.values():
        if g.get('version')==GUARD:
            aid=g['origin_plan_artifact_id'];r=base.history._state['records'].get(aid)
            need(r is not None and r['type']=='artifact','c_guard_origin_artifact');g['origin_plan_sha256']=r['body']['sha256']
    return guards


def _new_outputs(cfg,base,parsed,projection,remap):
    raw=parsed.payload();owners={}
    for coll in ('actors','actions','workflows','data','rules','components','responsibilities'):
        for row in raw['proposals'].get(coll,[]):
            owners[row['handle']]=base.context.source.refs(row['trace']['source_refs'])
            if coll=='workflows':
                for group in ('nodes','edges'):
                    for member in row[group]:owners[member['handle']]=owners[row['handle']]
    for row in raw['proposals'].get('mappings',[]):
        for p in row['parts']:owners[p['handle']]={row['source_ref']['input_pointer']}
    for q in raw['proposals']['findings']:owners[q['handle']]=base.context.source.refs(q['trace']['source_refs'])
    aliases={**deepcopy(cfg['aliases'])}
    for handle,a in projection['local_bindings'].items():
        key='scope.'+digest([parsed.namespace,int(cfg['step']),handle]);need(key not in aliases,'c_alias_collision');aliases[key]=deepcopy(a)
    for a in aliases.values():a['id']=remap.get(a['id'],a['id'])
    outputs={}
    for uid in cfg['unit_ids']:
        family=base.context.source.units[uid].obligations;ids=sorted(projection['local_bindings'][h]['id'] for h,uses in owners.items() if uses&family)
        outputs[uid]=dict(unit_id=uid,step=int(cfg['step']),origin_command_id=cfg['command_id'],output_ids=ids,raw_sha256=parsed.sha256,source_refs=refs(base.context.source,family),aliases={k:deepcopy(a) for k,a in aliases.items() if a['id'] in ids})
    return outputs,aliases


def build(cfg,base,primary,raw,now):
    """Build only a detached plan; caller must verify/publish with checked APIs."""
    validate('Config',cfg,base.history.budget);need(set(raw)=={'candidate','analysis'},'c_raw_lanes');b=base.history.budget;b.raw_work(raw['candidate'],raw['analysis'])
    alloc=Allocator(cfg,base);planbid=alloc.key('plan_blob');planaid=alloc.key('plan_artifact');cid=cfg['command_id'];rid=cfg['reserved_run_id'];source=base.context.source
    projection=None;parsed=None;diagnostics=[];outcome='revalidated';model=base.context.model();issues=deepcopy(base.issues);rows=effective_selectors(base,cfg['parent_metadata']);guards=inherited_guards(base,cfg);outputs=None;remap={};aliases=deepcopy(cfg['aliases'])
    if cfg['mode']=='step':
        try:parsed=candidate(raw['candidate'],base,cfg)
        except S02Error as error:diagnostics=[error.error];outcome='rejected'
        if parsed is not None:
            projection,proposed,findings,newrows=project(base,cfg,parsed,alloc.fresh,now)
            try:
                check_union(base,cfg,proposed,findings,newrows,raw['analysis'],parsed.payload());rows.update(newrows)
                if int(cfg['step'])>1:
                    model,issues,remap=successors(base,cfg,proposed,findings,rows,alloc.fresh,now)
                else:model=proposed;issues+=findings
                # New findings must retain any physical footprint they claim.
                for q in issues:
                    if q['body']['issue_key'] in newrows:q['body']=materialized_body(q,model,newrows[q['body']['issue_key']],source,b)
                outputs,aliases=_new_outputs(cfg,base,parsed,projection,remap);outcome='valid'
            except GuardNeeded as error:
                outcome='guard_only';model=base.context.model();issues=deepcopy(base.issues);rows=effective_selectors(base,cfg['parent_metadata']);remap={}
                key=guard_key(cid);need(key not in rows,'c_guard_key_collision');scope=allscope(model);qid=alloc.key('guard_issue')
                q=record('issue',qid,dict(issue_key=key,supersedes_id=None,model_id=model['id'],detected_step=int(cfg['step']),kind='analysis_omission',question='Revalidate retained scope before continuing discarded candidate',reason=';'.join(error.reasons),
                    trace=dict(origin='inferred',source_refs=refs(source,source.obligations),answer_refs=[],rationale='Code rejected the complete candidate union; synthetic technical guard',issue_ids=[]),affected=scope,blocking=deepcopy(scope),status='open',answer_ids=[],resolution_event_refs=[],resolution=None,resolution_carry=None,resolution_replacement=None),now)
                issues.append(q);rows[key]=dict(issue_id=qid,issue_key=key,target_step=1,kind='all_source_uses',source_refs=refs(source,source.obligations),element_ids=list(scope['element_ids']),mapping_part_ids=list(scope['mapping_part_ids']),impact_known=False,code_task_role='merge_guard')
                guards[key]=dict(version=GUARD,issue_id=qid,issue_key=key,origin_command_id=cid,root_issue_id=qid,source_context_id=source.context_id,base_pair=base.pair,failed_candidate_sha256=parsed.sha256,failed_analysis_sha256=cfg['inputs']['analysis']['sha256'],predicate=PREDICATE,origin_plan_sha256=None,origin_plan_artifact_id=planaid)
    else:
        passed=guard_can_resolve(base,cfg,raw['analysis'],guards)
        for q in issues:
            key=q['body']['issue_key']
            if key in guards and q['body']['status']=='open':
                old=q['id'];q.update(id=alloc.key('guard_successor.'+key),created_at=now);q['body']['supersedes_id']=old
                if passed:q['body'].update(status='resolved',resolution='Code rechecked retained guard; discarded candidate remains discarded',blocking=make_scope(base.pair[0]))
    domain=[];head=None;aset=None
    if outcome!='rejected':
        domain,aset=domain_records(base,cfg,model,issues,now,alloc.key('analysis_set'));head=[model['id'],aset['id']]
    sources=[];artifacts=[];blobs={};s=frozen_state(cfg,base.history)
    inputs=[('primary',primary)]+[(lane,s['stages'][cid,cfg['inputs'][lane]['stage_ref']['blob_id']]) for lane in ('candidate','analysis') if cfg['inputs'][lane] is not None]
    for lane,stage in inputs:
        aid=alloc.key('artifact.'+lane);a=artifact(aid,stage['purpose'],stage['bytes'],rid,now);artifacts.append(a);blobs[aid]=stage['bytes'];sources.append(dict(artifact_id=aid,stage_ref=dict(command_id=cid,blob_id=stage['blob_id'])))
    rr=record('run',rid,dict(mode='replay',source_context_id=source.context_id,config_artifact_id=sources[0]['artifact_id'],base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],command_id=cid,
        result_model_id=model['id'] if head and model['id']!=base.pair[0] else None,result_analysis_set_id=aset['id'] if aset else None,steps=[int(cfg['step'])],status='rejected' if outcome=='rejected' else 'blocked',started_at=cfg['started_at'],completed_at=now,attempts=[],errors=diagnostics),cfg['started_at'])
    records=domain+artifacts+[rr]
    for r in records:s['records'][r['id']]=r;s['record_profiles'][r['id']]=E1;s['owners'][r['id']]=cfg['session_id']
    s['blobs'].update(blobs)
    # Exactly one projected log/finalized event, replacing only this command's
    # own unfinalized seal log when the witness already contains it.
    for k in [k for k,e in s['events'].items() if k[0]==cid and e['kind']=='log']:del s['events'][k]
    for ordinal,kind,payload in [(2,'log',dict(message=MESSAGE)),(3,'finalized',dict(run_id=rid,promotions=sources))]:
        eid='h3c.projection.'+digest([cid,kind]);s['events'][cid,eid]=dict(event_id=eid,command_id=cid,ordinal=ordinal,kind=kind,payload=payload)
    h=HistoryData(**s,registry=base.history.registry,store_id=cfg['store_id'],budget=b);before=h.view(cfg['session_id'],base.pair,base.pair);meta=None
    if head:
        result=h.view(cfg['session_id'],head,head)
        if model['id']!=base.pair[0]:_append_only(before,result,remap,int(cfg['step']),cfg['unit_ids'])
        meta=admission(cfg,before,result,rows,guards,raw['analysis'],projection,new_outputs=outputs,remap=remap)
        blocked=bool(meta['full_hold_reasons'] or any(p['unresolved_keys'] or p['assessment_state']!='current' for p in meta['progress_by_unit'].values()))
        rr['body']['status']='blocked' if blocked else 'completed'
    plan=dict(**profile_pins(),marker=PLAN,plan_version=PLAN,bindings=bindings(cfg,primary),allocation=dict(plan_blob_id=planbid,plan_artifact_id=planaid,created_at=now,aliases=aliases),batch=dict(records=records,artifact_sources=sources,head=head),
        promotions=sources+[dict(artifact_id=planaid,stage_ref=dict(command_id=cid,blob_id=planbid))],admission=meta,candidate_outcome=outcome,diagnostics=diagnostics,candidate_projection=projection)
    validate('Plan',plan,b);return plan
