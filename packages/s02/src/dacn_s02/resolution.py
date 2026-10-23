"""A2 validators: immutable DIRECT roots, CARRY and REPLACEMENT proofs.

These are structural proof checks, never business acceptance. Human decisions
are separate trusted caller evidence bound to the immutable dependency graph;
a reviewer string inside an Issue cannot authorize its own conclusion.
"""
from dataclasses import dataclass
from hashlib import sha256
import re
from dacn_s01.revision import json_equal
from .codec_boundary import encode
from .errors import require
from .profiles import E1, L1
from .validation import (fields, shape, validate_direct, index_model, scope_sets,
                         subset, resolve_pointer)
from .scope import closure, reverse_impact, make_scope

@dataclass(frozen=True)
class HumanReviewEvidence:
    reviewer: str
    dependency_sha256: str
    assessment: str


def review_digest(issue, records, snapshots, profiles):
    """Pin reachable immutable records and snapshots, not future store heads.

    This digest binds a decision; it does not prove who made the decision.
    Only a trusted user-interaction adapter may supply HumanReviewEvidence.
    """
    todo=[issue['id']];seen=set();source_ids=set()
    while todo:
        identity=todo.pop()
        if identity in seen:continue
        require(identity in records,'review_evidence_record')
        seen.add(identity);r=records[identity]
        for value,spec,_,name in fields(r,profile=profiles[identity]):
            if 'x-record' in spec:todo.append(value)
            if name=='SourceRef':source_ids.add(value['snapshot_id'])
        if r['type']=='source_context':source_ids.add(r['body']['snapshot_id'])
    return sha256(encode(dict(records=[records[i] for i in sorted(seen)],snapshots=[snapshots[i] for i in sorted(source_ids)]))).hexdigest()


def _refkey(ref):return (ref['snapshot_id'],ref['input_pointer'])
def _reference(key):return dict(snapshot_id=key[0],input_pointer=key[1])
def _elementkey(ref):return (ref['model_id'],ref['element_id'])


def footprint(model, scope):
    """Forward + reverse impact, then follow data/actor refs without pulling
    unrelated actions merely because they share a component or responsibility.
    """
    es,ps=index_model(model)
    c=closure(model,scope);e,p=scope_sets(c.scope)
    r=reverse_impact(model,e,p);e,p=scope_sets(r)
    c=closure(model,make_scope(model['id'],e,p));e,p=scope_sets(c.scope)
    pending=list(e);seen=set()
    while pending:
        i=pending.pop()
        if i in seen:continue
        seen.add(i);v=es[i]
        for field in ('actor_ids','read_data_ids','write_data_ids','rule_ids','permission_rule_ids'):
            for target in v.get(field,[]):
                if target not in e:e.add(target);pending.append(target)
    return make_scope(model['id'],e,p),not c.reasons


def _sources(value):
    if type(value) is dict:
        if set(value)=={'snapshot_id','input_pointer'}:yield _refkey(value)
        else:
            for v in value.values():yield from _sources(v)
    elif type(value) is list:
        for v in value:yield from _sources(v)


def source_basis(issue, records, snapshots, events):
    """Derive basis from origin/previous trace, Answers, selected interpretation,
    and the full affected footprint; never trust a supplied checks inventory.
    """
    b=issue['body'];model=records[b['model_id']];scope,known=footprint(model,b['affected'])
    es,ps=index_model(model);keys=set(_sources(b['trace']))
    for i in scope['element_ids']:keys.update(_sources(es[i]))
    for row in model['body']['mappings']:
        if any(p['id'] in scope['mapping_part_ids'] for p in row['parts']):keys.add(_refkey(row['source_ref']))
    answerids=set(b['answer_ids'])|{r['answer_id'] for r in b['trace']['answer_refs']}
    for i in answerids:keys.update(_sources(records[i]['body']['existing_source_refs']))
    for ref in b['resolution_event_refs']:
        application=events[ref['command_id'],ref['event_id']]['payload']
        selected=application['interpretation_event']
        keys.update(_sources(events[selected['command_id'],selected['event_id']]['payload']['existing_source_refs']))
    # A requirement object obliges separate coverage of every criterion too.
    for sid,pointer in list(keys):
        match=re.fullmatch(r'/(functional_requirements|non_functional_requirements|constraints)/(0|[1-9][0-9]*)(?:/.*)?',pointer)
        if match:
            parent='/'+match[1]+'/'+match[2];keys.add((sid,parent))
            requirement=resolve_pointer(snapshots[sid]['input'],parent)
            keys.update((sid,parent+'/acceptance_criteria/'+str(i)) for i in range(len(requirement['acceptance_criteria'])))
    return keys,scope,known


