"""Pure private-envelope correspondence checks over detached HistoryData views.

These functions do not prepare/seal/finalize work or load a registry. A future
writer must repeat checked reads, external trust checks and paired CAS itself.
"""
from copy import deepcopy
from dataclasses import dataclass
from .codec_boundary import encode,decode
from .h3_contracts import validate, CONFIG, PLAN, ADMISSION, POLICY
from .h3_limits import need,digest
from .h3_history import HistoryView
from .validation import shape, index_model
from .profiles import E1


def _same_source(v,view):
    c=view.context.source
    need(v['source_context_id']==c.context_id and v['snapshot_id']==c.snapshot_id,'private_source_pin')


def config_intent(config):
    """Exclude only speculative T0 allocations; committed config bytes stay exact."""
    v=deepcopy(config)
    for k in ('reserved_run_id','started_at','intent_sha256'):v.pop(k)
    for pin in v['inputs'].values():
        if pin is not None:pin.pop('stage_ref')
    return v


def check_config(value,view):
    need(type(view) is HistoryView,'typed_history_view')
    b=view.history.budget;v=validate('Config',value,b)
    _same_source(v,view)
    need(v['store_id']==view.history.store_id and v['session_id']==view.session_id and
         v['parent_command_id']==view.parent_command_id,'config_identity')
    need([v['base_model_id'],v['base_analysis_set_id']]==view.pair and
         v['base_model_sha256']==digest(view.context.model()) and v['base_analysis_set_sha256']==digest(view.analysis_set),'config_base_pair')
    need(v['archive_sha256']==view.context.source.archive_sha256,'config_archive')
    need(v['historical_reviews_pin']==view.history.registry.pin(),'config_review_pin')
    need(v['history_binding']==view.history.binding(view),'config_whole_history_binding')
    if v['mode']=='adopt':need(set(v['unit_ids'])==set(view.context.source.units),'adopt_whole_inventory')
    else:view.context.source.selected(v['unit_ids'])
    need(v['intent_sha256']==digest(config_intent(v)),'config_intent')
    binding=validate('Binding',v['authority_binding'],b)
    pins=dict(store_id=v['store_id'],session_id=v['session_id'],parent_command_id=v['parent_command_id'],
        source_context_id=v['source_context_id'],snapshot_id=v['snapshot_id'],archive_sha256=v['archive_sha256'],
        base_pair=view.pair,base_model_sha256=v['base_model_sha256'],base_analysis_set_sha256=v['base_analysis_set_sha256'],
        operation=v['mode'],goal=v['goal'],step=v['step'],unit_ids=v['unit_ids'],aliases_sha256=digest(v['aliases']),
        history_sha256=digest(v['history_binding']),anchor_sha256=digest(v['anchor']) if v['anchor'] is not None else None,
        historical_reviews_pin=v['historical_reviews_pin'])
    for lane in ('candidate','analysis'):
        p=v['inputs'][lane];pins[lane+'_sha256']=p['sha256'] if p else None;pins[lane+'_length']=p['byte_length'] if p else 0
        if p:need(p['stage_ref']['command_id']==v['command_id'],'config_stage_owner')
    need(all(binding[k]==x for k,x in pins.items()),'config_authority_binding')
    proof=check_anchor(v['anchor'],view) if v['anchor'] is not None else None
    meta=v['parent_metadata']
    rows=_checked_progress(view,proof)
    if meta is not None:check_admission(meta,view,progress=proof)
    need(binding['progress_before_sha256']==(digest(rows) if meta is not None else None),'config_progress_binding')
    if meta is not None:
        need(binding['current_selectors_sha256']==digest(sorted(meta['selectors'].values(),key=lambda x:x['issue_key'])),'config_selector_binding')
    need(binding['retained_assessment_hashes']==sorted({digest(p['assessment']) for p in rows.values() if p['assessment'] is not None}),'config_retained_binding')
    records=view.history._state['records'];elements,parts=index_model(view.context.model())
    kinds={x['id']:name for name,coll in view.context.maps.items() for x in coll.values()}
    allowed={'Actor':'actors','Action':'actions','Workflow':'workflows','Data':'data','Rule':'rules',
        'Component':'components','Responsibility':'responsibilities','Interface':'interfaces','Dependency':'dependencies'}
    for alias in v['aliases'].values():
        typ=alias['kind'];identity=alias['id']
        if typ in allowed:need(kinds.get(identity)==allowed[typ],'config_alias_type')
        elif typ=='Part':need(identity in parts,'config_alias_part')
        elif typ=='Issue':need(identity in view.analysis_set['body']['issue_ids'],'config_alias_current_issue')
        else:
            group='nodes' if typ=='WorkflowNode' else 'edges'
            need(identity in {x['id'] for w in view.context.body['workflows'] for x in w[group]},'config_alias_workflow_member')
    return v


