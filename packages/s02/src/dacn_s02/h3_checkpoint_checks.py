"""Pure B-P01 checks over a canonically verified detached whole store.

No persistence, allocation, clocks, authority I/O or historical decision source.
Published plans are walked oldest-first with explicit cycle/depth bounds.
"""
from copy import deepcopy
from dataclasses import dataclass
from .codec_boundary import encode, decode
from .errors import S02Error
from .profiles import E1, blocking_statuses
from .scope import make_scope
from .h2_graph import impact
from .h2_policy import materialize
from .h3_history import HistoryView
from .h3_bindings import config_intent, check_anchor, _published, verify_guard_origin, verify_task_origin
from .h3_policy import selectors as checked_selectors, unassessed_progress, SemanticTrustContext, _view as checked_view
from .h3_limits import need, digest
from .h3_checkpoint_contracts import validate, CONFIG, PLAN, ADMISSION, POLICY, BINDING


def h2_published(command,view):
    """Actual versioned H2 published reader, without its history-free context.

    published_plan/primary/result/projection checks are detached primitives; they
    do not access the Repository. Whole-store checks already used external R.
    """
    result=_published(command,view)
    plan,cfg,_,_=result;key=command,digest(plan),digest(cfg)
    cache=getattr(view.history,'_b_checked_h2_publishers',None)
    if cache is None:cache={};view.history._b_checked_h2_publishers=cache
    view.history.budget.check()
    if key not in cache:
        from .h2_store import ScopeStore
        s=view.history._state;op=s['commands'][command]
        events=sorted((e for (c,_),e in s['events'].items() if c==command),key=lambda e:e['ordinal'])
        cmd=dict(operation=op,state='finalized',events=events,run=s['records'][op['reserved_run_id']])
        checked=ScopeStore(None,view.history.budget).published_plan(cmd,s)
        need(checked==plan,'b_H2_actual_published_reader');cache[key]=True
    return result


@dataclass(frozen=True)
class CheckpointGrant:
    binding_sha256: str
    control_sha256: str
    provider_id: str
    decision: str


def authorize(raw,trust,value,budget):
    """B-only exact tuple. Neither A approvals nor historical reviews grant work."""
    from hashlib import sha256
    need(type(trust) is SemanticTrustContext,'b_external_semantic_context')
    validate('Binding',value,budget)
    need(type(raw) is bytes and sha256(raw).hexdigest()==trust.expected_sha256,'b_external_authority_hash')
    control=validate('Authority',budget.parse(raw,kind='authority',slot='b.authority'),budget)
    need(control['provider_id']==trust.provider_id==value['provider_id'] and control['provider_version']==trust.provider_version==value['provider_version'],'b_authority_provider')
    selected=[r for r in control['approvals'] if encode(r['binding'])==encode(value)]
    return CheckpointGrant(digest(value),trust.expected_sha256,trust.provider_id,selected[0]['decision'] if len(selected)==1 else 'deny')


def dependencies(pin,view):
    """Verify the full T0 inventory, not a refreshed head or a narrower slice."""
    h=view.history;s=h._state;b=h.budget
    validate('History',pin,b)
    need(pin['historical_reviews_pin']==h.registry.pin(),'b_dependency_registry')
    ids=[p['record_id'] for p in pin['records']]
    evs=[(p['command_id'],p['event_id']) for p in pin['events']]
    need(len(ids)==len(set(ids)) and len(evs)==len(set(evs)),'b_dependency_inventory_unique')
    for p in pin['records']:
        b.check();need(p['record_id'] in s['records'] and digest(s['records'][p['record_id']])==p['sha256'],'b_dependency_record')
    for p in pin['events']:
        b.check();key=p['command_id'],p['event_id']
        need(key in s['events'] and digest(s['events'][key])==p['sha256'],'b_dependency_event')
    # All operations in the T0 whole graph have a prepared event. Their profile
    # inventory and all Record owners/profiles must match the original binding.
    commands={c for c,e in evs if s['events'][c,e]['kind']=='prepared'}
    need(commands=={c for c,e in evs},'b_dependency_prepared_inventory')
    selected=set(ids)
    # The original A binding hashes exact-codec maps in their checked inventory
    # order. Filter current inventory in that order; set iteration would change
    # exact bytes even when all profiles/owners remained identical.
    owners={i:v for i,v in s['owners'].items() if i in selected}
    profiles={i:v for i,v in s['record_profiles'].items() if i in selected}
    operations={c:v for c,v in s['operation_profiles'].items() if c in commands}
    need(digest(dict(records=profiles,operations=operations,owners=owners))==pin['owner_profiles_sha256'],'b_dependency_owners_profiles')
    seen=set()
    for p in pin['snapshots']:
        sid=p['snapshot_id'];need(sid not in seen,'b_dependency_snapshot_unique');seen.add(sid)
        need(sid in h._snapshots and digest(h._snapshots[sid])==p['sha256'],'b_dependency_snapshot')
        archives={s['records'][r['body']['envelope_artifact_id']]['body']['sha256'] for i,r in s['records'].items() if i in profiles and r['type']=='source_context' and r['body']['snapshot_id']==sid}
        need(bool(archives) and sorted(archives)[0]==p['archive_sha256'],'b_dependency_archive')
    need(seen=={s['records'][i]['body']['snapshot_id'] for i in ids if s['records'][i]['type']=='source_context'},'b_dependency_snapshot_inventory')
    need(pin['current_issues']=={q['body']['issue_key']:q['id'] for q in view.issues},'b_dependency_current_selection')
    return deepcopy(pin)