def _publication(issue, proof, records, commands, events):
    """Find the pinned introducing operation, not whichever set is head today."""
    candidates=[]
    for run in records.values():
        if run['type']!='run':continue
        b=run['body'];sid=b['result_analysis_set_id']
        if sid and issue['id'] in records[sid]['body']['changed_record_ids']:
            candidates.append(run)
    require(len(candidates)==1,'resolution_publication_unique')
    run=candidates[0];r=run['body'];op=commands.get(r['command_id'])
    require(op is not None,'resolution_publication_operation')
    base=records[proof['base_analysis_set_id']]['body'];result=records[r['result_analysis_set_id']]['body']
    require(r['base_model_id']==op['request'].get('base_model_id')==base['model_id'] and
            r['base_analysis_set_id']==op['request'].get('base_analysis_set_id')==proof['base_analysis_set_id'],'resolution_pinned_base_pair')
    require(op['request']['kind']=='work' or op['request']['kind']=='apply_answer','resolution_operation_kind')
    require(op['request']['source_context_id']==records[base['model_id']]['body']['source_context_id'],'resolution_base_source_pin')
    require(run['id']==op['reserved_run_id'] and r['status'] in ('completed','blocked'),'resolution_successful_run')
    require(any(e['kind']=='finalized' and e['payload']['run_id']==run['id'] for (c,_),e in events.items() if c==op['command_id']),'resolution_atomic_finalization')
    require(issue['id'] in result['issue_ids'] and result['model_id']==issue['body']['model_id'],'resolution_current_selection')
    previous={records[i]['body']['issue_key']:i for i in base['issue_ids']}
    current={records[i]['body']['issue_key']:i for i in result['issue_ids']}
    require(previous.keys()<=current.keys(),'resolution_keys_preserved')
    require(previous.get(issue['body']['issue_key'])==proof['from_issue_id'],'resolution_current_predecessor')
    for key,identity in previous.items():
        new=current[key]
        require(new==identity or records[new]['body']['supersedes_id']==identity,'resolution_no_skipped_key')
    if base['model_id']==result['model_id']:
        require(result['parent_set_id']==proof['base_analysis_set_id'] and proof['change_id'] is None,'resolution_same_model_set')
    else:
        m=records[result['model_id']]['body']
        require(m['parent_model_id']==base['model_id'] and m['change_id']==proof['change_id'] and proof['change_id'] is not None,'resolution_parent_model_change')
        ch=records[proof['change_id']]['body']
        require(ch['base_model_id']==base['model_id'] and ch['new_model_id']==result['model_id'] and proof['from_issue_id'] in ch['source_record_ids'],'resolution_change_evidence')
        require(not any(ref in ch['application_event_refs'] for ref in issue['body']['resolution_event_refs']),'resolution_no_old_application_backlink')
    return result


def _part_value(part):
    # These ID arrays are sets in the mapping contract, not ordered workflows.
    return {k:sorted(v) if k in ('action_ids','primary_responsibility_ids',
                                'supporting_responsibility_ids','issue_ids') else v
            for k,v in part.items()}