def _published(command,view,plan_id=None,*,check_parent=True):
    """Read only detached finalized/promoted bytes, never a caller progress dict."""
    try:return _published_data(command,view,plan_id,check_parent=check_parent)
    except (KeyError,TypeError,IndexError,ValueError):need(False,'publisher_metadata_shape')


def _published_data(command,view,plan_id,*,check_parent):
    h=view.history;s=h._state;r=s['records'];b=h.budget
    need(command in s['commands'],'publisher_command');op=s['commands'][command]
    need(op['session_id']==view.session_id,'publisher_session')
    final=[e for (c,_),e in s['events'].items() if c==command and e['kind']=='finalized']
    need(len(final)==1 and final[0]['payload']['run_id']==op['reserved_run_id'],'publisher_finalized')
    run=r[op['reserved_run_id']]['body'];need(run['status'] in ('completed','blocked'),'publisher_status')
    cfgid=run['config_artifact_id'];cfg=b.parse(s['blobs'][cfgid],kind='config',slot='history.config.'+cfgid)
    need(type(cfg) is dict and cfg['command_id']==command and cfg['reserved_run_id']==op['reserved_run_id'] and
         cfg['source_context_id']==view.context.source.context_id,'publisher_config')
    pair=[run['result_model_id'] or run['base_model_id'],run['result_analysis_set_id']]
    aids=[x['artifact_id'] for x in final[0]['payload']['promotions'] if x['artifact_id']!=cfgid and r[x['artifact_id']]['body']['purpose']=='config']
    need(len(aids)==1 and (plan_id is None or plan_id==aids[0]),'publisher_plan_inventory');aid=aids[0]
    plan=b.parse(s['blobs'][aid],kind='plan',slot='history.plan.'+aid)
    need(type(plan) is dict and plan.get('marker') in (PLAN,'s02-h2-plan/0.1.0-draft.2'),'publisher_plan_version')
    need(plan['bindings']['command_id']==command and plan['bindings']['reserved_run_id']==op['reserved_run_id'] and
         plan['batch']['head']==pair and all(r.get(x['id'])==x for x in plan['batch']['records']),'publisher_actual_plan')
    meta=plan['admission'];progress=meta['progress_by_unit']
    need(type(progress) is dict and set(progress)==set(view.context.source.units),'publisher_progress_inventory')
    for uid,row in progress.items():
        rows=_output_rows(row);done=int(row['work_completed_through'])
        need(sorted(rows)==list(range(1,done+1)) and 0<=done<=4,'publisher_stage_inventory')
        a=row['assessment'];need(a is not None and a['result_pair']==pair and
            a['result_model_sha256']==digest(r[pair[0]]) and a['result_analysis_set_sha256']==digest(r[pair[1]]) and
            a['state']==row['assessment_state'] and a['output_refs']==row['outputs'],'publisher_assessment')
    if check_parent:
        prior=None
        if cfg.get('parent_metadata') is not None:
            parent=_published(cfg['parent_command_id'],view,check_parent=False)[0]['admission']
            need(cfg['parent_metadata']==parent,'publisher_parent_metadata');prior=parent['progress_by_unit']
        for uid,row in progress.items():
            expected=digest(prior[uid]['assessment']) if prior and prior[uid]['assessment'] is not None else None
            need(row['assessment']['parent_assessment_sha256']==expected,'publisher_assessment_chain')
    return plan,cfg,pair,aid


def _output_rows(progress):
    rows=progress['outputs']
    if type(rows) is dict:
        result={int(k):v for k,v in rows.items()};need(len(result)==len(rows),'publisher_duplicate_stage')
    else:
        need(type(rows) is list,'publisher_output_rows');result={int(x['step']):x for x in rows}
        need(len(result)==len(rows),'publisher_duplicate_stage')
    return result


def _output_inventory(plan):
    return {(uid,step):row for uid,p in plan['admission']['progress_by_unit'].items() for step,row in _output_rows(p).items()}


