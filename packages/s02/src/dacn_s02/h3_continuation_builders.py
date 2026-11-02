"""Pure typed C projection and append-only A2 successors.

Allocations/times are explicit inputs. No filesystem, Repository, clock, decision,
Answer, application, Validation or TaskAttestation is created here.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from dacn_s01.revision import json_equal
from .repository import record
from .profiles import E1,blocking_statuses
from .validation import shape,index_model,resolve_pointer,scope_sets
from .scope import make_scope,reverse_impact
from .h1_candidates import Linker,KINDS
from .h1_builders import trace,allscope,part_has_gap
from .h2_candidates import parse_candidate
from .h2_graph import ModelContext,impact,semantic
from .h2_policy import materialize
from .h2_contracts import HoldSelector
from .h3_history import project_current_refs
from .h3_checkpoint_checks import normalized_aliases,task_inventory
from .resolution import source_basis,footprint,_scope_proof,_target_footprint_unchanged
from .h3_limits import need,digest
from .h3_continuation_inputs import refs,read_context,h2_aliases
from .h3_continuation_contracts import validate


class GuardNeeded(Exception):
    """Valid history/candidate but no permitted successor/independent publication."""
    def __init__(self,*reasons):self.reasons=tuple(sorted(set(reasons)));super().__init__(','.join(self.reasons))


def finding_key(command,step,handle):return 'h3.finding.'+digest([command,step,handle])
def guard_key(command):return 'h3.guard.'+sha256(command.encode('ascii')).hexdigest()


class CandidateLaneBudget:
    """Namespace parser slots per command without resetting any shared counter."""
    def __init__(self,budget,command):self.budget=budget;self.command=command
    def __getattr__(self,key):return getattr(self.budget,key)
    def parse(self,raw,*,slot=None,kind='raw'):
        return self.budget.parse(raw,slot='c.candidate.'+self.command+('.'+slot if slot else ''),kind=kind)


def candidate(raw,base,cfg):
    budget=base.history.budget;budget.raw_work(raw,b'x')
    # The unchanged H2 parser's local 'candidate' slot is scoped to this C
    # command. Historical publisher reconstruction shares the same invocation
    # budget, so different commands must not impersonate the same input slot.
    context=ModelContext(base.context.model(),base.context.source,CandidateLaneBudget(budget,cfg['command_id']))
    return parse_candidate(raw,context,step=int(cfg['step']),unit_ids=cfg['unit_ids'],
        expected_scope_hash=cfg['authority_binding']['read_write_intent_sha256'],base_aliases=h2_aliases(cfg['aliases']),
        read_context_ids=read_context(base,dict(cfg['parent_metadata'],selected_units=cfg['unit_ids'])),
        current_issue_ids=frozenset(q['id'] for q in base.issues))


def project(base,cfg,parsed,fresh,now,*,local_bindings=None,model_allocation=None):
    """Raw H2 shape -> typed pre-successor Model, with frozen replay allocation."""
    value=parsed.payload();step=int(cfg['step']);source=base.context.source
    if local_bindings is not None:
        declared=dict(parsed.declared_handles);need(set(local_bindings)==set(declared),'c_projection_handle_inventory')
        need(all(local_bindings[h]['kind']=={'Node':'WorkflowNode','Edge':'WorkflowEdge'}.get(k,k) for h,k in declared.items()),'c_projection_handle_types')
        order=[]
        def allocate():
            need(bool(order),'c_projection_allocation_count');return order.pop(0)
        # Linker declares in raw traversal order. Supply those IDs by handle,
        # rather than trusting a caller-controlled dict insertion order.
        probe=Linker(value,h2_aliases(cfg['aliases']),base.history._snapshots[source.snapshot_id],lambda:'c.shape.id')
        order.extend(local_bindings[h]['id'] for h in probe.local)
        linker=Linker(value,h2_aliases(cfg['aliases']),base.history._snapshots[source.snapshot_id],allocate)
        need(not order,'c_projection_allocation_count')
    else:linker=Linker(value,h2_aliases(cfg['aliases']),base.history._snapshots[source.snapshot_id],fresh)
    model=base.context.model()
    if step>1:
        mid,cid=model_allocation if model_allocation is not None else (fresh(),fresh())
        model.update(id=mid,created_at=now);model['body'].update(revision=int(model['body']['revision'])+1,parent_model_id=base.pair[0],change_id=cid,created_by_run_id=cfg['reserved_run_id'])
    for coll in KINDS:
        for row in value['proposals'].get(coll,[]):
            converted=linker.convert(row)
            if coll=='actors':converted['kind']='candidate'
            model['body'][coll].append(converted)
    if step==4:
        rows={r['source_ref']['input_pointer']:r for r in model['body']['mappings']}
        for row in value['proposals']['mappings']:
            old=rows[row['source_ref']['input_pointer']]
            need(old['assessment']=='not_assessed' and not old['parts'],'c_completed_mapping_edit')
            converted=linker.convert(row);old.update(parts=converted['parts'],assessment=converted['assessment'],issue_ids=converted['issue_ids'])
    findings=[];selectors={};elements,parts=index_model(model)
    for f in value['proposals']['findings']:
        affected={linker.ref(r) for r in f['affected_refs']};blocking={linker.ref(r) for r in f['blocking_refs']}
        need(blocking<=affected and affected<=elements.keys()|parts.keys(),'c_finding_scope')
        key=finding_key(cfg['command_id'],step,f['handle']);need(key not in cfg['parent_metadata']['selectors'],'c_new_key_collision')
        scope=make_scope(model['id'],affected&elements.keys(),affected&parts.keys())
        q=record('issue',linker.findings[f['handle']],dict(issue_key=key,supersedes_id=None,model_id=model['id'],detected_step=step,
            kind=f['kind'],question=f['question'],reason=f['reason'],trace=linker.convert(f['trace']),affected=scope,
            blocking=make_scope(model['id'],blocking&elements.keys(),blocking&parts.keys()),status='open',answer_ids=[],resolution_event_refs=[],resolution=None,resolution_carry=None,resolution_replacement=None),now)
        findings.append(q);sources=source.refs(q['body']['trace']['source_refs'])
        selectors[key]=dict(issue_id=q['id'],issue_key=key,target_step=1,kind='all_source_uses' if not f['impact_known'] else 'obligation_families' if sources<=source.obligations else 'explicit_uses',
            source_refs=refs(source,sources),element_ids=sorted(blocking&elements.keys()),mapping_part_ids=sorted(blocking&parts.keys()),impact_known=f['impact_known'],code_task_role=None)
    projection=dict(candidate_sha256=parsed.sha256,local_bindings=normalized_aliases(linker.local),pre_successor_model=model if step>1 else None,pre_successor_model_sha256=digest(model) if step>1 else None)
    validate('CandidateProjection',projection,base.history.budget)
    return projection,model,findings,selectors


def effective_selectors(base,metadata):
    """A full canonical A2 footprint can establish a local structural selector.

    A prose independence label alone never shrinks an unknown selector. Missing
    scope correspondence remains unknown/global. No historical bytes are edited.
    """
    rows=deepcopy(metadata['selectors']);s=base.history._state;source=base.context.source
    for q in base.issues:
        row=rows[q['body']['issue_key']];p=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        if row['impact_known'] or p is None:continue
        previous=s['records'][p['from_issue_id']]
        complete,_,_= _scope_proof(q,previous,p,s['records'])
        basis,_,known=source_basis(q,s['records'],base.history._snapshots,s['events'])
        current={ptr for sid,ptr in basis if sid==source.snapshot_id}
        if complete and known and current and current<=source.obligations:
            row.update(kind='obligation_families',source_refs=refs(source,current),impact_known=True)
    return rows


def hold_selector(row,source,identity=None):
    return HoldSelector(identity or row['issue_id'],row['issue_key'],int(row['target_step']),row['kind'],source.refs(row['source_refs']),frozenset(row['element_ids']),frozenset(row['mapping_part_ids']),row['impact_known'],row['code_task_role'])


def materialized_body(q,model,row,source,budget):
    body=deepcopy(q['body']);ctx=ModelContext(model,source,budget)
    sel=hold_selector(row,source,q['id']);fp=materialize(ctx,sel,q)
    body['affected']=make_scope(model['id'],set(body['affected']['element_ids'])|fp.elements,set(body['affected']['mapping_part_ids'])|fp.parts)
    if body['status'] in blocking_statuses(E1):
        body['blocking']=make_scope(model['id'],set(body['blocking']['element_ids'])|fp.uses|sel.elements,set(body['blocking']['mapping_part_ids'])|fp.active_parts|sel.parts)
    return body


def scope_check(old,body,model,records):
    previous=records[old['body']['model_id']];newscope,_=footprint(model,body['affected']);oldscope,_=footprint(previous,old['body']['affected'])
    ne,np=index_model(model);survive=make_scope(model['id'],set(oldscope['element_ids'])&ne.keys(),set(oldscope['mapping_part_ids'])&np.keys());survive,_=footprint(model,survive)
    current=make_scope(model['id'],set(newscope['element_ids'])|set(survive['element_ids']),set(newscope['mapping_part_ids'])|set(survive['mapping_part_ids']))
    body['affected']=current;oe,op=index_model(previous);oldmap={**oe,**op};newmap={**ne,**np};pairs=[]
    for i in sorted(set(oldscope['element_ids']+oldscope['mapping_part_ids'])):
        same=i in newmap and json_equal(oldmap[i],newmap[i]);pairs.append(dict(**{'from':dict(model_id=previous['id'],element_id=i),'to':dict(model_id=model['id'],element_id=i) if i in newmap else None},relation='unchanged' if same else 'modified' if i in newmap else 'removed',reason='Code compares exact typed values; row context checked canonically'))
    return dict(from_scope=oldscope,to_scope=current,element_pairs=pairs,reason='Code forward/reverse footprint and surviving impact on both Models')


def _basis(old,origin,base):
    s=base.history._state
    a,_,_=source_basis(old,s['records'],base.history._snapshots,s['events']);b,_,_=source_basis(origin,s['records'],base.history._snapshots,s['events']);return a|b


def _source_checks(basis,base):
    sid=base.context.source.snapshot_id;checks=[]
    for oldsid,ptr in sorted(basis):
        before=resolve_pointer(base.history._snapshots[oldsid]['input'],ptr)
        try:after=resolve_pointer(base.history._snapshots[sid]['input'],ptr)
        except (KeyError,IndexError,ValueError):after=None;present=False
        else:present=True
        checks.append(dict(from_ref=dict(snapshot_id=oldsid,input_pointer=ptr),to_ref=dict(snapshot_id=sid,input_pointer=ptr) if present else None,
            relation='equal_value' if present and json_equal(before,after) else 'changed' if present else 'removed',reason='Code checks exact source values and snapshot roles'))
    return checks


def _task_done(task,model,issues,source,step,units):
    if task['target_step']!=step or not set(task['unit_ids'])<=set(units) and task['role']!='global_mapping':return False
    ptrs=source.selected(task['unit_ids']);rows=model['body']['mappings']
    if step==4:return all(r['assessment']=='proposed' and r['parts'] for r in rows if r['source_ref']['input_pointer'] in ptrs)
    actions={a['id'] for a in model['body']['actions'] if source.refs(a['trace']['source_refs'])&ptrs}
    assigned={a for r in model['body']['responsibilities'] for a in r['action_ids']}
    gaps={a for q in issues if q['body']['status'] in blocking_statuses(E1) and q['body']['kind']=='analysis_omission' for a in q['body']['blocking']['element_ids']}
    return actions<=assigned|gaps


def successors(base,cfg,model,findings,rows,fresh,now,*,allocations=None):
    """Whole current-key map first, then typed current refs, then A2 proofs."""
    source=base.context.source;state=base.history._state;oldmap={q['body']['issue_key']:q for q in base.issues}
    need(model['id']!=base.pair[0],'c_successor_requires_model')
    ids=allocations or {k:fresh() for k in oldmap};need(set(ids)==set(oldmap),'c_successor_key_allocations')
    need(len(set(ids.values()))==len(ids),'c_successor_unique_ids')
    remap={q['id']:ids[k] for k,q in oldmap.items()}
    # An immutable Model may still physically name a same-key ancestor after
    # an AS-only checkpoint. Resolve its current-role fields by the CHECKED
    # selected lineage, never by a string/key match to an unrelated Issue.
    for key,current in oldmap.items():
        cursor=current['id'];visited=set()
        while cursor is not None:
            base.history.budget.check();need(cursor not in visited,'c_current_ref_lineage');visited.add(cursor)
            ancestor=state['records'][cursor]
            need(ancestor['type']=='issue' and ancestor['body']['issue_key']==key and state['owners'][cursor]==base.session_id,'c_current_ref_lineage')
            remap[cursor]=ids[key];cursor=ancestor['body']['supersedes_id']
    remap.update({q['id']:q['id'] for q in findings})
    model=deepcopy(model);model['body']=project_current_refs(model,model['id'],remap,base.history.budget)
    result={};records=deepcopy(state['records']);records[model['id']]=model
    tasks=task_inventory(base)
    for key,old in oldmap.items():
        body=project_current_refs(old,model['id'],remap,base.history.budget);body['supersedes_id']=old['id']
        q=record('issue',ids[key],body,now)
        if old['body']['status'] in blocking_statuses(E1):q['body']=materialized_body(q,model,rows[key],source,base.history.budget)
        result[key]=q;records[q['id']]=q
    # Targets are allocated/current before replacement proofs are constructed.
    for key,old in oldmap.items():
        q=result[key];body=q['body'];pb=old['body'];prior=pb['resolution_carry'] or pb['resolution_replacement']
        if prior is None and not (pb['status']=='resolved' and pb['answer_ids']):
            if key in tasks and pb['status']=='resolved':
                # Retain an already completed technical fact only by checking
                # its ORIGINAL predicate/unit on the whole current Model. A
                # later builder may add Parts without undoing responsibility
                # coverage. This does not resolve a task at a different step.
                task=tasks[key]
                if not _task_done(task,model,list(result.values())+findings,source,int(task['target_step']),task['unit_ids']):
                    raise GuardNeeded('RETAINED_TASK_PREDICATE_FAILED')
            elif key in tasks and _task_done(tasks[key],model,list(result.values())+findings,source,int(cfg['step']),cfg['unit_ids']):
                body.update(status='resolved',resolution='Code checked '+tasks[key]['predicate']+'; synthetic continuation',blocking=make_scope(model['id']))
            elif pb['status']=='resolved':
                probe=deepcopy(q);sc=scope_check(old,probe['body'],model,records);fake=dict(scope_check=sc)
                complete,unchanged,_=_scope_proof(probe,old,fake,records)
                if not (complete and unchanged):raise GuardNeeded('SOURCE_ONLY_MEANING_OR_IMPACT_CHANGED')
            continue
        origin=records[prior['origin_issue_id']] if prior else old;basis=_basis(old,origin,base)
        evaluation=dict(method='structural_check',evaluator='dacn-s02 H3-C pure builder',rule_version='s02-rules/a1a2-v1',evidence_record_ids=[model['id']],reason='Technical continuation only; no human decision')
        sc=scope_check(old,body,model,records);common=dict(origin_issue_id=origin['id'],from_issue_id=old['id'],base_analysis_set_id=base.pair[1],change_id=model['body']['change_id'],scope_check=sc,evaluation=evaluation)
        replace=pb['resolution_replacement'] is not None or prior is not None and prior['assessment']=='not_applicable'
        if replace:
            oldproof=pb['resolution_replacement'];target=None
            if oldproof is not None:
                tk=records[oldproof['replacement_issue_id']]['body']['issue_key'];target=result.get(tk)
            else:
                # An existing, uniquely covering current target may introduce
                # only an INCOMPLETE replacement. Ambiguity never auto-selects
                # a key, and an existing replacement never follows a new key.
                choices=[]
                for tk,t in result.items():
                    if tk==key or t['body']['resolution_replacement'] is not None:continue
                    oldtarget=oldmap[tk];tbasis,tscope,tknown=source_basis(oldtarget,state['records'],base.history._snapshots,state['events'])
                    oldscope,_=footprint(state['records'][old['body']['model_id']],old['body']['affected'])
                    if tknown and basis<=tbasis and all(a<=b for a,b in zip(scope_sets(oldscope),scope_sets(oldtarget['body']['affected']))):choices.append(t)
                if len(choices)==1:target=choices[0]
            if target is None or target['body']['issue_key']==key or target['body']['resolution_replacement'] is not None:raise GuardNeeded('OBSOLETE_REQUIRES_EXISTING_CURRENT_TARGET')
            obsolete=oldproof['obsolete_issue_id'] if oldproof else old['id']
            checks=[]
            if oldproof and any(c['disposition']=='removed' for c in oldproof['obligation_checks']):
                checks=deepcopy(oldproof['obligation_checks'])
                for c in checks:c['evidence_record_ids']=[target['id']]
            else:
                checks=[dict(old_ref=dict(snapshot_id=s,input_pointer=p),current_ref=dict(snapshot_id=source.snapshot_id,input_pointer=p),disposition='replaced',evidence_record_ids=[target['id']],reason='Current checked target evidence; no new completion decision') for s,p in sorted(basis) if p in source.obligations]
            proof=dict(**common,obsolete_issue_id=obsolete,replacement_issue_id=target['id'],assessment='incomplete',obligation_checks=checks)
            body.update(resolution_carry=None,resolution_replacement=proof,status='resolution_pending_revalidation',blocking=deepcopy(sc['to_scope']))
        else:
            checks=_source_checks(basis,base);proof=dict(**common,assessment='undetermined',source_checks=checks)
            body.update(resolution_carry=proof,resolution_replacement=None,status='resolution_pending_revalidation',blocking=deepcopy(sc['to_scope']))
        if not any(scope_sets(body['blocking'])):raise GuardNeeded('PENDING_SUCCESSOR_HAS_NO_MATERIALIZED_HOLD')
    # Classify all CARRY targets before REPLACEMENT continuation.
    for key,old in sorted(oldmap.items(),key=lambda row:result[row[0]]['body']['resolution_replacement'] is not None):
        q=result[key];body=q['body'];p=body['resolution_carry'] or body['resolution_replacement']
        if p is None:continue
        complete,unchanged,_=_scope_proof(q,old,p,records)
        oldsid=records[records[old['body']['model_id']]['body']['source_context_id']]['body']['snapshot_id']
        if body['resolution_carry'] is not None:
            same=all(c['relation']=='equal_value' and c['from_ref']==c['to_ref'] for c in p['source_checks'])
            current_basis,_,_=source_basis(q,records,base.history._snapshots,state['events'])
            targets={(c['to_ref']['snapshot_id'],c['to_ref']['input_pointer']) for c in p['source_checks'] if c['to_ref']}
            covered={r for r in current_basis if r[0]==source.snapshot_id}<=targets
            if old['body']['status']=='resolved' and complete and unchanged and same and covered and oldsid==source.snapshot_id:
                p['assessment']='applicable';body.update(status='resolved',blocking=make_scope(model['id']))
        else:
            previous=old['body']['resolution_replacement'];target=records[p['replacement_issue_id']]
            target_ok=target['body']['status']=='resolved' and not target['body']['resolution_replacement']
            oldtarget=records[previous['replacement_issue_id']] if previous else None
            # Old-model reevaluation tasks need current evidence/attestations;
            # this scope never fabricates those to keep a replacement complete.
            pending_tasks=False;mid=base.pair[0];seen=set()
            while mid is not None:
                need(mid not in seen,'c_task_model_cycle');seen.add(mid);m=records[mid]['body'];cid=m['change_id']
                if cid and records[cid]['body']['reevaluate']:pending_tasks=True
                mid=m['parent_model_id']
            basis=_basis(old,records[p['origin_issue_id']],base);seen={(c['old_ref']['snapshot_id'],c['old_ref']['input_pointer']) for c in p['obligation_checks']}
            targets={(c['current_ref']['snapshot_id'],c['current_ref']['input_pointer']) for c in p['obligation_checks'] if c['current_ref']}
            target_basis,_,_=source_basis(target,records,base.history._snapshots,state['events'])
            current_basis,_,_=source_basis(q,records,base.history._snapshots,state['events'])
            coverage=seen==basis and {r for r in current_basis if r[0]==source.snapshot_id}<=targets and targets<=target_basis and all(a<=b for a,b in zip(scope_sets(p['scope_check']['to_scope']),scope_sets(target['body']['affected'])))
            if previous and previous['assessment']=='complete' and coverage and oldsid==source.snapshot_id and complete and unchanged and target_ok and oldtarget and _target_footprint_unchanged(oldtarget['body'],target['body'],records) and not pending_tasks:
                p['assessment']='complete';body.update(status='resolution_replaced',blocking=make_scope(model['id']))
    return model,[result[k] for k in oldmap]+findings,remap


def domain_records(base,cfg,model,issues,now,aset_id):
    changed=model['id']!=base.pair[0];oldids=set(base.analysis_set['body']['issue_ids'])
    introduced=[q for q in issues if q['id'] not in oldids]
    aset=record('analysis_set',aset_id,dict(model_id=model['id'],revision=1 if changed else int(base.analysis_set['body']['revision'])+1,
        parent_set_id=None if changed else base.pair[1],scenario_ids=list(base.analysis_set['body']['scenario_ids']),characteristic_ids=list(base.analysis_set['body']['characteristic_ids']),
        issue_ids=[q['id'] for q in issues],changed_record_ids=[q['id'] for q in introduced],affected=allscope(model)),now)
    records=introduced+[aset]
    if changed:
        a,ap=index_model(base.context.model());b,bp=index_model(model);old={**a,**ap};new={**b,**bp}
        operations=[dict(kind='add' if i not in old else 'replace',element_id=i,reason='Append-only typed C proposal/current Issue refs') for i in sorted(new) if i not in old or old[i]!=new[i]]
        change=record('change',model['body']['change_id'],dict(base_model_id=base.pair[0],new_model_id=model['id'],kind='analysis_edit',old_source_context_id=base.context.source.context_id,new_source_context_id=base.context.source.context_id,
            reason='Synthetic append-only continuation; historical applications unchanged',source_record_ids=[q['id'] for q in base.issues],application_event_refs=[],operations=operations,
            affected=allscope(model),reused=[],reevaluate=[],invalidated_bundle_ids=[]),now)
        records.extend([model,change])
    for r in records:shape(r,profile=E1)
    return records,aset
