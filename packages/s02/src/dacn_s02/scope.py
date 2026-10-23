"""Finite fixed-point scope algebra (§9.1), not a business review workflow."""
from dataclasses import dataclass
from .errors import S02Error, require
from .profiles import L1, blocking_statuses
from .validation import COLLECTIONS, index_model, scope_sets, subset


def make_scope(model_id, elements=(), parts=()):
    return dict(model_id=model_id,element_ids=sorted(elements),mapping_part_ids=sorted(parts))

@dataclass(frozen=True)
class Closure:
    scope: dict
    action_ids: frozenset
    reasons: tuple


def closure(model, seed, choices=()):
    """Input must be a structurally validated Model, not a docs graph wrapper.

    All actions of *every* discovered part are queued. Support context never
    expands through all actions of a responsibility/component/interface.
    """
    b=model["body"];mid=model["id"];elements,parts=index_model(model)
    require(seed["model_id"]==mid,"scope_model")
    require(set(seed["element_ids"])<=elements.keys() and set(seed["mapping_part_ids"])<=parts.keys(),"scope_members")
    actions={a["id"]:a for a in b["actions"]};workflows={w["id"]:w for w in b["workflows"]}
    responsibilities={r["id"]:r for r in b["responsibilities"]}
    selected={};reasons=set()
    for c in choices:
        w=workflows.get(c["workflow_id"]);require(w is not None,"choice_workflow")
        point=next((p for p in w["branch_points"] if p["node_id"]==c["node_id"]),None)
        if point is None or point["mode"]!="exclusive":
            raise S02Error("SCOPE_UNDETERMINED","review","Branch cannot be narrowed",details={"scope":seed,"reason":"Choice requires an exclusive branch"})
        require((w["id"],c["node_id"]) not in selected,"choice_unique")
        require(any(e["id"]==c["edge_id"] and e["from"]==c["node_id"] for e in w["edges"]),"choice_outgoing")
        selected[w["id"],c["node_id"]]=c["edge_id"]
    aa=set(seed["element_ids"])&actions.keys();pp=set(seed["mapping_part_ids"])
    ee=set(seed["element_ids"]);done_a=set();done_p=set();done_w=set();done_r=set();done_support=set()
    if aa or any(parts[p]["action_ids"] for p in pp): pp.update(p["id"] for p in parts.values() if p["target"]=="system")
    reachable={}
    while True:
        before=(frozenset(aa),frozenset(pp),frozenset(ee))
        for pid in sorted(pp-done_p):
            p=parts[pid]
            aa.update(p["action_ids"])
            ee.update(p["primary_responsibility_ids"]+p["supporting_responsibility_ids"])
            done_p.add(pid)  # Only after *all* actions have entered the work set.
        for aid in sorted(aa-done_a):
            a=actions[aid];ee.add(aid)
            ee.update(a["rule_ids"]+a["permission_rule_ids"]+a["workflow_ids"])
            ee.update(r["id"] for r in b["rules"] if aid in r["action_ids"])
            matching=[p["id"] for p in parts.values() if p["target"]=="components" and aid in p["action_ids"]]
            if not matching: reasons.add("ACTION_WITHOUT_PART")
            pp.update(matching);done_a.add(aid)
        for wid in sorted((ee&workflows.keys())-done_w):
            w=workflows[wid];nodes={n["id"]:n for n in w["nodes"]};todo=[w["entry_node_id"]];visited=set();found=set()
            while todo:
                nid=todo.pop()
                if nid in visited: continue
                visited.add(nid);node=nodes[nid]
                if node["action_id"]: found.add(node["action_id"])
                chosen=selected.get((wid,nid))
                todo.extend(e["to"] for e in w["edges"] if e["from"]==nid and (chosen is None or e["id"]==chosen))
            reachable[wid]=found;aa.update(found);done_w.add(wid)
        for r in sorted((ee&responsibilities.keys())-done_r):
            rr=responsibilities[r];ee.add(rr["component_id"]);ee.update(rr["rule_ids"]);done_r.add(r)
        for d in b["dependencies"]:
            triggered=aa&set(d["action_ids"])
            if not d["action_ids"] and set(d["workflow_ids"])&done_w:
                triggered={n["action_id"] for wid in set(d["workflow_ids"])&done_w for n in workflows[wid]["nodes"] if n["action_id"] in aa}
            for aid in sorted(triggered):
                if (d["id"],aid) in done_support: continue
                support=next((s for s in d["support"] if s["action_id"]==aid),None)
                require(support is not None,"dependency_support_inventory")
                ee.update((d["id"],d["consumer_component_id"],d["provider_component_id"]))
                if d["interface_id"]: ee.add(d["interface_id"])
                ee.update(support["provider_responsibility_ids"])
                if support["required_action_ids"] is None: reasons.add("SCOPE_UNDETERMINED")
                else: aa.update(support["required_action_ids"])
                done_support.add((d["id"],aid))
        if before==(frozenset(aa),frozenset(pp),frozenset(ee)) and done_a==aa and done_p==pp: break
    for aid in aa:
        for wid in actions[aid]["workflow_ids"]:
            if aid not in reachable[wid]: reasons.add("SCOPE_UNDETERMINED")
    require(all(set(parts[p]["action_ids"])<=aa for p in pp),"closed_part_actions")
    return Closure(make_scope(mid,ee,pp),frozenset(aa),tuple(sorted(reasons)))