def _check_output(out,origin):
    ids=origin.get('output_ids',origin.get('local_ids',[]))
    need(set(out['output_ids'])==set(ids) and out['raw_sha256']==origin['raw_sha256'] and
         out['source_refs']==origin['source_refs'] and out['aliases']==origin['aliases'],'anchor_output_bytes')


def _output_origin(out,view):
    plan,cfg,pair,_=_published(out['origin_command_id'],view);key=out['unit_id'],int(out['step'])
    need(key in _output_inventory(plan),'anchor_output_origin_stage');_check_output(out,_output_inventory(plan)[key])
    need(plan['candidate_outcome']=='valid' and cfg['mode']=='step' and int(cfg['step'])==key[1] and
         key[0] in cfg['unit_ids'] and cfg['inputs']['candidate']['sha256']==out['raw_sha256'],'anchor_origin_raw_stage')
    # The raw pin must be a real input promotion of that publication.
    s=view.history._state;pin=cfg['inputs']['candidate'];final=next(e for (c,_),e in s['events'].items() if c==out['origin_command_id'] and e['kind']=='finalized')
    ref=dict(command_id=out['origin_command_id'],blob_id=pin['blob_id']) if plan['marker']=='s02-h2-plan/0.1.0-draft.2' else pin['stage_ref']
    artifacts=[p['artifact_id'] for p in final['payload']['promotions'] if p['stage_ref']==ref]
    need(len(artifacts)==1 and s['records'][artifacts[0]]['body']['sha256']==out['raw_sha256'],'anchor_origin_promoted_raw')
    elements,parts=index_model(s['records'][pair[0]]);issues=s['records'][pair[1]]['body']['issue_ids']
    need(set(out['output_ids'])<=set(elements)|set(parts)|set(issues),'anchor_output_origin_ids')


@dataclass(frozen=True)
class ProgressEvidence:
    """Detached, provenance-checked anchor stage data. No source of authority."""
    anchor_sha256: str
    pair: tuple
    raw: bytes
    anchor_raw: bytes

    def payload(self):return decode(self.raw)