def _structural_index(model):
    """E1 comparison values retain each Part's owning obligation and context.

    Keep the legacy index_model/closure representation untouched. Row/Part
    order is immaterial; row identity, source, assessment, issues and membership
    are not. No aggregate source set can substitute for these associations.
    """
    elements,_=index_model(model);parts={}
    for row in model['body']['mappings']:
        context={k:sorted(v) if k=='issue_ids' else v for k,v in row.items() if k!='parts'}
        context['part_ids']=sorted(p['id'] for p in row['parts'])
        for part in row['parts']:
            parts[part['id']]=dict(part=_part_value(part),mapping=context)
    return elements,parts


def _scope_proof(issue, previous, proof, records):
    old=records[previous['body']['model_id']];new=records[issue['body']['model_id']]
    oldscope,oldknown=footprint(old,previous['body']['affected'])
    newscope,newknown=footprint(new,issue['body']['affected'])
    sc=proof['scope_check']
    require(sc['from_scope']['model_id']==old['id'] and sc['to_scope']['model_id']==new['id'],'resolution_scope_models')
    require(subset(oldscope,sc['from_scope']) and subset(newscope,sc['to_scope']),'resolution_scope_coverage')
    # The Issue must retain every currently affected use in its own affected scope.
    require(subset(sc['to_scope'],issue['body']['affected']),'resolution_affected_coverage')
    olde,oldp=index_model(old);newe,newp=index_model(new)
    oldmap={**olde,**{i:_part_value(p) for i,p in oldp.items()}}
    newmap={**newe,**{i:_part_value(p) for i,p in newp.items()}}
    oe,op=_structural_index(old);ne,np=_structural_index(new)
    oldmeaning={**oe,**op};newmeaning={**ne,**np}
    oldids=set(sc['from_scope']['element_ids']+sc['from_scope']['mapping_part_ids'])
    newids=set(sc['to_scope']['element_ids']+sc['to_scope']['mapping_part_ids'])
    pairs=sc['element_pairs'];seen=set();targets=set();unchanged=True
    for pair in pairs:
        fr=pair['from'];to=pair['to'];require(fr['model_id']==old['id'] and fr['element_id'] in oldids,'resolution_old_element')
        seen.add(fr['element_id'])
        require((to is None)==(pair['relation']=='removed'),'resolution_element_removed')
        if to is not None:
            require(to['model_id']==new['id'] and to['element_id'] in newids,'resolution_current_element')
            targets.add(to['element_id'])
            equal=json_equal(oldmap[fr['element_id']],newmap[to['element_id']])
            if pair['relation']=='unchanged':require(equal,'resolution_element_value')
            # 'unchanged' Part payload does not assert an unchanged parent row.
            # Review/hold may retain that payload claim; structural release may not.
            same_meaning=json_equal(oldmeaning[fr['element_id']],newmeaning[to['element_id']])
            unchanged &= same_meaning and fr['element_id']==to['element_id'] and pair['relation']=='unchanged'
        else:unchanged=False
    # Missing proof is permitted only in undetermined/incomplete; caller gates release.
    complete=seen==oldids and targets==newids and oldknown and newknown
    # New elements, changed rules/Parts and reverse dependencies must be considered.
    changed={i for i in newmeaning if i not in oldmeaning or not json_equal(oldmeaning[i],newmeaning[i])}
    impact=reverse_impact(new,changed&newe.keys(),changed&newp.keys())
    ie,ip=scope_sets(impact);se,sp=scope_sets(sc['to_scope'])
    independent=not (ie&se or ip&sp)
    # Do not erase surviving old impact simply by declaring a smaller target scope.
    surviving=make_scope(new['id'],set(oldscope['element_ids'])&newe.keys(),set(oldscope['mapping_part_ids'])&newp.keys())
    surviving,_=footprint(new,surviving)
    require(subset(surviving,sc['to_scope']),'resolution_surviving_impact')
    return complete,unchanged and independent,sc['to_scope']


def _human(issue,proof,records,snapshots,profiles,reviews):
    ev=proof['evaluation']
    if ev['method']!='human_review':return
    decision=(reviews or {}).get(issue['id'])
    require(isinstance(decision,HumanReviewEvidence),'resolution_human_evidence_required')
    require(decision.reviewer==ev['evaluator'] and decision.assessment==proof['assessment'] and
            decision.dependency_sha256==review_digest(issue,records,snapshots,profiles),'resolution_human_evidence_binding')