def permitted_scope(model, requested, accepted, *, current_analysis_set_id, reviewed_analysis_set_id,
                    issues=(), pending_tasks=(), conditions=(), choices=(), profile=L1):
    """Pure gate result. Does not create Review/Handoff or prove renderer gates.

    Caller supplies current selected Issues and checked task attestations. The
    repository separately enforces pinned model/set freshness on publication.
    """
    mid=model["id"];elements,parts=index_model(model)
    empty=make_scope(mid)
    actionids={a["id"] for a in model["body"]["actions"]}
    # Report blocked uses as actions/obligations, as in draft.3 file08.
    # An unselected supporting node or a source-only actor is not itself a use.
    allscope=make_scope(mid,actionids,parts)
    if accepted["model_id"]!=mid or reviewed_analysis_set_id!=current_analysis_set_id:
        return dict(allowed_scope=empty,blocked_scope=allscope,reason_codes=["ANALYSIS_STALE"],closures=[])
    # Structurally valid intermediate mappings may have no Parts. Their
    # applicability is still unknown, not an empty (therefore waived) obligation.
    # Applies to every requirement AND criterion row, independently of priority.
    if any(not row['parts'] or row['assessment']!='proposed' for row in model['body']['mappings']):
        return dict(allowed_scope=empty,blocked_scope=allscope,
                    reason_codes=['MAPPING_NOT_ASSESSED','NO_ALLOWED_FUNCTIONAL_SCOPE'],closures=[])
    seeds=set(requested["mapping_part_ids"])
    seeds.update(p["id"] for p in parts.values() if set(p["action_ids"])&set(requested["element_ids"])&actionids)
    seeds={i for i in seeds if parts[i]["target"]=="components" and parts[i]["action_ids"]}
    allowed_e=set();allowed_p=set();reasons=set();out=[]
    def gate(c):
        failures=set(c.reasons);es,ps=scope_sets(c.scope)
        if not subset(c.scope,accepted): failures.add("UNREVIEWED_SCOPE")
        if not c.action_ids: failures.add("NO_FUNCTIONAL_SCOPE")
        if any(parts[p]["assignment"]!="proposed" for p in ps): failures.add("BLOCKED_SCOPE")
        if any(elements[e]["state"] in ("needs_clarification","needs_reanalysis") for e in es): failures.add("NEEDS_REANALYSIS")
        blocked=[i["body"]["blocking"] for i in issues if i["body"]["status"] in blocking_statuses(profile)]
        blocked += [t["scope"] for t in pending_tasks if t["status"]=="pending"]
        blocked += [c["scope"] for c in conditions if c["blocking"]]
        for s in blocked:
            require(s["model_id"]==mid,"blocker_model")
            se,sp=scope_sets(s)
            if es&se or ps&sp: failures.add("BLOCKED_SCOPE")
        return failures
    for seed in sorted(seeds):
        c=closure(model,make_scope(mid,parts=[seed]),choices);fail=gate(c)
        out.append(dict(seed=seed,scope=c.scope,reasons=sorted(fail)))
        if fail: reasons.update(fail)
        else:
            es,ps=scope_sets(c.scope);allowed_e.update(es);allowed_p.update(ps)
    if allowed_p:
        final=closure(model,make_scope(mid,allowed_e,allowed_p),choices);fail=gate(final)
        if fail: reasons.update(fail);allowed_e.clear();allowed_p.clear()
        else: allowed_e,allowed_p=scope_sets(final.scope)
    if not allowed_p: reasons.add("NO_ALLOWED_FUNCTIONAL_SCOPE")
    return dict(allowed_scope=make_scope(mid,allowed_e,allowed_p),
                blocked_scope=make_scope(mid,actionids-allowed_e,parts.keys()-allowed_p),
                reason_codes=sorted(reasons),closures=out)


def reverse_impact(model, changed_elements, changed_parts):
    """Conservative reverse closure; unknown branch/support => entire model."""
    es,ps=index_model(model);affected_e=set(changed_elements);affected_p=set(changed_parts)
    for pid,p in ps.items():
        if p["target"]!="components": continue
        c=closure(model,make_scope(model["id"],parts=[pid]))
        if c.reasons: return make_scope(model["id"],es,ps)
        ce,cp=scope_sets(c.scope)
        if ce&set(changed_elements) or cp&set(changed_parts): affected_e.update(ce);affected_p.update(cp)
    return make_scope(model["id"],affected_e,affected_p)
