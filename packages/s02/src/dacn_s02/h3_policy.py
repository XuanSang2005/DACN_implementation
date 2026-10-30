"""Pure H3 transitions/admission/retention; no records are allocated/published.

The caller supplies in-memory checked graphs or full proposed graphs. Canonical
validation runs unchanged; a pure result cannot authorize any storage effects.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from .codec_boundary import encode, decode
from .profiles import E1, blocking_statuses
from .validation import index_model, shape
from .h3_contracts import Contract, validate, BINDING, POLICY
from .h3_limits import need, digest
from .h3_history import HistoryView, project_current_refs
from .h2_contracts import HoldSelector
from .h2_policy import materialize
from .h2_graph import impact, semantic


@dataclass(frozen=True)
class SemanticTrustContext:
    provider_id: str
    provider_version: str
    expected_sha256: str


@dataclass(frozen=True)
class SemanticGrant:
    binding_sha256: str
    control_sha256: str
    provider_id: str
    decision: str


def authorize_bytes(raw,trust,binding,budget):
    """Pure exact tuple matcher. Only the external caller supplies trust.

    This is not an I/O adapter and never derives historical review decisions.
    """
    need(type(trust) is SemanticTrustContext,'semantic_external_context')
    budget.inspect(dict(provider_id=trust.provider_id,provider_version=trust.provider_version,control_sha256=trust.expected_sha256),input_lane=True,slot='h3.semantic_trust')
    need(type(binding) is Contract and binding.kind=='Binding','typed_h3_binding')
    v=validate('Binding',binding.payload(),budget)
    need(type(raw) is bytes and sha256(raw).hexdigest()==trust.expected_sha256,'semantic_control_hash')
    data=Contract.parse('Authority',raw,budget).payload()
    need(data['provider_id']==trust.provider_id==v['provider_id'] and
         data['provider_version']==trust.provider_version==v['provider_version'],'semantic_provider_binding')
    rows=[a for a in data['approvals'] if encode(a['binding'])==encode(v)]
    return SemanticGrant(digest(v),trust.expected_sha256,trust.provider_id,rows[0]['decision'] if len(rows)==1 else 'deny')


def _view(view):
    need(type(view) is HistoryView,'typed_history_view')
    r=view.history._state['records']
    need(view.pair==[view.context.id,view.analysis_set['id']] and
         view.context.model()==r[view.pair[0]] and view.analysis_set==r[view.pair[1]],'view_immutable_pair')
    need(view.issues==[r[i] for i in view.analysis_set['body']['issue_ids']],'view_current_selection')
    view.history.budget.check()


def transition(before,after,*,step=0,unit_ids=()):
    """Verify/project a proposed transition already represented as a full graph.

    Missing coverage is legal only in canonical undetermined/incomplete records;
    invalid applicable/complete claims are rejected by HistoryData, not repaired.
    Caller-owned record construction/publication is outside H3-A.
    """
    _view(before);_view(after);budget=before.history.budget
    need(after.history.budget is budget,'shared_transition_budget')
    need(before.session_id==after.session_id and before.history.store_id==after.history.store_id,'transition_session_store')
    need(before.history.registry.pin()==after.history.registry.pin(),'transition_registry_fixed')
    old=before.history._state;new=after.history._state
    for kind in ('records','record_profiles','owners','commands','operation_profiles','events','stages','blobs'):
        budget.check();need(all(k in new[kind] and new[kind][k]==v for k,v in old[kind].items()),'immutable_history_'+kind)
    added=set(new['records'])-set(old['records'])
    need(all(new['records'][i]['type'] in ('artifact','run','model','change','analysis_set','issue') for i in added),'transition_record_scope')
    need(not any(e['kind'] in ('application_applied','consent_recorded','interpretation_selected','s01_dispatch_intent','s01_result_observed')
        for k,e in new['events'].items() if k not in old['events']),'transition_no_answer_application')
    a=before.context;b=after.context
    need(a.source.context_id==b.source.context_id and a.source.snapshot_id==b.source.snapshot_id and
         a.source.archive_sha256==b.source.archive_sha256,'source_switch_out_of_scope')
    changed_model=a.id!=b.id
    if changed_model:
        need(b.body['parent_model_id']==a.id and b.body['revision']==a.body['revision']+1 and
             after.analysis_set['body']['revision']==1 and after.analysis_set['body']['parent_set_id'] is None,'transition_model_parent')
        change=new['records'][b.body['change_id']]['body']
        need(change['kind']=='analysis_edit' and not change['application_event_refs'],'transition_analysis_edit_only')
        need(type(step) is int and step in (2,3,4),'transition_step')
    else:
        need(after.analysis_set['body']['parent_set_id']==before.pair[1],'transition_set_parent')
    prev={q['body']['issue_key']:q for q in before.issues};cur={q['body']['issue_key']:q for q in after.issues}
    need(prev.keys()<=cur.keys(),'transition_all_keys')
    remap={q['id']:cur[k]['id'] for k,q in prev.items()}
    summaries=[]
    for key,q in cur.items():
        budget.check();body=q['body'];proof=body['resolution_carry'] or body['resolution_replacement']
        oldq=prev.get(key)
        if oldq is not None:
            need(q['id']==oldq['id'] or body['supersedes_id']==oldq['id'],'transition_current_predecessor')
        if q['id'] in added:
            if oldq is None:
                need(proof is None and body['status']=='open' and not body['answer_ids'] and not body['resolution_event_refs'] and body['resolution'] is None,'new_direct_findings_open_only')
            if proof is not None:
                need(proof['evaluation']['method']=='structural_check','no_new_human_decision')
                if body['resolution_replacement']:
                    targetkey=new['records'][proof['replacement_issue_id']]['body']['issue_key']
                    need(targetkey in prev,'no_new_replacement_target_key')
            if oldq and not proof:
                need(body['answer_ids']==oldq['body']['answer_ids'] and
                     body['resolution_event_refs']==oldq['body']['resolution_event_refs'],'direct_root_evidence_preserved')
                need(body['status']==oldq['body']['status'] and body['resolution']==oldq['body']['resolution'],'direct_no_implicit_resolution')
                expected=project_current_refs(oldq,b.id,remap,budget);expected['supersedes_id']=oldq['id']
                if body['status']=='resolved':need(body==expected,'source_only_resolution_meaning')
                else:
                    meaning=lambda x:{k:v for k,v in x.items() if k not in ('affected','blocking')}
                    need(meaning(body)==meaning(expected),'direct_pending_meaning')
                    for field in ('affected','blocking'):
                        need(set(expected[field]['element_ids'])<=set(body[field]['element_ids']) and
                             set(expected[field]['mapping_part_ids'])<=set(body[field]['mapping_part_ids']),'direct_pending_no_shrink')
        summaries.append(after.projection(key))
    if changed_model:
        _append_only(before,after,remap,step,unit_ids)
    return tuple(summaries)


def _append_only(before,after,remap,step,units):
    base=before.context;candidate=after.context;budget=before.history.budget
    selected=base.source.selected(units)
    projected=project_current_refs(base.model(),candidate.id,remap,budget)
    allowed={2:('actors','actions','workflows','data','rules'),3:('components','responsibilities'),4:()}[step]
    for group,rows in base.maps.items():
        new=candidate.maps[group];old={v['id']:v for v in projected[group]}
        need(rows.keys()<=new.keys(),'retained_elements_missing')
        need(all(semantic(old[i])==semantic(new[i]) for i in old),'completed_output_edit')
        need(group in allowed or rows.keys()==new.keys(),'step_write_group')
        for i in new.keys()-old.keys():
            refs=candidate.sources_in(new[i]);need(bool(refs) and refs<=selected,'new_output_write_sources')
    need(base.rows.keys()==candidate.rows.keys(),'retained_rows_inventory')
    oldrows={r['id']:r for r in projected['mappings']}
    for rid,r in oldrows.items():
        n=candidate.rows[rid]
        need(r['source_ref']==n['source_ref'],'retained_row_source')
        if semantic(r)!=semantic(n):
            need(step==4 and not r['parts'] and r['assessment']=='not_assessed' and
                 r['source_ref']['input_pointer'] in selected,'completed_row_context_edit')
    need(base.parts.keys()<=candidate.parts.keys(),'retained_parts_missing')


def selectors(view,rows,task_origins=(),guard_origins=()):
    _view(view);ctx=view.context;budget=view.history.budget
    need(type(rows) is list and len(rows)==len(view.issues),'selector_inventory')
    from .h3_bindings import verify_task_origin,verify_guard_origin
    guards={o['issue_key']:verify_guard_origin(o,view) for o in guard_origins}
    need(len(guards)==len(guard_origins),'guard_origin_unique')
    origins={o['issue_key']:verify_task_origin(o,view) for o in task_origins}
    need(len(origins)==len(task_origins),'task_origin_unique')
    result={}
    for row in rows:
        v=validate('Selector',row,budget,input_lane=True,slot='h3.selector.'+str(row.get('issue_id')))
        need(v['issue_id'] not in result,'selector_duplicate_issue')
        q=next((q for q in view.issues if q['id']==v['issue_id']),None)
        need(q is not None and q['body']['issue_key']==v['issue_key'],'selector_current_issue')
        if v['code_task_role']=='merge_guard':
            need(v['issue_key'] in guards and int(v['target_step'])==1,'hold_guard_origin_required')
        elif int(v['target_step'])!=1 or v['code_task_role'] is not None:
            origin=origins.get(v['issue_key'])
            need(origin is not None and origin['target_step']==v['target_step'] and origin['role']==v['code_task_role'],'hold_target_requires_task_origin')
        refs=ctx.source.refs(v['source_refs']);es=frozenset(v['element_ids']);ps=frozenset(v['mapping_part_ids'])
        need(es<=ctx.elements.keys() and ps<=ctx.parts.keys(),'selector_current_scope')
        need(set(q['body']['blocking']['element_ids'])<=es and set(q['body']['blocking']['mapping_part_ids'])<=ps,'selector_no_shrink')
        trace=ctx.source.refs(q['body']['trace']['source_refs'])
        need(v['kind']=='all_source_uses' or trace<=refs,'selector_source_coverage')
        need(v['impact_known'] or v['kind']=='all_source_uses','unknown_global_selector')
        if v['kind']=='obligation_families':need(bool(refs) and refs<=ctx.source.obligations,'selector_source_families')
        result[q['id']]=HoldSelector(q['id'],v['issue_key'],int(v['target_step']),v['kind'],refs,es,ps,v['impact_known'],v['code_task_role'])
    return result


@dataclass(frozen=True)
class AdmissionResult:
    allowed_units: tuple
    blocked_units: tuple
    global_blocked: bool
    unit_reasons: tuple
    reason_codes: tuple
    materialized_holds: tuple
    eligibility_authorized_in_process: bool = False  # Pure result, no storage permission.


def admit(view,selector_rows,binding,analysis,grant,trust,*,candidate_raw=None,progress=None,task_origins=(),guard_origins=()):
    _view(view);ctx=view.context;source=ctx.source;budget=view.history.budget
    need(type(binding) is Contract and binding.kind=='Binding','typed_h3_binding')
    need(type(analysis) is Contract and analysis.kind=='Analysis','typed_h3_analysis')
    b=validate('Binding',binding.payload(),budget);e=validate('Analysis',analysis.payload(),budget)
    holds=selectors(view,selector_rows,task_origins,guard_origins);units=source.selected(b['unit_ids']);selected=set(b['unit_ids'])
    budget.raw_work(candidate_raw,analysis.raw)
    expected=dict(store_id=view.history.store_id,session_id=view.session_id,parent_command_id=view.parent_command_id,
        source_context_id=source.context_id,snapshot_id=source.snapshot_id,archive_sha256=source.archive_sha256,
        base_pair=view.pair,base_model_sha256=ctx.hash,base_analysis_set_sha256=digest(view.analysis_set),
        current_selectors_sha256=digest(sorted(selector_rows,key=lambda x:x['issue_key'])),
        history_sha256=digest(view.history.binding(view)),historical_reviews_pin=view.history.registry.pin(),
        analysis_sha256=sha256(analysis.raw).hexdigest(),analysis_length=len(analysis.raw),
        candidate_sha256=sha256(candidate_raw).hexdigest() if candidate_raw is not None else None,candidate_length=len(candidate_raw or b''))
    from .h3_bindings import _checked_progress
    progress_rows=_checked_progress(view,progress) if progress is not None else None
    unproved=unassessed_progress(view) if progress is None else None
    reasons={u:set() for u in selected}
    def all_reason(reason):
        for rr in reasons.values():rr.add(reason)
    expected['progress_before_sha256']=digest(progress_rows) if progress_rows is not None else None
    expected['anchor_sha256']=progress.anchor_sha256 if progress is not None else None
    expected['retained_assessment_hashes']=sorted({digest(p['assessment']) for p in (progress_rows or {}).values() if p['assessment'] is not None})
    if any(b[k]!=v for k,v in expected.items()):all_reason('BINDING_STALE')
    if not (e['base_pair']==view.pair and e['snapshot_id']==source.snapshot_id and e['source_context_id']==source.context_id and
            e['selectors_sha256']==b['current_selectors_sha256'] and set(e['unit_ids'])==selected):all_reason('ANALYSIS_STALE')
    if (type(grant) is not SemanticGrant or type(trust) is not SemanticTrustContext or
        grant.binding_sha256!=digest(b) or grant.control_sha256!=trust.expected_sha256 or
        grant.provider_id!=trust.provider_id or trust.provider_id!=b['provider_id'] or trust.provider_version!=b['provider_version'] or grant.decision!='allow'):
        all_reason('SEMANTIC_AUTHORITY_REQUIRED')
    inspections={}
    for row in e['inspections']:
        budget.check();ptr=source.source(row['source_ref'],obligation=True)
        need(ptr not in inspections,'inspection_duplicate');basis=source.refs(row['basis_source_refs'])
        need(row['verdict']=='held' or row['read']=='inspected' and ptr in basis and not row['needed_facts'],'inspection_basis')
        inspections[ptr]=row
    need(set(inspections)==source.obligations,'inspection_all_obligations')
    pairs={}
    for row in e['independence']:
        need(row['issue_key'] in {q['body']['issue_key'] for q in view.issues} and row['unit_id'] in source.units,'independence_current_refs')
        key=row['issue_key'],row['unit_id'];need(key not in pairs,'independence_duplicate');source.refs(row['basis_source_refs']);pairs[key]=row
    heldrefs={p for p,row in inspections.items() if row['read']!='inspected' or row['verdict']=='held'}
    active=[q for q in view.issues if q['body']['status'] in blocking_statuses(E1)]
    covered=set();materialized=[]
    for q in view.issues:
        s=holds[q['id']];foot=materialize(ctx,s,q);materialized.append((q['body']['issue_key'],foot))
        if q in active:
            covered.update(source.obligations if not s.impact_known or s.kind=='all_source_uses' else
                {p for f in source.families if f.obligations&s.sources for p in f.obligations})
    if heldrefs-covered:all_reason('SOURCE_HOLD_MISSING')
    for u in sorted(selected):
        budget.check();refs=source.units[u].obligations;foot=ctx.closure(*ctx.source_seed(refs));rr=reasons[u]
        if heldrefs&refs:rr.add('OBLIGATION_HELD')
        if any(r['read']!='inspected' for r in inspections.values()):rr.add('INVENTORY_UNINSPECTED')
        rr.update(x for x in foot.reasons if x!='ACTION_WITHOUT_PART' or int(b['step'])==4)
        if any(ctx.elements[a]['initiator']=='unknown' for a in foot.actions):rr.add('INITIATOR_UNKNOWN')
        if any(ctx.parts[p]['assignment']!='proposed' or ctx.parts[p]['remaining_gap'] is not None for p in foot.parts):rr.add('PART_GAP')
        if progress_rows is not None and b['operation']=='step':
            need(u in progress_rows,'progress_unit_inventory');p=validate('Progress',progress_rows[u],budget)
            if int(p['work_completed_through'])!=int(b['step'])-1 or p['assessment_state'] in ('needs_revalidation','terminal_out_of_scope'):rr.add('PROGRESS_NOT_CURRENT')
        elif b['operation']=='step' and progress_rows is None and (int(b['step'])>1 or unproved[u]['actual_output_ids']):rr.add('PROGRESS_PROOF_REQUIRED')
        for q in active:
            s=holds[q['id']]
            origins=[o for o in task_origins if o['issue_id']==q['id']]
            exempt=bool(origins and (selected<=set(origins[0]['unit_ids']) or
                origins[0]['role']=='await_builder' and set(origins[0]['unit_ids'])<=selected) and int(b['step'])<=int(origins[0]['target_step']))
            if int(b['step'])<s.target_step or exempt:continue
            if not s.impact_known or s.kind=='all_source_uses':rr.add('UNKNOWN_GLOBAL_HOLD');continue
            held=materialize(ctx,s,q)
            familyrefs={p for f in source.families if f.obligations&s.sources for p in f.obligations}
            if (refs&familyrefs or foot.source_uses&familyrefs or foot.elements&s.elements or foot.parts&s.parts or
                foot.uses&held.uses or foot.active_parts&held.active_parts):rr.add('BLOCKING_USE');continue
            pair=pairs.get((s.issue_key,u))
            if pair is None or pair['verdict']!='independent' or not (refs|s.sources)<=source.refs(pair['basis_source_refs']):rr.add('INDEPENDENCE_NOT_PROVED')
    allowed=tuple(sorted(u for u,rr in reasons.items() if not rr));blocked=tuple(sorted(selected-set(allowed)))
    return AdmissionResult(allowed,blocked,bool(active or heldrefs or blocked),
        tuple((u,tuple(sorted(reasons[u]))) for u in sorted(selected)),tuple(sorted(set().union(*reasons.values()))),tuple(materialized))


def retained_output(before,after,unit_id):
    """Compare full Part-row-source context/impact without inventing progress."""
    _view(before);_view(after);a=before.context;b=after.context
    need(a.budget is b.budget,'shared_retention_budget')
    delta=impact(a,b);refs=a.source.units[unit_id].obligations
    foot=a.closure(*a.source_seed(refs));now=b.closure(*b.source_seed(refs))
    remap={q['id']:after.issue(q['body']['issue_key'])['id'] for q in before.issues}
    projected=project_current_refs(a.model(),b.id,remap,a.budget)
    olde={e['id']:e for group in a.maps for e in projected[group]}
    oldrows={r['id']:r for r in projected['mappings']}
    equal=(not delta.source_changed and all(i in b.elements and semantic(olde[i])==semantic(b.elements[i]) for i in foot.elements) and
        all(p in b.parts and semantic(next(row for row in oldrows.values() if any(v['id']==p for v in row['parts'])))==semantic(b.part_rows[p]) for p in foot.parts))
    impacted=bool(delta.before.uses&foot.uses or delta.before.active_parts&foot.active_parts or
                  delta.after.uses&now.uses or delta.after.active_parts&now.active_parts)
    known=not set(foot.reasons+now.reasons)-{'ACTION_WITHOUT_PART'}
    return dict(unit_id=unit_id,output_ids=sorted(foot.elements|foot.parts),
        state='current' if equal and known and not impacted else 'needs_revalidation',
        from_pair=list(before.pair),result_pair=list(after.pair),diff_sha256=digest(dict(
            elements=sorted(delta.changed_elements),parts=sorted(delta.changed_parts),rows=sorted(delta.changed_rows))),
        work_completed_through=None)  # Deliberately no stage inferred from Model.


def unassessed_progress(view):
    """No-anchor adoption projection. Existing outputs never become overwriteable."""
    _view(view);ctx=view.context;out={}
    for uid,family in ctx.source.units.items():
        ctx.budget.check();foot=ctx.closure(*ctx.source_seed(family.obligations))
        actual=sorted(foot.elements|foot.parts)
        out[uid]=dict(work_completed_through=0,outputs=[],actual_output_ids=actual,
            assessment_state='needs_revalidation' if actual else 'pending',unresolved_keys=[],next_tasks=[1],
            latest_checked_pair=None,assessment=None)
        validate('Progress',out[uid],ctx.budget)
    return out


def materialize_hold(context,selector_row,issue):
    """Pure local context control; whole A2 history validity is a separate check.

    Useful before Parts/with an empty domain graph. Never reclassifies an Issue's
    status, truncates an action set, or establishes historical resolution proof.
    """
    b=context.budget;v=validate('Selector',selector_row,b);shape(issue,profile=E1)
    need(v['issue_id']==issue['id'] and v['issue_key']==issue['body']['issue_key'] and
         issue['body']['model_id']==context.id,'hold_issue_binding')
    for name in ('affected','blocking'):
        scope=issue['body'][name]
        need(scope['model_id']==context.id and set(scope['element_ids'])<=context.elements.keys() and
             set(scope['mapping_part_ids'])<=context.parts.keys(),'hold_current_scope')
    need(set(issue['body']['blocking']['element_ids'])<=set(issue['body']['affected']['element_ids']) and set(issue['body']['blocking']['mapping_part_ids'])<=set(issue['body']['affected']['mapping_part_ids']),'hold_blocking_subset')
    sources=context.source.refs(v['source_refs'])
    need(v['kind']=='all_source_uses' or context.source.refs(issue['body']['trace']['source_refs'])<=sources,'hold_source_coverage')
    s=HoldSelector(v['issue_id'],v['issue_key'],int(v['target_step']),v['kind'],sources,
        frozenset(v['element_ids']),frozenset(v['mapping_part_ids']),v['impact_known'],v['code_task_role'])
    need(s.elements<=context.elements.keys() and s.parts<=context.parts.keys(),'hold_selector_members')
    return materialize(context,s,issue)