def check_anchor(value,view):
    v=validate('Anchor',value,view.history.budget);s=view.history._state;r=s['records'];budget=view.history.budget
    _same_source(v,view)
    need(v['plan_artifact_id'] in r and r[v['plan_artifact_id']]['type']=='artifact','anchor_plan_artifact')
    plan,cfg,pair,aid=_published(v['command_id'],view,v['plan_artifact_id'])
    need(r[aid]['body']['sha256']==v['plan_sha256'] and pair==v['published_pair'],'anchor_plan_hash_pair')
    inventory=_output_inventory(plan);keys=[(x['unit_id'],int(x['step'])) for x in v['outputs']]
    proved_units={uid for uid,_ in keys}
    need(len(keys)==len(set(keys)) and set(keys)=={key for key in inventory if key[0] in proved_units},'anchor_full_output_inventory')
    for out in v['outputs']:
        _check_output(out,inventory[out['unit_id'],int(out['step'])]);_output_origin(out,view)
        need(view.context.source.refs(out['source_refs'])==view.context.source.units[out['unit_id']].obligations,'anchor_full_family')
    outputs=deepcopy(v['outputs']);latest=plan
    # Anchor transitions must correspond to introducing operations, not hash claims.
    current=pair
    for t in v['transitions']:
        budget.check();need(t['from_pair']==current,'anchor_transition_order');_same_source(t,view)
        successor,_,nextpair,_=_published(t['command_id'],view)
        need(successor['bindings']['base_pair']==current and nextpair==t['to_pair'],'anchor_transition_pair')
        need(t['parent_assessment_sha256']==digest(latest['admission']['progress_by_unit']) and
             t['result_assessment_sha256']==digest(successor['admission']['progress_by_unit']),'anchor_assessment_chain_hashes')
        old=r[current[0]];new=r[t['to_pair'][0]];oe,opp=index_model(old);ne,np=index_model(new)
        # A missing/modified/removed correspondence is valid data but not proof
        # permitting progress transport. Never infer it from equal names/counts.
        pairs=t['correspondence'];need(all(x['relation'] in ('unchanged','current_ref_rebind') and x['to_id'] is not None for x in pairs),'anchor_incomplete_correspondence')
        seen=set()
        for x in pairs:
            key=x['kind'],x['from_id'];need(key not in seen,'anchor_duplicate_correspondence');seen.add(key)
            tables={'element':(oe,ne),'part':(opp,np),
                'row':({x['id']:x for x in old['body']['mappings']},{x['id']:x for x in new['body']['mappings']}),
                'issue':({i:r[i] for i in r[current[1]]['body']['issue_ids']},{i:r[i] for i in r[t['to_pair'][1]]['body']['issue_ids']})}
            a,b=tables[x['kind']];need(x['from_id'] in a and x['to_id'] in b,'anchor_correspondence_refs')
            need(x['from_context_sha256']==digest(a[x['from_id']]) and x['to_context_sha256']==digest(b[x['to_id']]),'anchor_correspondence_hash')
            if x['relation']=='unchanged':need(a[x['from_id']]==b[x['to_id']] and x['from_id']==x['to_id'],'anchor_unchanged_claim')
            else:
                # Rebinding alone needs an explicit current-key projection. H3-A
                # conservatively refuses unproved domain edits or arbitrary pairs.
                from .h3_history import project_current_refs
                remap={r[i]['body']['issue_key']:i for i in r[t['to_pair'][1]]['body']['issue_ids']}
                ids={i:remap[r[i]['body']['issue_key']] for i in r[current[1]]['body']['issue_ids']}
                projected=project_current_refs(old,new['id'],ids,budget)
                if x['kind']=='element':expected=next(e for group in ('actors','actions','workflows','data','rules','components','responsibilities','interfaces','dependencies') for e in projected[group] if e['id']==x['from_id'])
                elif x['kind']=='row':expected=next(y for y in projected['mappings'] if y['id']==x['from_id'])
                elif x['kind']=='part':expected=next(y for row in projected['mappings'] for y in row['parts'] if y['id']==x['from_id'])
                else:
                    expected=deepcopy(a[x['from_id']]);expected['body']=project_current_refs(expected,new['id'],ids,budget)
                    expected['id']=x['to_id'];expected['body']['supersedes_id']=x['from_id'];expected['created_at']=b[x['to_id']]['created_at']
                need(expected==b[x['to_id']],'anchor_current_ref_rebind')
        need(old['body']['source_context_id']==new['body']['source_context_id']==view.context.source.context_id,'anchor_same_actual_source')
        from .h2_graph import ModelContext,impact
        a=ModelContext(old,view.context.source,budget);b=ModelContext(new,view.context.source,budget);delta=impact(a,b)
        summary=dict(elements=sorted(delta.changed_elements),parts=sorted(delta.changed_parts),rows=sorted(delta.changed_rows),source_changed=delta.source_changed)
        closure=dict(before=delta.before.scope(),after=delta.after.scope())
        need(t['diff_sha256']==digest(summary) and t['closure_sha256']==digest(closure),'anchor_actual_diff_closure')
        correspondence={x['from_id']:x['to_id'] for x in pairs}
        tracked={i for x in outputs for i in x['output_ids']}
        need(tracked<=correspondence.keys(),'anchor_output_coverage')
        for out in outputs:
            out['output_ids']=[correspondence[i] for i in out['output_ids']]
            for alias in out['aliases'].values():
                need(alias['id'] in correspondence,'anchor_alias_coverage');alias['id']=correspondence[alias['id']]
        expected=_output_inventory(successor)
        # A transport is not a new completed-stage claim. If intervening work
        # advanced the publisher, use its complete anchor instead of a prefix.
        need({key for key in expected if key[0] in proved_units}=={(x['unit_id'],int(x['step'])) for x in outputs},'anchor_progress_changed_use_current_publisher')
        for out in outputs:_check_output(out,expected[out['unit_id'],int(out['step'])])
        latest=successor;current=t['to_pair']
    need(current==view.pair,'anchor_to_current_pair')
    from .h3_policy import unassessed_progress
    progress=latest['admission']['progress_by_unit'];byunit=unassessed_progress(view)
    for uid in view.context.source.units:
        if uid not in proved_units:
            # Whole omitted units have no transport proof. Preserve every known
            # publisher output (including inspection findings) as unassessed.
            known={i for row in _output_rows(progress[uid]).values() for i in row.get('output_ids',row.get('local_ids',[]))}
            byunit[uid]['actual_output_ids']=sorted(set(byunit[uid]['actual_output_ids'])|known)
            if known:byunit[uid]['assessment_state']='needs_revalidation'
            continue
        os=sorted((x for x in outputs if x['unit_id']==uid),key=lambda x:int(x['step']))
        p=progress[uid];done=int(p['work_completed_through'])
        need([int(x['step']) for x in os]==list(range(1,done+1)),'anchor_stage_sequence')
        actual=view.context.closure(*view.context.source_seed(view.context.source.units[uid].obligations))
        byunit[uid]=dict(work_completed_through=done,outputs=os,actual_output_ids=sorted(actual.elements|actual.parts|{i for x in os for i in x['output_ids']}),
            assessment_state=p['assessment_state'],unresolved_keys=list(p['unresolved_keys']),next_tasks=list(p['next_tasks']),latest_checked_pair=None,assessment=None)
        validate('Progress',byunit[uid],budget)
    return ProgressEvidence(digest(v),tuple(view.pair),encode(byunit),encode(v))