def validate_resolution(issue,records,snapshots,*,events,stages,commands,profiles,reviews=None,_active=None):
    """Dispatch only after owner-profile shape validation; recursive history checks."""
    active=set() if _active is None else _active
    require(issue['id'] not in active,'resolution_history_cycle');active.add(issue['id'])
    b=issue['body'];carry=b['resolution_carry'];replacement=b['resolution_replacement']
    proof=carry if carry is not None else replacement
    require(proof is not None,'resolution_branch')
    def get(i,typ):
        r=records.get(i);require(r is not None and r['type']==typ,'resolution_typed_history');return r
    previous=get(proof['from_issue_id'],'issue');origin=get(proof['origin_issue_id'],'issue')
    require(proof['from_issue_id']==b['supersedes_id'] and previous['body']['issue_key']==b['issue_key']==origin['body']['issue_key'],'resolution_lineage')
    require(subset(b['blocking'],b['affected']),'issue_blocking_subset')
    for name in ('answer_ids','resolution_event_refs','resolution'):
        require(json_equal(b[name],previous['body'][name]) and json_equal(b[name],origin['body'][name]),'resolution_root_preserved')
    require(origin['body']['status']=='resolved' and bool(origin['body']['answer_ids']) and bool(origin['body']['resolution_event_refs']),'resolution_direct_answer_root')
    require(not origin['body'].get('resolution_carry') and not origin['body'].get('resolution_replacement'),'resolution_direct_root')
    shape(origin,profile=profiles[origin['id']]);validate_direct(origin,records,events)
    pb=previous['body'];pp=pb.get('resolution_carry') or pb.get('resolution_replacement')
    if previous['id']!=origin['id']:
        require(profiles[previous['id']]==E1 and pp is not None and pp['origin_issue_id']==origin['id'],'resolution_predecessor_chain')
        validate_resolution(previous,records,snapshots,events=events,stages=stages,commands=commands,profiles=profiles,reviews=reviews,_active=active)
    result=_publication(issue,proof,records,commands,events)
    ev=proof['evaluation']
    require(ev['rule_version']=='s02-rules/a1a2-v1','resolution_rule_version')
    for i in ev['evidence_record_ids']:
        r=records.get(i);require(r is not None,'resolution_evidence_exists')
        # Evidence may be the declared base, current model, root or predecessor;
        # analysis evidence with a model pin must be current or the pinned base.
        require(r['body'].get('model_id',b['model_id']) in (b['model_id'],pb['model_id']),'resolution_evidence_version')
    _human(issue,proof,records,snapshots,profiles,reviews)
    scope_complete,scope_unchanged,hold=_scope_proof(issue,previous,proof,records)
    basis,_,_=source_basis(previous,records,snapshots,events)
    origin_basis,_,_=source_basis(origin,records,snapshots,events);basis|=origin_basis
    oldsid=records[records[pb['model_id']]['body']['source_context_id']]['body']['snapshot_id']
    newsid=records[records[b['model_id']]['body']['source_context_id']]['body']['snapshot_id']
    current_basis,_,_=source_basis(issue,records,snapshots,events)
    current_basis={r for r in current_basis if r[0]==newsid}
    if carry is not None:
        require(pb.get('resolution_replacement') is None,'carry_after_replacement')
        require(not pp or pp['assessment']!='not_applicable','carry_obsolete_requires_replacement')
        seen=set();targets=set();equal=True;relations={}
        for c in carry['source_checks']:
            key=_refkey(c['from_ref']);to=c['to_ref']
            require(key in basis,'carry_source_basis');seen.add(key)
            relations.setdefault(key,set()).add(c['relation']=='removed')
            require(len(relations[key])==1,'carry_contradictory_correspondence')
            require((to is None)==(c['relation']=='removed'),'carry_removed_source')
            if to is not None:
                require(to['snapshot_id']==newsid,'carry_current_source');targets.add(_refkey(to))
                same=json_equal(resolve_pointer(snapshots[key[0]]['input'],key[1]),resolve_pointer(snapshots[newsid]['input'],to['input_pointer']))
                if c['relation']=='equal_value':require(same,'carry_equal_value')
                equal &= same and c['relation']=='equal_value' and key==_refkey(to)
            else:equal=False
        complete=seen==basis and current_basis<=targets and scope_complete
        applicable=carry['assessment']=='applicable'
        require(b['status']==('resolved' if applicable else 'resolution_pending_revalidation'),'carry_status')
        if ev['method']=='structural_check':
            require(carry['assessment']!='not_applicable','carry_method_assessment')
            if applicable:
                require(oldsid==newsid and pb['status']=='resolved' and complete and equal and scope_unchanged,'carry_structural_proof')
        if applicable:require(complete and bool(ev['evidence_record_ids']),'carry_complete_proof')
        if applicable:require(not any(scope_sets(b['blocking'])),'carry_release_blocking')
        else:require(subset(hold,b['blocking']) and any(scope_sets(b['blocking'])),'carry_revalidation_hold')
    else:
        validate_replacement(issue,previous,origin,proof,result,records,snapshots,events,profiles,
                             basis,current_basis,scope_complete,scope_unchanged,hold,oldsid,newsid)
    active.remove(issue['id'])