def seed(view):
    """Conservative selectors; only actual H2 publication may supply known impact.

    Stage completion is never taken here. H2 code guards keep their verified
    origins; all other unproven impacts remain global holds.
    """
    s=view.history._state;cmd=view.parent_command_id;old=None;guards={}
    run=s['records'][s['commands'][cmd]['reserved_run_id']]['body']
    raw=s['blobs'].get(run['config_artifact_id'])
    if raw is not None:
        cfg=view.history.budget.parse(raw,kind='config',slot='history.config.'+run['config_artifact_id'])
        marker=cfg.get('marker') if type(cfg) is dict else None
        need(marker!='s02_2a_work_config','b_h1_bridge_unsupported')
        need(marker in (None,'s02-h2-config/0.1.0-draft.2'),'b_publisher_version_unsupported')
        if marker=='s02-h2-config/0.1.0-draft.2':old=h2_published(cmd,view)[0]
    rows={}
    for q in view.issues:
        key=q['body']['issue_key'];prior=old['admission']['selectors'].get(key) if old else None
        if prior is not None:
            need(prior['issue_id']==q['id'],'b_h2_selector_current')
            row={k:deepcopy(v) for k,v in prior.items() if k!='version'}
            row['target_step']=1;row['code_task_role']=None
        else:
            row=dict(issue_id=q['id'],issue_key=key,target_step=1,kind='all_source_uses',
                source_refs=deepcopy(q['body']['trace']['source_refs']),element_ids=list(q['body']['blocking']['element_ids']),
                mapping_part_ids=list(q['body']['blocking']['mapping_part_ids']),impact_known=False,code_task_role=None)
        origin=task_origin(q,view)
        if origin is not None:row.update(target_step=origin['target_step'],code_task_role=origin['role'])
        if old and key in old['admission']['guards']:
            g=old['admission']['guards'][key]
            origin=dict(issue_id=q['id'],issue_key=key,origin_command_id=g['origin_command_id'],root_issue_id=g['root_issue_id'],
                source_context_id=view.context.source.context_id,base_pair=g['base_pair'],failed_candidate_sha256=g['candidate_sha256'],
                failed_analysis_sha256=g['analysis_sha256'],predicate=g['predicate'],origin_plan_sha256='0'*64)
            # The introducing guard plan may precede the current H2 publisher.
            plan,_,_,aid=h2_published(g['origin_command_id'],view)
            origin['origin_plan_sha256']=s['records'][aid]['body']['sha256']
            verify_guard_origin(origin,view);guards[key]=origin;row['code_task_role']='merge_guard'
        rows[key]=row
    checked_selectors(view,list(rows.values()),list(task_inventory(view).values()),list(guards.values()))
    return rows,guards


def analysis(raw,cfg,base):
    b=base.history.budget;e=validate('Analysis',b.parse(raw,kind='raw',slot='b.analysis.'+cfg['command_id']),b)
    source=base.context.source
    need(e['source_context_id']==source.context_id and e['snapshot_id']==source.snapshot_id and e['base_pair']==base.pair and
         e['unit_ids']==cfg['unit_ids'] and e['selectors_sha256']==cfg['authority_binding']['current_selectors_sha256'],'b_analysis_binding')
    inspections={};pairs={}
    for row in e['inspections']:
        ptr=source.source(row['source_ref'],obligation=True);need(ptr not in inspections,'b_duplicate_inspection')
        refs=source.refs(row['basis_source_refs'])
        need(row['verdict']=='held' or row['read']=='inspected' and ptr in refs and not row['needed_facts'],'b_inspection_basis')
        inspections[ptr]=row
    need(set(inspections)==source.obligations,'b_full_inspection_inventory')
    keys={q['body']['issue_key'] for q in base.issues}
    for row in e['independence']:
        key=row['issue_key'],row['unit_id'];need(key not in pairs,'b_duplicate_independence')
        need(key[0] in keys and key[1] in source.units,'b_independence_refs');source.refs(row['basis_source_refs']);pairs[key]=row
    return inspections,pairs


def intent_value(mode,step,units,goal,aliases,rows,progress):
    return dict(mode=mode,step=step,unit_ids=units,goal=goal,aliases_sha256=digest(aliases),
                current_selectors_sha256=digest(sorted(rows.values(),key=lambda x:x['issue_key'])),
                progress_before_sha256=digest(progress) if progress is not None else None)


def aliases_for(anchor,base):
    """Only current Issue aliases rebind by the unchanged key, never history refs."""
    aliases={};s=base.history._state;current={q['body']['issue_key']:q['id'] for q in base.issues}
    if anchor is None:return aliases
    for out in anchor['outputs']:
        for key,a in out['aliases'].items():
            value=deepcopy(a)
            if value['kind']=='Issue':
                old=s['records'].get(value['id'])
                need(old is not None and old['type']=='issue' and s['owners'][old['id']]==base.session_id,'b_alias_issue_history')
                issuekey=old['body']['issue_key'];need(issuekey in current,'b_alias_issue_key')
                value['id']=current[issuekey]
            need(key not in aliases or aliases[key]==value,'b_anchor_alias_conflict');aliases[key]=value
    return aliases


def normalized_aliases(values):
    """H2 locator names map to the already specified H3 workflow member kinds."""
    result=deepcopy(values)
    for a in result.values():a['kind']={'Node':'WorkflowNode','Edge':'WorkflowEdge'}.get(a['kind'],a['kind'])
    return result


def workflow_members(context):
    return {x['id']:x for w in context.body['workflows'] for field in ('nodes','edges') for x in w[field]}


def binding(view,*,provider_id,mode,step,units,goal,aliases,rows,progress,anchor,raw):
    source=view.context.source
    return validate('Binding',dict(version=BINDING,purpose='synthetic_test_only',provider_id=provider_id,provider_version='local-synthetic/1',policy_version=POLICY,
        store_id=view.history.store_id,session_id=view.session_id,parent_command_id=view.parent_command_id,source_context_id=source.context_id,snapshot_id=source.snapshot_id,
        archive_sha256=source.archive_sha256,base_pair=view.pair,base_model_sha256=digest(view.context.model()),base_analysis_set_sha256=digest(view.analysis_set),
        operation=mode,goal=goal,step=step,unit_ids=units,aliases_sha256=digest(aliases),current_selectors_sha256=digest(sorted(rows.values(),key=lambda x:x['issue_key'])),
        progress_before_sha256=digest(progress) if progress is not None else None,
        retained_assessment_hashes=sorted({digest(p['assessment']) for p in (progress or {}).values() if p['assessment'] is not None}),
        read_write_intent_sha256=digest(intent_value(mode,step,units,goal,aliases,rows,progress)),candidate_sha256=None,candidate_length=0,
        analysis_sha256=__import__('hashlib').sha256(raw).hexdigest(),analysis_length=len(raw),history_sha256=digest(view.history.binding(view)),
        anchor_sha256=digest(anchor) if anchor is not None else None,historical_reviews_pin=view.history.registry.pin()),view.history.budget)