def _checked_progress(view,progress):
    if progress is None:
        from .h3_policy import unassessed_progress
        return unassessed_progress(view)
    need(type(progress) is ProgressEvidence,'progress_provenance_required')
    reproved=check_anchor(decode(progress.anchor_raw),view)
    need(reproved==progress,'progress_anchor_binding')
    return reproved.payload()


def check_admission(value,view,*,progress=None):
    v=validate('Admission',value,view.history.budget);ctx=view.context
    need(v['result_pair']==view.pair,'admission_result_pair')
    expected=[dict(source_ref=r['source_ref'],mapping_row_id=r['id'],assessment=r['assessment'],mapping_part_ids=[p['id'] for p in r['parts']],issue_ids=r['issue_ids']) for r in ctx.body['mappings']]
    need(v['obligations']==expected,'admission_obligation_inventory')
    current={q['body']['issue_key']:q for q in view.issues}
    need(set(v['selectors'])==set(current),'admission_selector_inventory')
    from .h3_policy import selectors
    selectors(view,list(v['selectors'].values()),list(v['tasks'].values()),list(v['guards'].values()))
    for key,selector in v['selectors'].items():need(selector['issue_key']==key,'admission_selector_key')
    need(set(v['progress_by_unit'])==set(ctx.source.units),'admission_progress_inventory')
    expected=_checked_progress(view,progress)
    need(v['progress_by_unit']==expected,'admission_progress_provenance')
    retained=[p['assessment'] for _,p in sorted(expected.items()) if p['assessment'] is not None]
    need(v['retained_assessments']==retained,'admission_retained_assessment_inventory')
    need({x['issue_key'] for x in v['issue_roles']}==set(current) and len(v['issue_roles'])==len(current),'admission_issue_role_inventory')
    for roles in v['issue_roles']:
        q=current[roles['issue_key']];p=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        need(roles['current_issue_id']==q['id'] and roles['predecessor_issue_id']==q['body']['supersedes_id'],'admission_issue_roles')
        for name in ('origin_issue_id','obsolete_issue_id','replacement_issue_id'):need(roles[name]==(p.get(name) if p else None),'admission_history_roles')
    summary_keys=[t['issue_key'] for t in v['transitions']]
    need(len(summary_keys)==len(set(summary_keys)) and set(summary_keys)<=set(current),'admission_transition_inventory')
    previous=view.history.view(view.session_id,v['from_pair'],v['from_pair'])
    need(previous.context.source.context_id==ctx.source.context_id,'admission_from_source')
    old={q['body']['issue_key']:q['id'] for q in previous.issues}
    changed={key for key,q in current.items() if old.get(key)!=q['id']}
    need(set(old)<=set(current) and changed<=set(summary_keys),'admission_changed_issue_summaries')
    for t in v['transitions']:
        q=current[t['issue_key']];body=q['body'];proof=body['resolution_carry'] or body['resolution_replacement']
        branch='CARRY' if body['resolution_carry'] else 'REPLACEMENT' if body['resolution_replacement'] else 'DIRECT'
        need(t['proof_record_id']==q['id'] and t['proof_sha256']==digest(q),'admission_transition_record')
        need(t['branch']==branch and t['assessment']==(proof['assessment'] if proof else None),'admission_transition_correspondence')
    for lane in ('tasks','guards'):
        need(all(k==o['issue_key'] for k,o in v[lane].items()),'admission_origin_keys')
    for origin in [*v['tasks'].values(),*v['guards'].values()]:
        need(origin['issue_key'] in current and origin['issue_id']==current[origin['issue_key']]['id'],'origin_current_issue')
        command=origin['origin_command_id'];s=view.history._state
        need(command in s['commands'] and origin['root_issue_id'] in s['records'],'origin_history_exists')
        root=s['records'][origin['root_issue_id']]
        need(root['type']=='issue' and root['body']['issue_key']==origin['issue_key'] and
             root['body']['kind'] in ('verification','analysis_omission'),'origin_root_binding')
        cursor=origin['issue_id'];seen=set()
        while cursor!=root['id']:
            need(cursor is not None and cursor not in seen,'origin_current_lineage');seen.add(cursor)
            cursor=s['records'][cursor]['body']['supersedes_id']
        finals=[e for (c,_),e in s['events'].items() if c==command and e['kind']=='finalized']
        need(len(finals)==1,'origin_publication')
        plans=[p['artifact_id'] for p in finals[0]['payload']['promotions'] if s['records'][p['artifact_id']]['body']['sha256']==origin['origin_plan_sha256']]
        need(len(plans)==1,'origin_plan_pin')
        raw=view.history.budget.parse(s['blobs'][plans[0]],kind='plan',slot='history.plan.'+plans[0]);need(type(raw) is dict and raw.get('marker') in (PLAN,'s02-h2-plan/0.1.0-draft.2'),'origin_plan_version')
        need(root in raw['batch']['records'],'origin_root_publication')
        lane='tasks' if 'role' in origin else 'guards';declared=raw['admission'][lane].get(origin['issue_key'])
        need(type(declared) is dict and all(declared.get(k)==origin[k] for k in ('origin_command_id','root_issue_id','predicate')),'origin_predicate')
    return v