def _removed_source(old_ref, current_snapshot, snapshots):
    """A human removal assertion may not contradict unchanged source values.
    Requirement IDs survive array reordering; criterion equality alone never
    supplies a correspondence, but it can refute a claim of removal.
    """
    old=resolve_pointer(snapshots[old_ref['snapshot_id']]['input'],old_ref['input_pointer'])
    match=re.fullmatch(r'/(functional_requirements|non_functional_requirements|constraints)/(0|[1-9][0-9]*)(?:/acceptance_criteria/(0|[1-9][0-9]*))?',old_ref['input_pointer'])
    if match:
        previous=snapshots[old_ref['snapshot_id']]['input'][match[1]][int(match[2])]
        for requirement in current_snapshot['input'][match[1]]:
            if requirement['id']==previous['id']:
                if match[3] is None:require(not json_equal(old,requirement),'replacement_removed_source_unchanged')
                else:require(not any(json_equal(old,c) for c in requirement['acceptance_criteria']),'replacement_removed_criterion_present')
    else:
        try:new=resolve_pointer(current_snapshot['input'],old_ref['input_pointer'])
        except (KeyError,IndexError,ValueError):return
        require(not json_equal(old,new),'replacement_removed_source_unchanged')


def _task_current_scope(scope, issue, records):
    """Transport the immutable task through explicit, validated lineage proofs.

    Same IDs or evidence IDs are not correspondence. Every old member needs a
    nonremoved pair at every model transition; split mappings retain all targets.
    Missing/removal correspondence cannot establish task completion.
    """
    current=issue['body']['model_id']
    if scope['model_id']==current:return scope
    transitions={};cursor=issue;visited=set()
    while cursor['id'] not in visited:
        visited.add(cursor['id']);body=cursor['body']
        proof=body.get('resolution_replacement') or body.get('resolution_carry')
        if proof is None:break
        sc=proof['scope_check'];old=sc['from_scope']['model_id'];new=sc['to_scope']['model_id']
        if old!=new:transitions[old,new]=sc['element_pairs']
        cursor=records[proof['from_issue_id']]
    chain=[];mid=current;visited=set()
    while mid!=scope['model_id']:
        require(mid is not None and mid not in visited,'replacement_task_model_lineage');visited.add(mid)
        parent=records[mid]['body']['parent_model_id'];chain.append((parent,mid));mid=parent
    transported=scope
    for old,new in reversed(chain):
        pairs=transitions.get((old,new),[]);oldmaps=index_model(records[old]);newmaps=index_model(records[new])
        mapped=[]
        for ids,oldmap,newmap in zip(scope_sets(transported),oldmaps,newmaps):
            targets=set()
            for identity in ids:
                matches=[p for p in pairs if p['from']==dict(model_id=old,element_id=identity)]
                require(bool(matches) and all(p['to'] is not None for p in matches),'replacement_task_correspondence')
                for pair in matches:
                    to=pair['to'];require(identity in oldmap and to['model_id']==new and to['element_id'] in newmap,'replacement_task_correspondence')
                    targets.add(to['element_id'])
                # A surviving obligation cannot disappear via a renamed pair.
                if identity in newmap:targets.add(identity)
            mapped.append(targets)
        transported=make_scope(new,*mapped)
    return transported