def task_origin(q,base):
    """Preserve a task's checked H2 origin without granting a B build permit."""
    if q['body']['kind']!='verification' or q['body']['answer_ids'] or q['body']['resolution_carry'] is not None or q['body']['resolution_replacement'] is not None:return None
    cache=getattr(base.history,'_b_task_origins',None)
    if cache is None:cache={};base.history._b_task_origins=cache
    cachekey=q['id'],digest(q);base.history.budget.check()
    if cachekey in cache:return deepcopy(cache[cachekey])
    s=base.history._state;key=q['body']['issue_key'];root=q;seen=set()
    while root['body']['supersedes_id'] is not None:
        base.history.budget.check();need(root['id'] not in seen,'b_task_lineage');seen.add(root['id']);root=s['records'][root['body']['supersedes_id']]
    for cid,op in s['commands'].items():
        if op['session_id']!=base.session_id:continue
        run=s['records'].get(op['reserved_run_id']);sid=run['body']['result_analysis_set_id'] if run else None
        if sid is None or root['id'] not in s['records'][sid]['body']['changed_record_ids']:continue
        cfgraw=s['blobs'].get(run['body']['config_artifact_id'])
        if cfgraw is None:continue
        cfg=decode(cfgraw)
        if type(cfg) is not dict or cfg.get('marker')!='s02-h2-config/0.1.0-draft.2':continue
        plan,_,_,aid=h2_published(cid,base);declared=plan['admission']['tasks'].get(key)
        if declared is None:break
        origin={k:declared[k] for k in ('origin_command_id','root_issue_id','unit_ids','target_step','role','predicate')}
        origin.update(issue_id=q['id'],issue_key=key,origin_plan_sha256=s['records'][aid]['body']['sha256'])
        verify_task_origin(origin,base);cache[cachekey]=deepcopy(origin);return origin
    cache[cachekey]=None;return None


def _builder_task(q,base):return task_origin(q,base) is not None


def task_inventory(view):
    result={}
    for q in view.issues:
        origin=task_origin(q,view)
        if origin is not None:result[q['body']['issue_key']]=origin
    return result


def _guard_pass(base,cfg,rows,guards,inspections,pairs):
    if cfg['mode']!='revalidate':return False
    ctx=base.context;source=ctx.source
    holds=checked_selectors(base,list(rows.values()),list(task_inventory(base).values()),list(guards.values()))
    other=set()
    for q in base.issues:
        if q['body']['issue_key'] in guards or q['body']['status'] not in blocking_statuses(E1):continue
        if _builder_task(q,base):continue
        s=holds[q['id']]
        other.update(source.obligations if s.kind=='all_source_uses' or not s.impact_known else
                     {p for f in source.families if f.obligations&s.sources for p in f.obligations})
    ok=all(r['read']=='inspected' and (r['verdict']!='held' or p in other) for p,r in inspections.items())
    for key,g in guards.items():
        verify_guard_origin(g,base)
        origin=h2_published(g['origin_command_id'],base)[0]['admission']['guards'][key]
        failed=origin.get('failed_candidate_model')
        if failed is not None:
            from .h2_graph import ModelContext
            need(digest(failed)==origin['failure_context_sha256'],'b_guard_failed_context_pin')
            old=base.history._state['records'][g['base_pair'][0]]
            impact(ModelContext(old,source,base.history.budget),ModelContext(failed,source,base.history.budget))
        for unit in source.units:
            p=pairs.get((key,unit));held=bool(source.units[unit].obligations&other)
            ok &= bool(p and p['verdict']==('held' if held else 'independent') and source.obligations<=source.refs(p['basis_source_refs']))
    ok &= all(x=='ACTION_WITHOUT_PART' for x in ctx.closure(*ctx.source_seed(source.obligations)).reasons)
    return bool(ok)


def issue_changes(cfg,base,rows,guards,raw):
    """Only previously published H2 technical guards may get DIRECT successors."""
    inspections,pairs=analysis(raw,cfg,base);passed=_guard_pass(base,cfg,rows,guards,inspections,pairs)
    result={}
    if cfg['mode']=='revalidate':
        for key in guards:
            q=base.issue(key)
            if q['body']['status']!='open':continue
            body=deepcopy(q['body']);body['supersedes_id']=q['id']
            body['status']='resolved' if passed else 'open'
            body['resolution']='Code checked retained AS-only guard; synthetic only' if passed else None
            if passed:body['blocking']=make_scope(base.pair[0])
            result[key]=body
    return result


