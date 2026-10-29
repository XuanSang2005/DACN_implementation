"""Private H2 checkpoint metadata and checked code-owned selectors."""
from copy import deepcopy
from dataclasses import asdict, replace
from .codec_boundary import encode
from .errors import storage_error
from .h2_contracts import SourceInventory, HoldSelector, ConstructionPermit, POLICY
from .h2_graph import ModelContext, semantic
from .h2_limits import digest, need

HANDLER = 's02-2a-h2-b/0.7.0a2'
CONFIG = 's02-h2-config/0.1.0-draft.2'
PLAN = 's02-h2-plan/0.1.0-draft.2'
ADMISSION = 's02-h2-admission/0.1.0-draft.2'


def source_inventory(view, budget):
    context = view['state']['records'][view['config']['source_context_id']]
    # verify_archive was called by WorkStore.context on this checked state.
    archive = view['state']['records'][context['body']['envelope_artifact_id']]
    return SourceInventory(view['snapshot'], context['id'], archive['body']['sha256'], budget)


def selectors(meta, issues, source, budget, *, derived=False):
    stored = meta['selectors']
    need(set(stored) == {q['body']['issue_key'] for q in issues}, 'checkpoint_selector_inventory')
    result = []
    for issue in issues:
        row = deepcopy(stored[issue['body']['issue_key']])
        need(row['issue_id'] == issue['id'], 'checkpoint_current_selector')
        # Code-derived result selectors have aggregate result bounds; they are
        # not another occurrence of caller input in the invocation counters.
        result.append(HoldSelector.parse(row, source, budget, input_lane=not derived))
    return tuple(result)


def selector(issue, source, *, role=None, target=1, unknown=False, sources=None):
    body = issue['body']
    refs = source.refs(body['trace']['source_refs']) if sources is None else frozenset(sources)
    kind = 'all_source_uses' if unknown else 'obligation_families' if refs <= source.obligations else 'explicit_uses'
    return HoldSelector(issue['id'], body['issue_key'], target, kind, refs,
                        frozenset(body['blocking']['element_ids']), frozenset(body['blocking']['mapping_part_ids']), not unknown, role)


def pack(value):
    """Deterministic JSON projection of policy results, not a second policy."""
    if hasattr(value, '__dataclass_fields__'):return pack(asdict(value))
    if isinstance(value, dict):return {k:pack(v) for k,v in value.items()}
    if isinstance(value, (set,frozenset)):return sorted(pack(v) for v in value)
    if isinstance(value, (tuple,list)):return [pack(v) for v in value]
    return value


def empty_progress(source):
    return {u:dict(work_completed_through=0, outputs={}, assessment_state='pending',
                   latest_checked_pair=None, assessment=None, guard_keys=[], unresolved_keys=[], next_tasks=[1]) for u in sorted(source.units)}


def check_stage(meta, units, step, mode, goal):
    for unit in units:
        p = meta['progress_by_unit'][unit];done = int(p['work_completed_through'])
        if mode == 'step':
            need(done == step-1, 'h2_pair_already_completed_or_prerequisite_missing')
            need(p['assessment_state'] not in ('needs_revalidation','terminal_out_of_scope'), 'h2_prerequisite_not_current')
        elif goal == 'retained_output':
            need(str(step) in p['outputs'] and done >= step, 'h2_retained_output_absent')
        else:
            need(done == step-1, 'h2_admission_prerequisite')


def permits(meta, issues, units, step, origin_lookup):
    result=[]
    for issue in issues:
        key=issue['body']['issue_key'];task=meta['tasks'].get(key)
        if task is None:continue
        origin=origin_lookup(task['origin_command_id'])
        root=origin['admission']['tasks'].get(key)
        need(root == task and any(r['id']==task['root_issue_id'] and r['type']=='issue' and r['body']['issue_key']==key for r in origin['batch']['records']), 'construction_origin')
        need(task['predicate'] in ('h2.all_mapping/1','h2.unit_mapping/1','h2.unit_responsibility/1'), 'construction_predicate')
        result.append(ConstructionPermit(issue['id'], key, task['origin_command_id'], origin['bindings']['reserved_run_id'],
                       digest(origin), frozenset(task['unit_ids']), int(task['target_step']), task['role']))
    return tuple(result)


def hold_footprint(ctx, issue, hold):
    """Rematerialize a hold on either side of a checked append-only delta.

    A new candidate ID has no base counterpart. Project only absent physical
    IDs away on base; the complete selector is checked on candidate first.
    Logical source families and the closure algorithm remain unchanged.
    """
    from .h2_policy import materialize
    projected = replace(hold, elements=frozenset(hold.elements & ctx.elements.keys()),
                        parts=frozenset(hold.parts & ctx.parts.keys()))
    q = deepcopy(issue)
    q['body']['blocking']['element_ids'] = sorted(set(q['body']['blocking']['element_ids']) & ctx.elements.keys())
    q['body']['blocking']['mapping_part_ids'] = sorted(set(q['body']['blocking']['mapping_part_ids']) & ctx.parts.keys())
    return materialize(ctx, projected, q)


def blocking_keys(ctx, issues, holds, units):
    """Source and physical blockers for full unit footprints, never provenance alone."""
    need({q['id'] for q in issues} == {s.issue_id for s in holds}, 'checkpoint_hold_inventory')
    by_id = {s.issue_id:s for s in holds}
    feet = {u:ctx.closure(*ctx.source_seed(ctx.source.units[u].obligations)) for u in units}
    result = {u:[] for u in units}
    for q in issues:
        ctx.budget.check()
        if q['body']['status'] != 'open':continue
        s = by_id[q['id']];held = hold_footprint(ctx,q,s)
        refs = {p for f in ctx.source.families if f.obligations & s.sources for p in f.obligations}
        for u,foot in feet.items():
            ctx.budget.check()
            if (s.kind == 'all_source_uses' or not s.impact_known or
                ctx.source.units[u].obligations & refs or foot.source_uses & refs or
                foot.elements & s.elements or foot.parts & s.parts or
                foot.uses & held.uses or foot.active_parts & held.active_parts):
                result[u].append(s.issue_key)
    return {u:sorted(keys) for u,keys in result.items()}


def normalized_model(model, issues):
    """Only code-owned current Issue IDs and Model revision envelope normalized."""
    keys={q['id']:q['body']['issue_key'] for q in issues}
    def walk(v):
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {k:sorted(keys.get(i,i) for i in x) if k=='issue_ids' else walk(x) for k,x in v.items()}
        return v
    body=walk(deepcopy(model['body']))
    for key in ('revision','parent_model_id','change_id','created_by_run_id'):body.pop(key)
    return semantic(body)