def check_plan(value,config,view,*,progress=None):
    v=validate('Plan',value,view.history.budget);cfg=validate('Config',config,view.history.budget)
    binding=v['bindings'];need(all(binding[k]==cfg[k] for k in ('command_id','session_id','parent_command_id','reserved_run_id','intent_sha256','handler_version')),'plan_config_identity')
    need(binding['base_pair']==[cfg['base_model_id'],cfg['base_analysis_set_id']] and
         binding['primary_config_sha256']==digest(cfg) and binding['historical_reviews_pin']==cfg['historical_reviews_pin'] and
         binding['history_sha256']==digest(cfg['history_binding']) and binding['authority_binding_sha256']==digest(cfg['authority_binding']) and
         binding['anchor_sha256']==(digest(cfg['anchor']) if cfg['anchor'] else None),'plan_config_pins')
    need(binding['primary_config_stage_ref']['command_id']==cfg['command_id'],'plan_primary_stage_owner')
    records=v['batch']['records'];ids=[r['id'] for r in records]
    need(len(ids)==len(set(ids)),'plan_record_ids')
    need(all(r['type'] in ('run','artifact','model','change','issue','analysis_set') for r in records),'plan_record_types')
    runs=[r for r in records if r['type']=='run']
    need(len(runs)==1 and runs[0]['id']==cfg['reserved_run_id'] and runs[0]['body']['command_id']==cfg['command_id'],'plan_reserved_run')
    need(not runs[0]['body']['attempts'],'plan_providerless')
    if cfg['mode']=='adopt':need(not any(r['type'] in ('issue','model','change') for r in records),'adopt_no_issue_model_change')
    actual=view.history._state
    need(cfg['command_id'] in actual['commands'],'plan_projected_operation')
    op=actual['commands'][cfg['command_id']]
    need(op['reserved_run_id']==cfg['reserved_run_id'] and op['parent_command_id']==cfg['parent_command_id'] and op['session_id']==cfg['session_id'],'plan_operation_identity')
    need(all(actual['records'].get(r['id'])==r for r in records),'plan_exact_projected_records')
    for r in records:
        if r['type']=='issue':
            p=r['body']['resolution_carry'] or r['body']['resolution_replacement']
            need(p is None or p['evaluation']['method']=='structural_check','plan_no_human_decision')
    byid={r['id']:r for r in records}
    for promotion in v['batch']['artifact_sources']:
        aid=promotion['artifact_id'];sr=promotion['stage_ref']
        need(aid in byid and byid[aid]['type']=='artifact' and byid[aid]['body']['producer_run_id']==cfg['reserved_run_id'],'plan_promoted_artifact')
        need((sr['command_id'],sr['blob_id']) in actual['stages'],'plan_stage_exists')
        stage=actual['stages'][sr['command_id'],sr['blob_id']];artifact=byid[aid]['body']
        need(stage['sha256']==artifact['sha256'] and stage['byte_length']==artifact['byte_length'] and stage['purpose']==artifact['purpose'],'plan_stage_artifact_pin')
    refs=[p['stage_ref'] for p in v['batch']['artifact_sources']]
    prepared=[binding['primary_config_stage_ref']]+[p['stage_ref'] for p in cfg['inputs'].values() if p is not None]
    need(sorted(refs,key=encode)==sorted(prepared,key=encode) and len(refs)==len({encode(p) for p in refs}),'plan_exact_input_promotions')
    need(runs[0]['body']['base_model_id']==cfg['base_model_id'] and runs[0]['body']['base_analysis_set_id']==cfg['base_analysis_set_id'] and
         runs[0]['body']['source_context_id']==cfg['source_context_id'],'plan_run_base_pins')
    expected=deepcopy(v['batch']['artifact_sources'])+[dict(artifact_id=v['allocation']['plan_artifact_id'],stage_ref=dict(command_id=cfg['command_id'],blob_id=v['allocation']['plan_blob_id']))]
    need(v['promotions']==expected and len({p['artifact_id'] for p in expected})==len(expected),'plan_promotions')
    planid=v['allocation']['plan_artifact_id']
    need(planid in actual['records'] and actual['records'][planid]['type']=='artifact' and actual['records'][planid]['body']['sha256']==digest(v),'plan_sealed_artifact_hash')
    if v['batch']['head'] is None:
        need(v['admission'] is None and all(r['type'] in ('run','artifact') for r in records),'plan_no_domain_head')
    else:
        need(v['batch']['head']==view.pair and v['admission'] is not None,'plan_result_pair')
        rb=runs[0]['body'];need([rb['result_model_id'] or rb['base_model_id'],rb['result_analysis_set_id']]==view.pair,'plan_run_result_pair')
        need(binding['base_pair']==[rb['base_model_id'],rb['base_analysis_set_id']]==
             [op['request']['base_model_id'],op['request']['base_analysis_set_id']],'plan_actual_base_pair')
        need(v['admission']['from_pair']==binding['base_pair'],'plan_admission_base_pair')
        check_admission(v['admission'],view,progress=progress)
        need(all(view.history._state['records'].get(r['id'])==r for r in records if r['type'] not in ('artifact','run')),'plan_actual_domain_records')
    return v