def admission(cfg,base,result,stages,rows,guards,raw):
    """Deterministically derive all result assessments, independent of plan claims."""
    b=base.history.budget;ctx=result.context;source=ctx.source
    inspections,pairs=analysis(raw,cfg,base)
    current={q['body']['issue_key']:q for q in result.issues};previous={q['body']['issue_key']:q for q in base.issues}
    rows=deepcopy(rows);guards=deepcopy(guards)
    for k,q in current.items():
        rows[k]['issue_id']=q['id']
        if k in guards:guards[k]['issue_id']=q['id']
    tasks=task_inventory(result)
    holds=checked_selectors(result,list(rows.values()),list(tasks.values()),list(guards.values()))
    roles=[];summaries=[]
    for key,q in current.items():
        p=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        roles.append(dict(issue_key=key,predecessor_issue_id=q['body']['supersedes_id'],current_issue_id=q['id'],
            origin_issue_id=p['origin_issue_id'] if p else None,obsolete_issue_id=p.get('obsolete_issue_id') if p else None,
            replacement_issue_id=p.get('replacement_issue_id') if p else None))
        if previous[key]['id']!=q['id']:
            summaries.append(dict(issue_key=key,branch='CARRY' if q['body']['resolution_carry'] else 'REPLACEMENT' if p else 'DIRECT',
                assessment=p['assessment'] if p else None,proof_record_id=q['id'],proof_sha256=digest(q),reason_codes=[]))
    roles.sort(key=lambda x:x['issue_key']);summaries.sort(key=lambda x:x['issue_key'])
    active=[q for q in result.issues if q['body']['status'] in blocking_statuses(E1)];held={p for p,r in inspections.items() if r['read']!='inspected' or r['verdict']=='held'}
    full=set();unresolved={u:[] for u in source.units};unit_reasons={u:set() for u in source.units}
    covered=set()
    for q in active:
        sel=holds[q['id']];fp=materialize(ctx,sel,q)
        # Adoption inspects stage 1. A proven later-stage task keeps its actual
        # target predicate; it is not a stage-1 business blocker. No B builder
        # exemption applies at the task's target stage.
        if max(1,int(cfg['step']))<sel.target_step:continue
        refs=source.obligations if not sel.impact_known or sel.kind=='all_source_uses' else {p for f in source.families if f.obligations&sel.sources for p in f.obligations}
        covered.update(refs)
        for uid,f in source.units.items():
            target=ctx.closure(*ctx.source_seed(f.obligations))
            touches=not sel.impact_known or sel.kind=='all_source_uses' or bool(f.obligations&refs or target.source_uses&refs or target.elements&sel.elements or target.parts&sel.parts or target.uses&fp.uses or target.active_parts&fp.active_parts)
            proof=pairs.get((sel.issue_key,uid))
            independent=bool(proof and proof['verdict']=='independent' and (f.obligations|sel.sources)<=source.refs(proof['basis_source_refs']))
            if touches or not independent:unresolved[uid].append(sel.issue_key)
    if held-covered:full.add('SOURCE_HOLD_MISSING')
    if any(r['read']!='inspected' for r in inspections.values()):full.add('INVENTORY_UNINSPECTED')
    progress=deepcopy(stages)
    for uid,p in progress.items():
        actual=ctx.closure(*ctx.source_seed(source.units[uid].obligations))
        unit_reasons[uid].update(x for x in actual.reasons if x!='ACTION_WITHOUT_PART' or int(cfg['step'])==4)
        if any(ctx.elements[i]['initiator']=='unknown' for i in actual.actions):unit_reasons[uid].add('INITIATOR_UNKNOWN')
        if any(ctx.parts[i]['assignment']!='proposed' or ctx.parts[i]['remaining_gap'] is not None for i in actual.parts):unit_reasons[uid].add('PART_GAP')
        p['actual_output_ids']=sorted(set(p['actual_output_ids'])|actual.elements|actual.parts)
        p['actual_output_ids']=sorted(set(p['actual_output_ids'])|{x['id'] for w in ctx.body['workflows'] if w['id'] in actual.elements for field in ('nodes','edges') for x in w[field]})
        p['unresolved_keys']=sorted(unresolved[uid])
        if p['work_completed_through']==0 and p['actual_output_ids']:state='needs_revalidation';unit_reasons[uid].add('PROGRESS_PROOF_REQUIRED')
        elif any(k in guards for k in p['unresolved_keys']):state='needs_revalidation'
        elif p['unresolved_keys'] or held&source.units[uid].obligations or full or unit_reasons[uid]:state='assessed_held'
        else:state='current'
        p.update(assessment_state=state,latest_checked_pair=result.pair,next_tasks=[] if int(p['work_completed_through'])==4 else [int(p['work_completed_through'])+1])
    full.update(x for rr in unit_reasons.values() for x in rr)
    meta=dict(marker=ADMISSION,policy_version=POLICY,from_pair=base.pair,result_pair=result.pair,
        obligations=[dict(source_ref=r['source_ref'],mapping_row_id=r['id'],assessment=r['assessment'],mapping_part_ids=[p['id'] for p in r['parts']],issue_ids=r['issue_ids']) for r in ctx.body['mappings']],
        selectors=rows,tasks=tasks,guards=guards,progress_by_unit=progress,retained_assessments=[],issue_roles=roles,transitions=summaries,full_hold_reasons=sorted(full))
    delta=impact(base.context,ctx)
    stage_inventory={u:{k:p[k] for k in ('work_completed_through','outputs','actual_output_ids')} for u,p in sorted(progress.items())}
    proof=digest(dict(history_sha256=digest(cfg['history_binding']),analysis_sha256=cfg['inputs']['analysis']['sha256'],
        authority_binding_sha256=digest(cfg['authority_binding']),historical_reviews_pin=cfg['historical_reviews_pin'],
        anchor_sha256=digest(cfg['anchor']) if cfg['anchor'] is not None else None,issue_roles=roles,transitions=summaries,full_hold_reasons=meta['full_hold_reasons'],stage_inventory=stage_inventory))
    for uid,p in progress.items():
        prior=cfg['parent_metadata']['progress_by_unit'][uid]['assessment'] if cfg['parent_metadata'] else None
        p['assessment']=dict(from_pair=base.pair,result_pair=result.pair,parent_assessment_sha256=digest(prior) if prior is not None else None,
            source_sha256=digest(dict(source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,obligations=[dict(snapshot_id=source.snapshot_id,input_pointer=x) for x in sorted(source.obligations)])),
            diff_sha256=digest(dict(elements=sorted(delta.changed_elements),parts=sorted(delta.changed_parts),rows=sorted(delta.changed_rows),source_changed=delta.source_changed)),
            context_sha256=digest(ctx.model()),closure_sha256=digest(dict(before=delta.before.scope(),after=delta.after.scope())),proof_sha256=proof,
            result_model_sha256=digest(ctx.model()),result_analysis_set_sha256=digest(result.analysis_set),output_refs=deepcopy(p['outputs']),state=p['assessment_state'])
        validate('Progress',p,b)
    retained={}
    for _,p in sorted(progress.items()):retained.setdefault(digest(p['assessment']),deepcopy(p['assessment']))
    meta['retained_assessments']=list(retained.values())
    return validate('Admission',meta,b)


@dataclass(frozen=True)
class PublishedCheckpoint:
    command_id: str
    config_raw: bytes
    plan_raw: bytes

    def config(self):return decode(self.config_raw)
    def plan(self):return decode(self.plan_raw)


@dataclass(frozen=True)
class CheckpointStageEvidence:
    anchor_sha256: str
    raw: bytes
    anchor_raw: bytes

    def payload(self):return decode(self.raw)