def _target_footprint_unchanged(previous, current, records):
    """Structural identity correspondence covers target scopes AND their impact.

    Model pins may change, but member sets and exact referenced values must not.
    Any changed/renamed member needs the human-review branch instead.
    """
    old=records[previous['model_id']];new=records[current['model_id']]
    oldmaps=_structural_index(old);newmaps=_structural_index(new)
    for field in ('affected','blocking'):
        if scope_sets(previous[field])!=scope_sets(current[field]):return False
        before,oldknown=footprint(old,previous[field]);after,newknown=footprint(new,current[field])
        if not oldknown or not newknown or scope_sets(before)!=scope_sets(after):return False
        for ids,oldmap,newmap in zip(scope_sets(before),oldmaps,newmaps):
            if any(i not in newmap or not json_equal(oldmap[i],newmap[i]) for i in ids):return False
    return True


def validate_replacement(issue,previous,origin,proof,result,records,snapshots,events,profiles,
                         basis,current_basis,scope_complete,scope_unchanged,hold,oldsid,newsid):
    b=issue['body'];pb=previous['body'];ev=proof['evaluation']
    obsolete=records[proof['obsolete_issue_id']];ob=obsolete['body'];oc=ob.get('resolution_carry')
    require(obsolete['type']=='issue' and oc is not None and oc['assessment']=='not_applicable' and
            oc['evaluation']['method']=='human_review' and oc['origin_issue_id']==origin['id'],'replacement_obsolete')
    ancestor=previous['id'];seen=set()
    while ancestor!=obsolete['id']:
        require(ancestor is not None and ancestor not in seen,'replacement_obsolete_ancestor');seen.add(ancestor)
        old=records[ancestor]['body'];rp=old.get('resolution_replacement')
        require(rp is not None and rp['obsolete_issue_id']==obsolete['id'],'replacement_obsolete_fixed')
        ancestor=old['supersedes_id']
    target=records[proof['replacement_issue_id']];tb=target['body']
    require(target['type']=='issue' and target['id'] in result['issue_ids'] and tb['model_id']==b['model_id'] and tb['issue_key']!=b['issue_key'],'replacement_current_target')
    # No target chains/cycles, even for an incomplete replacement.
    require(tb.get('resolution_replacement') is None,'replacement_target_chain')
    seen=set();targets=set();removed=False;dispositions={}
    for c in proof['obligation_checks']:
        key=_refkey(c['old_ref']);to=c['current_ref']
        require(key in basis,'replacement_obligation_basis');seen.add(key)
        dispositions.setdefault(key,set()).add(c['disposition'])
        require(len(dispositions[key])==1,'replacement_contradictory_disposition')
        require((to is None)==(c['disposition']=='removed'),'replacement_removed_obligation')
        require(bool(c['evidence_record_ids']),'replacement_obligation_evidence')
        for i in c['evidence_record_ids']:
            r=records.get(i);require(r is not None and (r['body'].get('model_id')==b['model_id'] or i==b['model_id']),'replacement_current_evidence')
        if to is None:
            removed=True
            require(c['old_ref']['snapshot_id']!=newsid,'replacement_removal_source_revision')
            _removed_source(c['old_ref'],snapshots[newsid],snapshots)
        else:
            require(to['snapshot_id']==newsid,'replacement_current_source');targets.add(_refkey(to))
    complete=proof['assessment']=='complete'
    require(b['status']==('resolution_replaced' if complete else 'resolution_pending_revalidation'),'replacement_status')
    if not complete:
        require(subset(hold,b['blocking']) and any(scope_sets(b['blocking'])),'replacement_revalidation_hold');return
    require(tb['status']=='resolved' and (tb.get('resolution_carry') is None or tb['resolution_carry']['assessment']=='applicable'),'replacement_target_resolved')
    targetbasis,_,_=source_basis(target,records,snapshots,events)
    require(seen==basis and current_basis<=targets | (targetbasis if removed and ev['method']=='human_review' else set()) and scope_complete,'replacement_full_coverage')
    require(targets<=targetbasis and subset(hold,tb['affected']),'replacement_target_coverage')
    require(bool(ev['evidence_record_ids']) and not any(scope_sets(b['blocking'])),'replacement_complete_evidence')
    # Every relevant historical task requires current-model completion evidence.
    modelid=b['model_id'];visited=set()
    attestations=[]
    for i in ev['evidence_record_ids']:
        r=records[i]
        if r['type']=='validation':
            require(r['body']['model_id']==b['model_id'] and r['body']['analysis_set_id'] in
                    [i for i,r in records.items() if r['type']=='analysis_set' and r['body']==result],'replacement_attestation_selection')
            attestations.extend(r['body']['completed_change_tasks'])
    while modelid is not None:
        require(modelid not in visited,'replacement_model_cycle');visited.add(modelid)
        model=records[modelid]['body'];cid=model['change_id']
        if cid:
            for index,task in enumerate(records[cid]['body']['reevaluate']):
                # Unknown correspondence across snapshots conservatively retains tasks.
                relevant=task['scope']['model_id']!=b['model_id'] or any(x&y for x,y in zip(scope_sets(task['scope']),scope_sets(hold)))
                if not relevant:continue
                proofs=[a for a in attestations if a['change_id']==cid and a['task_index']==index]
                evidence=list(task['evidence_record_ids']) if task['status']=='completed' and task['scope']['model_id']==b['model_id'] else []
                evidence+= [i for a in proofs for i in a['evidence_record_ids']]
                require(bool(evidence),'replacement_task_attestation')
                task_scope=_task_current_scope(task['scope'],issue,records)
                for i in evidence:
                    r=records.get(i);require(r is not None and r['body'].get('model_id')==b['model_id'],'replacement_task_evidence')
                    sc=r['body'].get('scope',r['body'].get('affected'))
                    require(sc is not None and subset(task_scope,sc),'replacement_task_scope')
        modelid=model['parent_model_id']
    if ev['method']=='structural_check':
        pp=pb.get('resolution_replacement')
        require(pp is not None and pp['assessment']=='complete' and oldsid==newsid and scope_unchanged,'replacement_structural_continuation')
        if removed:
            def obligations(p):return [{k:c[k] for k in ('old_ref','current_ref','disposition')} for c in p['obligation_checks']]
            require(json_equal(obligations(pp),obligations(proof)),'replacement_removal_continuation')
        oldtarget=records[pp['replacement_issue_id']]
        # Follow current target's same-key lineage; never auto-follow a new key.
        require(oldtarget['body']['issue_key']==tb['issue_key'],'replacement_target_key_changed')
        ancestor=target['id'];visited=set()
        while ancestor!=oldtarget['id']:
            require(ancestor is not None and ancestor not in visited,'replacement_target_lineage');visited.add(ancestor)
            ancestor=records[ancestor]['body']['supersedes_id']
        require(_target_footprint_unchanged(oldtarget['body'],tb,records),'replacement_target_footprint')
        # Scope pins/sets were checked separately; all other meaning must agree.
        def meaning(body):return {k:v for k,v in body.items() if k not in ('model_id','supersedes_id','resolution_carry','resolution_replacement','affected','blocking')}
        require(json_equal(meaning(oldtarget['body']),meaning(tb)),'replacement_target_meaning')