def verify_task_origin(value,view):
    """Verify a construction permit against an actual immutable promoted plan."""
    from .h3_contracts import _DEFS
    from .validation import Validator,FORMATS
    v=deepcopy(value);view.history.budget.inspect(v)
    need(next(Validator({**_DEFS['TaskOrigin'],'$defs':_DEFS},format_checker=FORMATS).iter_errors(v),None) is None,'task_origin_shape')
    state=view.history._state;records=state['records'];key=v['issue_key'];q=view.issue(key)
    need(q['id']==v['issue_id'] and q['body']['kind']=='verification' and v['role'] in ('await_builder','global_mapping'),'task_current_issue')
    command=v['origin_command_id'];need(command in state['commands'],'task_origin_command')
    op=state['commands'][command];run=records[op['reserved_run_id']]['body']
    need(op['session_id']==view.session_id and run['status'] in ('completed','blocked') and run['result_analysis_set_id'] is not None,'task_origin_run')
    root=records.get(v['root_issue_id']);need(root is not None and root['type']=='issue' and root['body']['issue_key']==key and root['body']['kind']=='verification','task_root')
    need(root['id'] in records[run['result_analysis_set_id']]['body']['changed_record_ids'],'task_root_introduced')
    cursor=q['id'];seen=set()
    while cursor!=root['id']:
        need(cursor is not None and cursor not in seen,'task_current_lineage');seen.add(cursor);cursor=records[cursor]['body']['supersedes_id']
    finals=[e for (c,_),e in state['events'].items() if c==command and e['kind']=='finalized']
    need(len(finals)==1,'task_origin_finalized')
    artifacts=[p['artifact_id'] for p in finals[0]['payload']['promotions'] if records[p['artifact_id']]['body']['purpose']=='config' and records[p['artifact_id']]['body']['sha256']==v['origin_plan_sha256']]
    need(len(artifacts)==1,'task_origin_plan_hash')
    plan=view.history.budget.parse(state['blobs'][artifacts[0]],kind='plan',slot='history.plan.'+artifacts[0])
    need(type(plan) is dict and plan.get('marker') in (PLAN,'s02-h2-plan/0.1.0-draft.2') and
         plan['bindings']['command_id']==command and plan['bindings']['reserved_run_id']==op['reserved_run_id'] and root in plan['batch']['records'],'task_origin_plan_binding')
    declared=plan['admission']['tasks'].get(key)
    need(type(declared) is dict and all(declared.get(k)==v[k] for k in ('origin_command_id','root_issue_id','unit_ids','target_step','role','predicate')),'task_origin_predicate')
    need(v['predicate'] in ('h2.all_mapping/1','h2.unit_mapping/1','h2.unit_responsibility/1'),'task_known_predicate')
    need(bool(v['unit_ids']) and set(v['unit_ids'])<=set(view.context.source.units),'task_unit_inventory')
    need(v['role']!='global_mapping' or set(v['unit_ids'])==set(view.context.source.units) and v['target_step']==4,'global_task_full_inventory')
    return v