class CheckpointVerifier:
    def __init__(self,history):self.history=history;self.cache={};self.active=set()

    def view(self,pair,session):return self.history.view(session,pair,pair)

    def checked_view(self,view):
        checked_view(view);need(view.history is self.history,'b_view_history')
        actual=self.view(view.pair,view.session_id)
        need(view.parent_command_id==actual.parent_command_id,'b_view_publisher')
        need(type(view.context) is type(actual.context) and view.context.budget is self.history.budget,'b_view_context_type_budget')
        need(view.context.source.__dict__==actual.context.source.__dict__,'b_view_source_inventory')
        for key,value in actual.context.__dict__.items():
            if key in ('source','budget'):continue
            provided=view.context.__dict__.get(key)
            if key in ('source_elements','source_parts','action_parts','action_rules','action_support'):
                # Existing closure indexes memoize empty defaultdict entries.
                # Their absence/presence is not a new edge or source use.
                need(type(provided) is type(value),'b_view_context_indices')
                need({k:v for k,v in provided.items() if v}=={k:v for k,v in value.items() if v},'b_view_context_indices')
            else:need(provided==value,'b_view_context_indices')
        return actual

    def selector_seed(self,base):
        s=self.history._state;cid=base.parent_command_id;run=s['records'][s['commands'][cid]['reserved_run_id']]['body']
        raw=s['blobs'].get(run['config_artifact_id'])
        if raw is not None:
            cfg=self.history.budget.parse(raw,kind='config',slot='history.config.'+run['config_artifact_id'])
            if type(cfg) is dict and cfg.get('marker')==CONFIG:
                plan=self.published(cid).plan()
                return deepcopy(plan['admission']['selectors']),deepcopy(plan['admission']['guards'])
        return seed(base)

    def anchor(self,value,base):
        """Version-dispatched stage proof; B transports only immutable AS paths."""
        base=self.checked_view(base)
        validate('Anchor',value,self.history.budget);s=self.history._state
        commands=[value['command_id'],*[t['command_id'] for t in value['transitions']]]
        def is_b(cid):
            need(cid in s['commands'],'b_anchor_command')
            op=s['commands'][cid]
            finals=[e for (c,_),e in s['events'].items() if c==cid and e['kind']=='finalized']
            need(len(finals)==1 and finals[0]['payload']['run_id']==op['reserved_run_id'],'b_anchor_finalized')
            run=s['records'].get(op['reserved_run_id'])
            need(run is not None and run['type']=='run','b_anchor_run')
            rb=run['body']
            need(op['session_id']==base.session_id and s['owners'][run['id']]==base.session_id,'b_anchor_session')
            need(rb['command_id']==cid and rb['status'] in ('completed','blocked') and rb['result_analysis_set_id'] is not None,'b_anchor_publication')
            need(rb['config_artifact_id'] in s['blobs'],'b_anchor_config')
            raw=s['blobs'][rb['config_artifact_id']]
            cfg=self.history.budget.parse(raw,kind='config',slot='b.config.'+cid)
            return type(cfg) is dict and cfg.get('marker')==CONFIG
        nested=any(a['kind'] in ('WorkflowNode','WorkflowEdge') for out in value['outputs'] for a in out['aliases'].values())
        if not any(is_b(c) for c in commands) and not nested:
            for c in dict.fromkeys([*commands,*[o['origin_command_id'] for o in value['outputs']]]):h2_published(c,base)
            return check_anchor(value,base)
        source=base.context.source
        need(value['source_context_id']==source.context_id and value['snapshot_id']==source.snapshot_id,'b_anchor_source')
        pair=value['published_pair'];start=self.view(pair,base.session_id)
        if is_b(value['command_id']):
            first=self.published(value['command_id']).plan();aid=first['allocation']['plan_artifact_id']
            need(first['batch']['head']==pair and aid==value['plan_artifact_id'] and s['records'][aid]['body']['sha256']==value['plan_sha256'],'b_anchor_actual_publisher')
        else:
            first,_,actualpair,aid=h2_published(value['command_id'],start)
            need(actualpair==pair and aid==value['plan_artifact_id'] and s['records'][aid]['body']['sha256']==value['plan_sha256'],'b_anchor_actual_H2_publisher')
        outputs=deepcopy(value['outputs']);keys=[(o['unit_id'],int(o['step'])) for o in outputs];units={u for u,_ in keys}
        def inventory(plan):
            result={}
            for u,p in plan['admission']['progress_by_unit'].items():
                rows=p['outputs']
                if type(rows) is dict:result.update({(u,int(k)):v for k,v in rows.items()})
                else:result.update({(u,int(v['step'])):v for v in rows})
            return result
        def match(out,actual):
            need(set(out['output_ids'])==set(actual.get('output_ids',actual.get('local_ids',[]))) and out['raw_sha256']==actual['raw_sha256'] and out['source_refs']==actual['source_refs'] and out['aliases']==normalized_aliases(actual['aliases']),'b_anchor_output_inventory')
        inv=inventory(first);need(len(keys)==len(set(keys)) and set(keys)=={k for k in inv if k[0] in units},'b_anchor_full_stages')
        for out in outputs:
            match(out,inv[out['unit_id'],int(out['step'])])
            need(source.refs(out['source_refs'])==source.units[out['unit_id']].obligations,'b_anchor_full_family')
            origin,ocfg,opair,_=h2_published(out['origin_command_id'],start)
            need(ocfg['mode']=='step' and int(ocfg['step'])==int(out['step']) and out['unit_id'] in ocfg['unit_ids'] and origin['candidate_outcome']=='valid','b_anchor_raw_origin_step')
            original=inventory(origin);need((out['unit_id'],int(out['step'])) in original,'b_anchor_origin_inventory');match(out,original[out['unit_id'],int(out['step'])])
            pin=ocfg['inputs']['candidate'];need(pin['sha256']==out['raw_sha256'],'b_anchor_origin_raw_hash')
            final=next(e for (c,_),e in s['events'].items() if c==out['origin_command_id'] and e['kind']=='finalized')
            ref=dict(command_id=out['origin_command_id'],blob_id=pin['blob_id']);promoted=[p['artifact_id'] for p in final['payload']['promotions'] if p['stage_ref']==ref]
            need(len(promoted)==1 and s['records'][promoted[0]]['body']['sha256']==out['raw_sha256'],'b_anchor_origin_promoted_raw')
            context=self.view(opair,base.session_id).context;members=workflow_members(context)
            valid=set(context.elements)|set(context.parts)|set(members)|set(s['records'][opair[1]]['body']['issue_ids'])
            need(set(out['output_ids'])<=valid,'b_anchor_origin_typed_ids')
            for a in out['aliases'].values():
                if a['kind']=='WorkflowNode':need(a['id'] in {x['id'] for w in context.body['workflows'] for x in w['nodes']},'b_anchor_origin_node')
                if a['kind']=='WorkflowEdge':need(a['id'] in {x['id'] for w in context.body['workflows'] for x in w['edges']},'b_anchor_origin_edge')
        latest=first
        for t in value['transitions']:
            self.history.budget.check();need(t['from_pair']==pair and is_b(t['command_id']),'b_anchor_AS_transition_version')
            nxt=self.published(t['command_id']).plan();newpair=nxt['batch']['head']
            need(nxt['bindings']['base_pair']==pair and newpair==t['to_pair'] and newpair[0]==pair[0],'b_anchor_AS_transition_pair')
            need(t['source_context_id']==source.context_id and t['snapshot_id']==source.snapshot_id,'b_anchor_transition_source')
            need(t['parent_assessment_sha256']==digest(latest['admission']['progress_by_unit']) and t['result_assessment_sha256']==digest(nxt['admission']['progress_by_unit']),'b_anchor_assessment_chain')
            old=self.view(pair,base.session_id);new=self.view(newpair,base.session_id);delta=impact(old.context,new.context)
            need(t['diff_sha256']==digest(dict(elements=sorted(delta.changed_elements),parts=sorted(delta.changed_parts),rows=sorted(delta.changed_rows),source_changed=delta.source_changed)) and
                 t['closure_sha256']==digest(dict(before=delta.before.scope(),after=delta.after.scope())),'b_anchor_actual_diff')
            tables={'element':({**old.context.elements,**workflow_members(old.context)},{**new.context.elements,**workflow_members(new.context)}),'part':(old.context.parts,new.context.parts),'row':(old.context.rows,new.context.rows),
                    'issue':({q['id']:q for q in old.issues},{q['id']:q for q in new.issues})}
            correspond={};seen=set()
            for x in t['correspondence']:
                key=x['kind'],x['from_id'];need(key not in seen,'b_anchor_correspondence_unique');seen.add(key)
                a,b=tables[x['kind']];need(x['from_id'] in a and x['to_id'] in b,'b_anchor_correspondence_refs')
                need(x['from_context_sha256']==digest(a[x['from_id']]) and x['to_context_sha256']==digest(b[x['to_id']]),'b_anchor_correspondence_hash')
                if x['relation']=='unchanged':need(x['from_id']==x['to_id'] and a[x['from_id']]==b[x['to_id']],'b_anchor_unchanged')
                elif x['relation']=='current_ref_rebind' and x['kind']=='issue':
                    expected=deepcopy(a[x['from_id']]);expected.update(id=x['to_id'],created_at=b[x['to_id']]['created_at']);expected['body']['supersedes_id']=x['from_id']
                    need(expected==b[x['to_id']],'b_anchor_issue_rebind')
                else:need(False,'b_anchor_incomplete_correspondence')
                correspond[x['from_id']]=x['to_id']
            for out in outputs:
                need(set(out['output_ids'])<=correspond.keys() and all(a['id'] in correspond for a in out['aliases'].values()),'b_anchor_correspondence_coverage')
                out['output_ids']=[correspond[i] for i in out['output_ids']]
                for a in out['aliases'].values():a['id']=correspond[a['id']]
            latest=nxt;pair=newpair;inv=inventory(latest)
            need({k for k in inv if k[0] in units}=={(o['unit_id'],int(o['step'])) for o in outputs},'b_anchor_no_new_completed_work')
            for out in outputs:match(out,inv[out['unit_id'],int(out['step'])])
        need(pair==base.pair,'b_anchor_to_entry')
        projected=unassessed_progress(base)
        for uid,p in latest['admission']['progress_by_unit'].items():
            if uid not in units:
                known={i for (u,_),r in inventory(latest).items() if u==uid for i in r.get('output_ids',r.get('local_ids',[]))}
                projected[uid]['actual_output_ids']=sorted(set(projected[uid]['actual_output_ids'])|known)
                if known:projected[uid]['assessment_state']='needs_revalidation'
                continue
            rows=sorted((o for o in outputs if o['unit_id']==uid),key=lambda o:int(o['step']))
            need([int(o['step']) for o in rows]==list(range(1,int(p['work_completed_through'])+1)),'b_anchor_stage_sequence')
            projected[uid].update(work_completed_through=p['work_completed_through'],outputs=rows,actual_output_ids=sorted(set(projected[uid]['actual_output_ids'])|set(p.get('actual_output_ids',[]))|{i for o in rows for i in o['output_ids']}),
                assessment_state=p['assessment_state'],unresolved_keys=p['unresolved_keys'],next_tasks=p['next_tasks'])
        return CheckpointStageEvidence(digest(value),encode(projected),encode(value))

    def inputs(self,cfg,base,parent=None):
        if cfg['mode']=='adopt':
            need(parent is None and cfg['parent_metadata'] is None,'b_adopt_parent')
            stage=self.anchor(cfg['anchor'],base).payload() if cfg['anchor'] is not None else unassessed_progress(base)
            rows,guards=self.selector_seed(base)
        else:
            need(type(parent) is PublishedCheckpoint and parent.command_id==base.parent_command_id,'b_checked_parent_required')
            plan=self.published(parent.command_id).plan()
            need(parent==self.cache[parent.command_id] and cfg['parent_metadata']==plan['admission'],'b_exact_parent_metadata')
            need(cfg['anchor'] is None,'b_revalidate_parent_is_stage_chain')
            stage=deepcopy(plan['admission']['progress_by_unit']);rows=deepcopy(plan['admission']['selectors']);guards=deepcopy(plan['admission']['guards'])
        return stage,rows,guards

    def config(self,cfg,base,raw,parent=None):
        base=self.checked_view(base)
        b=self.history.budget;validate('Config',cfg,b);source=base.context.source
        need(type(base) is HistoryView and base.history is self.history,'b_config_view')
        need(cfg['store_id']==self.history.store_id and cfg['session_id']==base.session_id and cfg['parent_command_id']==base.parent_command_id,'b_config_identity')
        need([cfg['base_model_id'],cfg['base_analysis_set_id']]==base.pair and cfg['base_model_sha256']==digest(base.context.model()) and cfg['base_analysis_set_sha256']==digest(base.analysis_set),'b_config_pair')
        need(cfg['source_context_id']==source.context_id and cfg['snapshot_id']==source.snapshot_id and cfg['archive_sha256']==source.archive_sha256,'b_config_source')
        need(cfg['historical_reviews_pin']==self.history.registry.pin(),'b_config_registry')
        dependencies(cfg['history_binding'],base)
        stages,rows,guards=self.inputs(cfg,base,parent)
        source.selected(cfg['unit_ids'])
        need(cfg['mode']!='adopt' or set(cfg['unit_ids'])==set(source.units),'b_adopt_full_inventory')
        if cfg['goal']=='retained_output':
            for uid in cfg['unit_ids']:
                progress=stages[uid]
                need(int(progress['work_completed_through'])>=cfg['step'] and any(int(o['step'])==cfg['step'] for o in progress['outputs']),'b_retained_stage_proof_required')
        aliases={}
        if cfg['mode']=='revalidate':aliases=parent.plan()['allocation']['aliases']
        elif cfg['anchor'] is not None:aliases=aliases_for(cfg['anchor'],base)
        need(cfg['aliases']==aliases,'b_config_aliases')
        allowed={name:set(coll) for name,coll in base.context.maps.items()}
        kinds={'Actor':'actors','Action':'actions','Workflow':'workflows','Data':'data','Rule':'rules','Component':'components','Responsibility':'responsibilities','Interface':'interfaces','Dependency':'dependencies'}
        for a in aliases.values():
            typ=a['kind'];identity=a['id']
            if typ in kinds:need(identity in allowed[kinds[typ]],'b_alias_current_type')
            elif typ=='Part':need(identity in base.context.parts,'b_alias_current_part')
            elif typ=='Issue':need(identity in base.analysis_set['body']['issue_ids'],'b_alias_current_issue')
            else:
                group='nodes' if typ=='WorkflowNode' else 'edges';need(identity in {x['id'] for w in base.context.body['workflows'] for x in w[group]},'b_alias_current_workflow')
        expected=binding(base,provider_id=cfg['authority_binding']['provider_id'],mode=cfg['mode'],step=cfg['step'],units=cfg['unit_ids'],goal=cfg['goal'],aliases=aliases,
            rows=rows,progress=cfg['parent_metadata']['progress_by_unit'] if cfg['parent_metadata'] else None,anchor=cfg['anchor'],raw=raw)
        # binding() observes the current whole store. Only its dependency pin is
        # frozen at T0: extensions never rewrite the exact historical intent.
        expected['history_sha256']=digest(cfg['history_binding'])
        need(cfg['authority_binding']==expected,'b_config_authority_binding')
        need(cfg['intent_sha256']==digest(config_intent(cfg)),'b_config_intent')
        pin=cfg['inputs']['analysis'];need(pin['sha256']==__import__('hashlib').sha256(raw).hexdigest() and pin['byte_length']==len(raw) and pin['stage_ref']['command_id']==cfg['command_id'],'b_config_raw')
        analysis(raw,cfg,base)
        return stages,rows,guards

    def result(self,cfg,plan,base,result,parent=None):
        base=self.checked_view(base);result=self.checked_view(result)
        b=self.history.budget;s=self.history._state;validate('Plan',plan,b)
        need(result.history is self.history and base.history is self.history,'b_shared_result_graph')
        op=s['commands'][cfg['command_id']]
        raw=s['stages'][cfg['command_id'],cfg['inputs']['analysis']['stage_ref']['blob_id']]['bytes']
        stages,rows,guards=self.config(cfg,base,raw,parent)
        need(all(op[k]==cfg[k] for k in ('command_id','session_id','parent_command_id','reserved_run_id')) and op['request']['kind']=='work','b_operation_identity')
        need(op['request']==dict(kind='work',source_context_id=cfg['source_context_id'],base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],scope=None,config_artifact_id=None),'b_operation_request')
        need(result.pair[0]==base.pair[0] and result.context.model()==base.context.model(),'b_as_only_model')
        need(plan['batch']['head']==result.pair and plan['allocation']['aliases']==cfg['aliases'],'b_result_head_aliases')
        aset=result.analysis_set['body'];need(aset['parent_set_id']==base.pair[1] and aset['revision']==base.analysis_set['body']['revision']+1,'b_as_parent')
        old={q['body']['issue_key']:q for q in base.issues};cur={q['body']['issue_key']:q for q in result.issues}
        need(old.keys()==cur.keys(),'b_result_all_keys')
        need(list(old)==list(cur),'b_result_selection_order')
        changes=issue_changes(cfg,base,rows,guards,raw);introduced=[]
        for key,q in cur.items():
            if key not in changes:need(q==old[key],'b_unchanged_issue_bytes')
            else:
                need(q['id']!=old[key]['id'] and q['body']==changes[key],'b_guard_successor_exact');introduced.append(q['id'])
        need(aset['changed_record_ids']==introduced,'b_changed_issue_inventory')
        records=plan['batch']['records'];ids=[r['id'] for r in records]
        need(len(ids)==len(set(ids)) and all(s['records'].get(r['id'])==r for r in records),'b_planned_actual_bytes')
        need({r['id'] for r in records if r['type']=='issue'}==set(introduced) and [r['id'] for r in records if r['type']=='analysis_set']==[result.pair[1]],'b_exact_domain_inventory')
        need(all(r['type'] in ('artifact','run','issue','analysis_set') for r in records),'b_no_model_change')
        need(plan['admission']==admission(cfg,base,result,stages,rows,guards,raw),'b_result_assessment_exact')
        need(plan['candidate_outcome']==('adopted' if cfg['mode']=='adopt' else 'revalidated') and not plan['diagnostics'],'b_result_outcome')
        blocked=bool(plan['admission']['full_hold_reasons'] or any(p['unresolved_keys'] or p['assessment_state']!='current' for p in plan['admission']['progress_by_unit'].values()))
        runs=[r for r in records if r['type']=='run'];need(len(runs)==1 and runs[0]['id']==cfg['reserved_run_id'],'b_reserved_run')
        rb=runs[0]['body'];need(rb['status']==('blocked' if blocked else 'completed') and rb['result_model_id'] is None and rb['result_analysis_set_id']==result.pair[1] and not rb['attempts'] and not rb['errors'],'b_run_outcome')
        need(rb['command_id']==cfg['command_id'] and rb['source_context_id']==cfg['source_context_id'] and [rb['base_model_id'],rb['base_analysis_set_id']]==base.pair and rb['started_at']==cfg['started_at'],'b_run_pins')
        need(rb['steps']==([] if cfg['mode']=='adopt' else [cfg['step']]),'b_run_steps')
        need(rb['mode']=='replay' and rb['completed_at']==plan['allocation']['created_at'] and runs[0]['created_at']==cfg['started_at'],'b_run_times_mode')
        need(all(r['created_at']==plan['allocation']['created_at'] for r in records if r['type']!='run'),'b_allocation_record_times')
        self.envelope(cfg,plan)
        return deepcopy(plan)

    def envelope(self,cfg,plan):
        s=self.history._state;b=self.history.budget;cid=cfg['command_id'];events=sorted((e for (c,_),e in s['events'].items() if c==cid),key=lambda e:e['ordinal'])
        need(events and events[0]['kind']=='prepared','b_prepared_event')
        refs=events[0]['payload']['stage_refs'];primary=[x for x in refs if s['stages'][x['command_id'],x['blob_id']]['purpose']=='config']
        need(len(primary)==1,'b_primary_unique');pr=primary[0]
        need(s['stages'][pr['command_id'],pr['blob_id']]['bytes']==encode(cfg),'b_primary_bytes')
        expected=dict(command_id=cid,session_id=cfg['session_id'],parent_command_id=cfg['parent_command_id'],reserved_run_id=cfg['reserved_run_id'],
            primary_config_sha256=digest(cfg),primary_config_stage_ref=pr,intent_sha256=cfg['intent_sha256'],base_pair=[cfg['base_model_id'],cfg['base_analysis_set_id']],
            history_sha256=digest(cfg['history_binding']),anchor_sha256=digest(cfg['anchor']) if cfg['anchor'] is not None else None,
            authority_binding_sha256=digest(cfg['authority_binding']),historical_reviews_pin=cfg['historical_reviews_pin'],handler_version=cfg['handler_version'])
        need(plan['bindings']==expected,'b_plan_bindings')
        need(refs==[pr,cfg['inputs']['analysis']['stage_ref']],'b_exact_prepared_refs')
        sources=plan['batch']['artifact_sources'];need([p['stage_ref'] for p in sources]==refs and len({p['artifact_id'] for p in sources})==len(refs),'b_exact_raw_promotions')
        for p in sources:
            st=s['stages'][p['stage_ref']['command_id'],p['stage_ref']['blob_id']];a=s['records'][p['artifact_id']]
            need(a['type']=='artifact' and a['body']['producer_run_id']==cfg['reserved_run_id'] and a['body']['purpose']==st['purpose'] and
                 a['body']['sha256']==st['sha256'] and a['body']['byte_length']==st['byte_length'] and s['blobs'][a['id']]==st['bytes'],'b_artifact_raw_bytes')
        alloc=plan['allocation'];extra=dict(artifact_id=alloc['plan_artifact_id'],stage_ref=dict(command_id=cid,blob_id=alloc['plan_blob_id']))
        need(plan['promotions']==sources+[extra],'b_promotions')
        need(len({p['artifact_id'] for p in plan['promotions']})==len(plan['promotions']),'b_promotion_unique')
        aid=alloc['plan_artifact_id'];stage=s['stages'][cid,alloc['plan_blob_id']]
        need(stage['bytes']==encode(plan) and s['blobs'][aid]==stage['bytes'] and s['records'][aid]['body']['sha256']==digest(plan),'b_plan_promoted_bytes')
        need(s['records'][aid]['created_at']==alloc['created_at'] and s['records'][aid]['body']['producer_run_id']==cfg['reserved_run_id'],'b_plan_artifact_allocation')
        need(all(e['kind'] in ('prepared','log','finalized') and (e['kind']!='log' or e['payload']=={'message':'H3-B immutable work plan sealed'}) for e in events),'b_own_event_protocol')
        need(sum(e['kind']=='log' for e in events)==1 and sum(e['kind']=='finalized' for e in events)==1,'b_own_event_counts')
        need(events[-1]['kind']=='finalized' and events[-1]['payload']==dict(run_id=cfg['reserved_run_id'],promotions=plan['promotions']),'b_finalized_exact')
        own={bid for (c,bid) in s['stages'] if c==cid};need(own=={x['blob_id'] for x in refs}|{alloc['plan_blob_id']},'b_own_stage_inventory')
        need(s['records'][cfg['reserved_run_id']]['body']['config_artifact_id']==sources[0]['artifact_id'],'b_run_config_artifact')

    def published(self,command):
        need(command not in self.active,'b_publisher_anchor_cycle');self.history.budget.cap('depth',len(self.active)+1)
        self.active.add(command)
        try:return self._published(command)
        finally:self.active.remove(command)

    def _published(self,command):
        if command in self.cache:return self.cache[command]
        s=self.history._state;b=self.history.budget;todo=[];seen=set();cursor=command
        while cursor not in self.cache:
            b.check();b.cap('depth',len(todo)+1);need(cursor not in seen,'b_publisher_cycle');seen.add(cursor)
            need(cursor in s['commands'],'b_publisher_command');op=s['commands'][cursor];run=s['records'][op['reserved_run_id']]['body']
            need(run['status'] in ('completed','blocked'),'b_publisher_status')
            cfgraw=s['blobs'][run['config_artifact_id']];cfg=validate('Config',b.parse(cfgraw,kind='config',slot='b.config.'+cursor),b)
            finals=[e for (c,_),e in s['events'].items() if c==cursor and e['kind']=='finalized'];need(len(finals)==1,'b_publisher_finalized')
            aids=[p['artifact_id'] for p in finals[0]['payload']['promotions'] if p['artifact_id']!=run['config_artifact_id'] and s['records'][p['artifact_id']]['body']['purpose']=='config'];need(len(aids)==1,'b_publisher_plan')
            raw=s['blobs'][aids[0]];plan=validate('Plan',b.parse(raw,kind='plan',slot='b.plan.'+cursor),b)
            todo.append((cursor,cfgraw,raw,cfg,plan))
            if cfg['mode']=='adopt':break
            cursor=cfg['parent_command_id']
        for cid,cfgraw,raw,cfg,plan in reversed(todo):
            base=self.view([cfg['base_model_id'],cfg['base_analysis_set_id']],cfg['session_id']);result=self.view(plan['batch']['head'],cfg['session_id'])
            parent=self.cache.get(cfg['parent_command_id']) if cfg['mode']=='revalidate' else None
            self.result(cfg,plan,base,result,parent)
            self.cache[cid]=PublishedCheckpoint(cid,cfgraw,raw)
        return self.cache[command]


def check_checkpoint_result(config,plan,base_view,result_view,*,stage_evidence=None,checked_parent_plan=None):
    verifier=CheckpointVerifier(result_view.history)
    if config['mode']=='revalidate':
        parent=verifier.published(config['parent_command_id'])
        need(checked_parent_plan is None or checked_parent_plan==parent,'b_parent_capability')
    else:parent=None
    if stage_evidence is not None:
        expected=verifier.anchor(config['anchor'],base_view)
        need(stage_evidence==expected,'b_stage_capability')
    return verifier.result(config,plan,base_view,result_view,parent)
