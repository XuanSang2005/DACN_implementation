"""Pure C admission/union and result assessments. No permission is inferred here."""
from copy import deepcopy
from .h1_builders import part_has_gap
from .profiles import E1,blocking_statuses
from .h2_graph import ModelContext,impact,semantic
from .h2_policy import materialize
from .h3_checkpoint_checks import workflow_members,task_inventory
from .h3_history import project_current_refs
from .h3_limits import need,digest
from .h3_continuation_contracts import ADMISSION,POLICY,validate
from .h3_continuation_inputs import inspections,refs
from .h3_continuation_builders import GuardNeeded,effective_selectors,hold_selector


def family_refs(source,selector):
    if not selector.impact_known or selector.kind=='all_source_uses':return set(source.obligations)
    return {p for f in source.families if f.obligations&selector.sources for p in f.obligations} if selector.kind=='obligation_families' else set(selector.sources)


def touches(ctx,q,row,unit):
    s=hold_selector(row,ctx.source,q['id']);foot=ctx.closure(*ctx.source_seed(ctx.source.units[unit].obligations));hold=materialize(ctx,s,q)
    source=family_refs(ctx.source,s)
    # Context-only shared component/responsibility membership is not an action
    # bridge. Both footprints still expand every discovered Part to all actions.
    return not s.impact_known or s.kind=='all_source_uses' or bool(ctx.source.units[unit].obligations&source or foot.source_uses&source or
        foot.uses&hold.uses or foot.active_parts&hold.active_parts or foot.uses&s.elements or foot.active_parts&s.parts)


def task_exempt(task,cfg):
    selected=set(cfg['unit_ids']);units=set(task['unit_ids'])
    return int(cfg['step'])<=int(task['target_step']) and (selected<=units or task['role']=='await_builder' and units<=selected)


def check_union(base,cfg,model,findings,newrows,raw,candidate):
    source=base.context.source;rows=effective_selectors(base,cfg['parent_metadata']);seen,pairs=inspections(raw,cfg,base);reasons=set();step=int(cfg['step'])
    tasks=task_inventory(base);after=ModelContext(model,source,base.history.budget)
    # A semantic grant/usable analysis cannot erase the candidate's own negative
    # inventory. Compatible holds still use the scoped, whole-union checks below;
    # contradictory or unread raw stays discarded under a guard on the base.
    raw_held={r['source_ref']['input_pointer'] for r in candidate['inspection'] if r['verdict']=='held'}|source.refs(candidate['unrepresented_source_refs'])
    if any(r['read']!='inspected' for r in candidate['inspection']):reasons.add('CANDIDATE_INVENTORY_UNINSPECTED')
    if any(seen[p]['verdict']!='held' for p in raw_held):reasons.add('CANDIDATE_SOURCE_HOLD_MISSING')
    for uid in cfg['unit_ids']:
        p=cfg['parent_metadata']['progress_by_unit'][uid]
        if int(p['work_completed_through'])!=step-1:reasons.add('PROGRESS_PREREQUISITE_OR_ALREADY_COMPLETED')
        if p['assessment_state'] in ('needs_revalidation','terminal_out_of_scope'):reasons.add('PROGRESS_NOT_CURRENT')
        if not p['work_completed_through'] and p['actual_output_ids']:reasons.add('REQUIRES_PROGRESS_PROOF_OR_DOMAIN_EDIT')
        if step>1 and any(seen[x]['verdict']=='held' or seen[x]['read']!='inspected' for x in source.units[uid].obligations):reasons.add('OBLIGATION_HELD')
    if any(r['read']!='inspected' for r in seen.values()):reasons.add('INVENTORY_UNINSPECTED')
    covered=set()
    for q in base.issues:
        key=q['body']['issue_key'];row=rows[key];sel=hold_selector(row,source)
        if q['body']['status'] not in blocking_statuses(E1):continue
        covered.update(family_refs(source,sel))
        if step<sel.target_step or key in tasks and task_exempt(tasks[key],cfg):continue
        for uid in cfg['unit_ids']:
            p=pairs.get((key,uid));full=(source.units[uid].obligations|sel.sources)
            if not p or p['verdict']!='independent' or not full<=source.refs(p['basis_source_refs']):reasons.add('INDEPENDENCE_NOT_PROVED')
            if touches(base.context,q,row,uid) or touches(after,q,row,uid):reasons.add('BLOCKING_UNION_USE')
    for q in findings:
        row=newrows[q['body']['issue_key']];covered.update(family_refs(source,hold_selector(row,source)))
        if step>1:
            for uid in cfg['unit_ids']:
                if touches(after,q,row,uid):reasons.add('NEW_FINDING_BLOCKS_UNION')
    held={p for p,r in seen.items() if r['verdict']=='held' or r['read']!='inspected'}
    if held-covered:reasons.add('SOURCE_HOLD_MISSING')
    # Assess all retained unselected output uses on both sides of the full
    # candidate, not just the raw candidate's declared write roots.
    delta=impact(base.context,after)
    for uid,p in cfg['parent_metadata']['progress_by_unit'].items():
        if uid in cfg['unit_ids'] or not p['actual_output_ids']:continue
        old=base.context.closure(*base.context.source_seed(source.units[uid].obligations));new=after.closure(*after.source_seed(source.units[uid].obligations))
        if delta.before.uses&old.uses or delta.before.active_parts&old.active_parts or delta.after.uses&new.uses or delta.after.active_parts&new.active_parts:reasons.add('RETAINED_OUTPUT_IMPACT')
    selected=after.closure(*after.source_seed(source.selected(cfg['unit_ids'])))
    reasons.update(r for r in selected.reasons if r!='ACTION_WITHOUT_PART' or step==4)
    if any(after.elements[i]['initiator']=='unknown' for i in selected.actions):reasons.add('INITIATOR_UNKNOWN')
    if step==4 and any(part_has_gap(after.parts[p]) for p in selected.parts):reasons.add('PART_GAP')
    if reasons:raise GuardNeeded(*reasons)
    return rows