def verify_guard_origin(value,view):
    """Existing H2 guard provenance only; this never resolves or exempts a hold."""
    from hashlib import sha256
    from .h3_contracts import _DEFS
    from .validation import Validator,FORMATS
    v=deepcopy(value);view.history.budget.inspect(v)
    need(next(Validator({**_DEFS['GuardOrigin'],'$defs':_DEFS},format_checker=FORMATS).iter_errors(v),None) is None,'guard_origin_shape')
    state=view.history._state;records=state['records'];command=v['origin_command_id'];q=view.issue(v['issue_key'])
    need(q['id']==v['issue_id'] and q['body']['kind']=='analysis_omission' and not q['body']['answer_ids'] and
         q['body']['resolution_carry'] is None and q['body']['resolution_replacement'] is None,'guard_current_direct')
    need(v['issue_key']=='h2.guard.'+sha256(command.encode('ascii')).hexdigest() and v['predicate']=='h2.merge_assessment/1','guard_key_predicate')
    need(command in state['commands'],'guard_origin_command');op=state['commands'][command]
    need(op['session_id']==view.session_id and op['request']['source_context_id']==v['source_context_id']==view.context.source.context_id and
         [op['request']['base_model_id'],op['request']['base_analysis_set_id']]==v['base_pair'],'guard_source_base')
    finals=[e for (c,_),e in state['events'].items() if c==command and e['kind']=='finalized']
    need(len(finals)==1,'guard_origin_finalized')
    plans=[p['artifact_id'] for p in finals[0]['payload']['promotions'] if records[p['artifact_id']]['body']['purpose']=='config' and records[p['artifact_id']]['body']['sha256']==v['origin_plan_sha256']]
    need(len(plans)==1,'guard_origin_plan_hash');plan=view.history.budget.parse(state['blobs'][plans[0]],kind='plan',slot='history.plan.'+plans[0])
    need(plan.get('marker')=='s02-h2-plan/0.1.0-draft.2' and plan['candidate_outcome']=='guard_only' and
         plan['bindings']['command_id']==command and plan['bindings']['reserved_run_id']==op['reserved_run_id'],'guard_origin_plan')
    root=records.get(v['root_issue_id']);need(root is not None and root in plan['batch']['records'] and root['body']['status']=='open' and
         root['body']['model_id']==v['base_pair'][0] and root['body']['supersedes_id'] is None,'guard_root')
    declared=plan['admission']['guards'].get(v['issue_key'])
    need(type(declared) is dict and all(declared.get(k)==v[k] for k in ('origin_command_id','root_issue_id','base_pair','predicate')) and
         declared['candidate_sha256']==v['failed_candidate_sha256'] and declared['analysis_sha256']==v['failed_analysis_sha256'],'guard_failed_raw_pins')
    cursor=q['id'];seen=set()
    while cursor!=root['id']:
        need(cursor is not None and cursor not in seen,'guard_current_lineage');seen.add(cursor);cursor=records[cursor]['body']['supersedes_id']
    return v