def guard_can_resolve(base,cfg,raw,guards):
    if cfg['mode']!='revalidate':return False
    rows=effective_selectors(base,cfg['parent_metadata']);seen,pairs=inspections(raw,cfg,base);source=base.context.source;held=set()
    for q in base.issues:
        k=q['body']['issue_key']
        if k not in guards and q['body']['status'] in blocking_statuses(E1) and k not in cfg['parent_metadata']['tasks']:
            held.update(family_refs(source,hold_selector(rows[k],source)))
    if any(r['read']!='inspected' or r['verdict']=='held' and p not in held for p,r in seen.items()):return False
    if any(r!='ACTION_WITHOUT_PART' for r in base.context.closure(*base.context.source_seed(source.obligations)).reasons):return False
    for key in guards:
        for uid,f in source.units.items():
            p=pairs.get((key,uid));verdict='held' if f.obligations&held else 'independent'
            if not p or p['verdict']!=verdict or not source.obligations<=source.refs(p['basis_source_refs']):return False
    return True


def admission(cfg,base,result,rows,guards,raw,projection,*,new_outputs=None,remap=None):
    b=base.history.budget;ctx=result.context;source=ctx.source;seen,pairs=inspections(raw,cfg,base)
    prior=cfg['parent_metadata'];progress=deepcopy(prior['progress_by_unit']);current={q['body']['issue_key']:q for q in result.issues};old={q['body']['issue_key']:q for q in base.issues}
    rows=deepcopy(rows);guards=deepcopy(guards);remap=remap or {};tasks=deepcopy(prior['tasks'])
    for k,q in current.items():
        rows[k]['issue_id']=q['id'];rows[k]['element_ids']=sorted(q['body']['blocking']['element_ids']);rows[k]['mapping_part_ids']=sorted(q['body']['blocking']['mapping_part_ids'])
        if k in guards:guards[k]['issue_id']=q['id']
        if k in tasks:tasks[k]['issue_id']=q['id']
    roles=[];transitions=[]
    for k,q in current.items():
        p=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        roles.append(dict(issue_key=k,predecessor_issue_id=q['body']['supersedes_id'],current_issue_id=q['id'],origin_issue_id=p['origin_issue_id'] if p else None,obsolete_issue_id=p.get('obsolete_issue_id') if p else None,replacement_issue_id=p.get('replacement_issue_id') if p else None))
        if k not in old or old[k]['id']!=q['id']:
            transitions.append(dict(issue_key=k,branch='CARRY' if q['body']['resolution_carry'] else 'REPLACEMENT' if p else 'DIRECT',assessment=p['assessment'] if p else None,proof_record_id=q['id'],proof_sha256=digest(q),reason_codes=[]))
    roles.sort(key=lambda r:r['issue_key']);transitions.sort(key=lambda r:r['issue_key'])
    held={p for p,r in seen.items() if r['read']!='inspected' or r['verdict']=='held'};unresolved={u:[] for u in source.units};covered=set();full=set();unit_reasons={u:set() for u in source.units}
    for q in result.issues:
        if q['body']['status'] not in blocking_statuses(E1):continue
        key=q['body']['issue_key'];row=rows[key];sel=hold_selector(row,source)
        covered.update(family_refs(source,sel))
        if max(1,int(cfg['step']))<sel.target_step:continue
        for uid,f in source.units.items():
            p=pairs.get((key,uid));independent=bool(p and p['verdict']=='independent' and (f.obligations|sel.sources)<=source.refs(p['basis_source_refs']))
            if touches(ctx,q,row,uid) or not independent:unresolved[uid].append(key)
    if held-covered:full.add('SOURCE_HOLD_MISSING')
    if any(r['read']!='inspected' for r in seen.values()):full.add('INVENTORY_UNINSPECTED')
    for uid,p in progress.items():
        for output in p['outputs']:
            output['output_ids']=[remap.get(i,i) for i in output['output_ids']]
            for a in output['aliases'].values():a['id']=remap.get(a['id'],a['id'])
        p['actual_output_ids']=[remap.get(i,i) for i in p['actual_output_ids']]
        if new_outputs and uid in new_outputs:
            need(int(p['work_completed_through'])==int(cfg['step'])-1,'c_stage_advance_exact')
            p['work_completed_through']=int(cfg['step']);p['outputs'].append(deepcopy(new_outputs[uid]))
        actual=ctx.closure(*ctx.source_seed(source.units[uid].obligations));p['actual_output_ids']=sorted(set(p['actual_output_ids'])|actual.elements|actual.parts|{i for out in p['outputs'] for i in out['output_ids']})
        p['actual_output_ids']=sorted(set(p['actual_output_ids'])|{m['id'] for w in ctx.body['workflows'] if w['id'] in actual.elements for g in ('nodes','edges') for m in w[g]})
        p['unresolved_keys']=sorted(unresolved[uid]);unit_reasons[uid].update(r for r in actual.reasons if r!='ACTION_WITHOUT_PART' or int(cfg['step'])==4)
        if not p['work_completed_through'] and p['actual_output_ids']:state='needs_revalidation';unit_reasons[uid].add('PROGRESS_PROOF_REQUIRED')
        elif any(k in guards for k in p['unresolved_keys']):state='needs_revalidation'
        elif p['unresolved_keys'] or held&source.units[uid].obligations or full or unit_reasons[uid]:state='assessed_held'
        else:state='current'
        p.update(assessment_state=state,latest_checked_pair=result.pair,next_tasks=[] if int(p['work_completed_through'])==4 else [int(p['work_completed_through'])+1])
    full.update(r for reasons in unit_reasons.values() for r in reasons)
    meta=dict(marker=ADMISSION,policy_version=POLICY,from_pair=base.pair,result_pair=result.pair,
        obligations=[dict(source_ref=r['source_ref'],mapping_row_id=r['id'],assessment=r['assessment'],mapping_part_ids=[p['id'] for p in r['parts']],issue_ids=r['issue_ids']) for r in ctx.body['mappings']],
        selectors=rows,tasks=tasks,guards=guards,progress_by_unit=progress,retained_assessments=[],issue_roles=roles,transitions=transitions,full_hold_reasons=sorted(full))
    delta=impact(base.context,ctx);proof=digest(dict(history_sha256=digest(cfg['history_binding']),analysis_sha256=cfg['inputs']['analysis']['sha256'],authority_binding_sha256=digest(cfg['authority_binding']),historical_reviews_pin=cfg['historical_reviews_pin'],anchor_sha256=None,
        issue_roles=roles,transitions=transitions,full_hold_reasons=meta['full_hold_reasons'],stage_inventory={u:{k:p[k] for k in ('work_completed_through','outputs','actual_output_ids')} for u,p in sorted(progress.items())},
        candidate_projection_sha256=digest(projection) if projection is not None else None,candidate_sha256=cfg['inputs']['candidate']['sha256'] if cfg['inputs']['candidate'] else None))
    for uid,p in progress.items():
        p['assessment']=dict(from_pair=base.pair,result_pair=result.pair,parent_assessment_sha256=digest(prior['progress_by_unit'][uid]['assessment']),
            source_sha256=digest(dict(source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,obligations=refs(source,source.obligations))),
            diff_sha256=digest(dict(elements=sorted(delta.changed_elements),parts=sorted(delta.changed_parts),rows=sorted(delta.changed_rows),source_changed=delta.source_changed)),context_sha256=digest(ctx.model()),closure_sha256=digest(dict(before=delta.before.scope(),after=delta.after.scope())),proof_sha256=proof,
            result_model_sha256=digest(ctx.model()),result_analysis_set_sha256=digest(result.analysis_set),output_refs=deepcopy(p['outputs']),state=p['assessment_state'])
        validate('Progress',p,b)
    retained={digest(p['assessment']):p['assessment'] for _,p in sorted(progress.items())};meta['retained_assessments']=list(retained.values())
    return validate('Admission',meta,b)
