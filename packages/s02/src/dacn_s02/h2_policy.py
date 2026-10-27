"""Pure H2 admission/materialization/merge checks. Never creates domain Records."""
from dataclasses import dataclass
from hashlib import sha256
from .codec_boundary import encode
from .profiles import E1
from .validation import shape
from .h2_contracts import (AuthorityGrant, AuthorityContext, BindingRequest, AnalysisEvidence, ConstructionPermit,
                           HoldSelector, selectors_hash)
from .h2_graph import Footprint, impact, semantic
from .h2_limits import digest, need


@dataclass(frozen=True)
class Admission:
    allowed_units: tuple
    blocked_units: tuple
    global_blocked: bool
    reason_codes: tuple
    footprint: Footprint
    unit_reasons: tuple
    materialized_holds: tuple
    outcome: str = 'assessed'


def _empty_result(ctx, units, reason, outcome='assessed'):
    return Admission((), tuple(sorted(units)), True, (reason,), ctx.closure(),
                     tuple((u, (reason,)) for u in sorted(units)), (), outcome)


def _current(ctx, aset, issues, selectors):
    shape(aset, profile=E1)
    need(aset['type'] == 'analysis_set' and aset['body']['model_id'] == ctx.id, 'current_analysis_model')
    ctx.budget.cap('issues', len(issues))
    _aggregate(ctx, issues)
    need(len({q['id'] for q in issues}) == len(issues) and set(aset['body']['issue_ids']) == {q['id'] for q in issues}, 'current_issue_inventory')
    need(len({q['body']['issue_key'] for q in issues}) == len(issues), 'current_issue_keys')
    need(all(type(s) is HoldSelector for s in selectors) and {s.issue_id for s in selectors} == {q['id'] for q in issues}, 'selector_issue_inventory')
    by_id = {s.issue_id: s for s in selectors}
    need(len(by_id) == len(selectors), 'selector_unique')
    for q in issues:
        shape(q, profile=E1)
        b = q['body'];s = by_id[q['id']]
        need(q['type'] == 'issue' and b['model_id'] == ctx.id and b['issue_key'] == s.issue_key, 'selector_issue_binding')
        need(b['status'] in ('open', 'resolved') and not b['answer_ids'] and b['resolution_carry'] is None and b['resolution_replacement'] is None, 'historical_answer_a2_out_of_scope')
        for name in ('affected', 'blocking'):
            need(b[name]['model_id'] == ctx.id and set(b[name]['element_ids']) <= ctx.elements.keys() and set(b[name]['mapping_part_ids']) <= ctx.parts.keys(), 'issue_current_scope')
        need(set(b['blocking']['element_ids']) <= set(b['affected']['element_ids']) and set(b['blocking']['mapping_part_ids']) <= set(b['affected']['mapping_part_ids']), 'issue_blocking_subset')
        need(set(b['blocking']['element_ids']) <= s.elements and set(b['blocking']['mapping_part_ids']) <= s.parts, 'selector_cannot_shrink_current_blocker')
        ctx.source.refs([dict(snapshot_id=ctx.source.snapshot_id, input_pointer=p) for p in s.sources])
        trace_sources = ctx.source.refs(b['trace']['source_refs'])
        need(s.kind == 'all_source_uses' or trace_sources <= s.sources, 'selector_cannot_drop_issue_sources')
    model_refs = set()
    todo = [ctx.body]
    while todo:
        value = todo.pop()
        if type(value) is dict:
            model_refs.update(value.get('issue_ids', []))
            todo.extend(value.values())
        elif type(value) is list:
            todo.extend(value)
    need(model_refs <= by_id.keys(), 'model_issue_refs_current')
    return by_id


def _aggregate(ctx, issues):
    # Result bounds apply to the full Model plus current Issues, not just the
    # Model or the (usually much smaller) materialized work footprint.
    ctx.budget.inspect(dict(model=ctx.model(), current_issues=list(issues)))


def _pins(base, aset, selectors, binding, evidence, grant, authority_context, candidate_raw):
    need(type(binding) is BindingRequest and type(evidence) is AnalysisEvidence, 'typed_work_contracts')
    b = binding.payload();source = base.source
    source.selected(b['unit_ids'])
    expected = dict(source_context_id=source.context_id, snapshot_id=source.snapshot_id,
                    archive_sha256=source.archive_sha256, base_model_id=base.id, base_model_sha256=base.hash,
                    base_analysis_set_id=aset['id'], base_analysis_set_sha256=digest(aset),
                    current_selectors_sha256=selectors_hash(selectors, source))
    if any(b[k] != v for k, v in expected.items()) or not evidence.matches(binding):
        return 'ANALYSIS_STALE'
    base.budget.raw_work(candidate_raw, evidence.raw)
    if b['candidate_length'] != len(candidate_raw or b'') or b['candidate_sha256'] != (None if candidate_raw is None else sha256(candidate_raw).hexdigest()):
        return 'RAW_BINDING_MISMATCH'
    if type(grant) is not AuthorityGrant:
        return 'AUTHORITY_REQUIRED'
    if grant.decision in ('unavailable', 'invalid'):
        return 'AUTHORITY_' + grant.decision.upper()
    if type(authority_context) is not AuthorityContext:
        return 'AUTHORITY_CONTEXT_REQUIRED'
    if not grant.matches(binding, authority_context):
        return 'AUTHORITY_' + grant.decision.upper() if grant.decision != 'allow' else 'AUTHORITY_BINDING_MISMATCH'
    # Aggregate once as well as individual lexical guards: callers cannot evade
    # totals by parsing contracts with separate Budget instances.
    value = dict(request=b, analysis=evidence.payload(), selectors=[s.payload(source) for s in selectors])
    if candidate_raw is not None:
        from .codec_boundary import decode
        base.budget.check();value['candidate'] = base.budget.parse(candidate_raw, slot='candidate')
    base.budget.inspect(value)
    return None


def materialize(ctx, selector, issue):
    """Persistent source selector -> current physical footprint, even pre-Parts."""
    s = selector
    need(s.issue_id == issue['id'] and s.issue_key == issue['body']['issue_key'], 'materialize_issue_binding')
    need(set(issue['body']['blocking']['element_ids']) <= s.elements and set(issue['body']['blocking']['mapping_part_ids']) <= s.parts, 'materialize_current_blocker')
    if s.kind == 'all_source_uses' or not s.impact_known:
        return ctx.closure(ctx.elements, ctx.parts)
    sources = set(s.sources)
    if s.kind == 'obligation_families':
        sources = {p for f in ctx.source.families if f.obligations & sources for p in f.obligations}
    e, p = ctx.source_seed(sources)
    e.update(s.elements);p.update(s.parts)
    return ctx.closure(e, p)


def _evaluate(base, ctx, aset, issues, selectors, binding, evidence, grant, candidate_raw, phase, permits, authority_context):
    need(phase in ('before', 'post'), 'admission_phase')
    need(base.budget is ctx.budget, 'shared_invocation_budget')
    by_id = _current(base, aset, issues, selectors)
    b = binding.payload();units = frozenset(b['unit_ids']);step = b['step']
    pin_error = _pins(base, aset, selectors, binding, evidence, grant, authority_context, candidate_raw)
    if pin_error:
        return _empty_result(ctx, units, pin_error)
    source = ctx.source
    need(all(type(p) is ConstructionPermit and p.unit_ids <= source.units.keys() and (p.role != 'global_mapping' or p.unit_ids == source.units.keys()) for p in permits), 'checked_construction_permits')
    need(source.context_id == base.source.context_id and source.snapshot_hash == base.source.snapshot_hash, 'same_source_only')
    budget = ctx.budget
    reasons = {u: set() for u in units}
    rows = {r['source_ref']['input_pointer']: r for r in ctx.rows.values()}
    active = []
    materialized = []
    result_refs = 0
    for q in issues:
        budget.check();s = by_id[q['id']]
        need(s.elements <= ctx.elements.keys() and s.parts <= ctx.parts.keys(), 'hold_projection_members')
        held = materialize(ctx, s, q)
        result_refs += 2 + len(held.elements) + len(held.parts) + len(held.actions)
        budget.cap('refs', result_refs)
        materialized.append((s.issue_key, held))
        if q['body']['status'] == 'open':
            active.append((q, s))
    held_inspections = {p for p, row in evidence.inspections.items() if row['verdict'] == 'held' or row['read'] != 'inspected'}
    # Unrepresented/unknown obligations cannot silently have no current hold.
    represented = set()
    for _, s in active:
        if s.kind == 'all_source_uses':
            represented.update(source.obligations)
        else:
            represented.update(p for f in source.families if f.obligations & s.sources for p in f.obligations)
    unheld = held_inspections - represented
    footprints = {}
    seeds = {}
    seed_e = set();seed_p = set()
    for u in sorted(units):
        budget.check();refs = source.units[u].obligations
        es, ps = ctx.source_seed(refs)
        seeds[u] = es, ps
        seed_e.update(es);seed_p.update(ps)
        c = ctx.closure(es, ps);footprints[u] = c
        rr = reasons[u]
        if unheld:
            rr.add('SOURCE_HOLD_MISSING')
        if refs & held_inspections:
            rr.add('OBLIGATION_HELD')
        if any(v['read'] != 'inspected' for v in evidence.inspections.values()):
            rr.add('INDEPENDENCE_INVENTORY_UNINSPECTED')
        rr.update(r for r in c.reasons if r != 'ACTION_WITHOUT_PART' or phase == 'post' and step == 4)
        if any(ctx.elements[a]['initiator'] == 'unknown' for a in c.actions):
            rr.add('INITIATOR_UNKNOWN')
        if any(ctx.parts[p]['assignment'] != 'proposed' or ctx.parts[p]['covered_portion'] is None or ctx.parts[p]['remaining_gap'] is not None for p in c.parts):
            rr.add('PART_GAP')
        if step >= 4 or phase == 'post' and step == 3:
            assigned = {a for r in ctx.maps['responsibilities'].values() for a in r['action_ids']}
            if not c.actions <= assigned:
                rr.add('UNASSIGNED_ACTION')
        if phase == 'post' and step == 4:
            for p in refs:
                row = rows[p]
                if row['assessment'] != 'proposed' or not row['parts']:
                    rr.add('MAPPING_NOT_PROPOSED')
                if any(x['assignment'] != 'proposed' or x['covered_portion'] is None or x['remaining_gap'] is not None for x in row['parts']):
                    rr.add('MAPPING_GAP')
        for q, s in active:
            if step < s.target_step:
                continue
            exempt = any(type(p) is ConstructionPermit and p.valid_for(q, s, units, step) for p in permits)
            if exempt:
                continue  # building this task, not resolving it/reviewing it
            if s.kind == 'all_source_uses' or not s.impact_known:
                rr.add('UNKNOWN_GLOBAL_HOLD');continue
            held_refs = {p for f in source.families if f.obligations & s.sources for p in f.obligations}
            if refs & held_refs or c.source_uses & s.sources or c.source_uses & held_refs or c.elements & s.elements or c.parts & s.parts:
                rr.add('BLOCKING_USE');continue
            pair = evidence.pairs.get((s.issue_key, u))
            if not pair or pair['verdict'] != 'independent' or not (refs | s.sources) <= pair['basis']:
                rr.add('INDEPENDENCE_NOT_PROVED')
    # Retain the full requested footprint, but reclose only units that passed
    # their own gates when checking permission to build. A defect in held U
    # must not be attributed to independent V merely by sharing a reason name.
    # assess_union still rejects/holds the entire built candidate atomically.
    union = ctx.closure(seed_e, seed_p)
    eligible = [u for u in units if not reasons[u]]
    permitted = ctx.closure({e for u in eligible for e in seeds[u][0]},
                            {p for u in eligible for p in seeds[u][1]})
    union_reasons = {r for r in permitted.reasons if r != 'ACTION_WITHOUT_PART' or phase == 'post' and step == 4}
    for q, s in active:
        if step < s.target_step or any(type(p) is ConstructionPermit and p.valid_for(q, s, units, step) for p in permits):
            continue
        if permitted.elements & s.elements or permitted.parts & s.parts:
            union_reasons.add('UNION_BLOCKING_USE')
    for u in eligible:
        reasons[u].update(union_reasons)
    allowed = tuple(sorted(u for u in units if not reasons[u]))
    blocked = tuple(sorted(units - set(allowed)))
    budget.cap('refs', result_refs + len(units) * 2 + 1 + len(union.elements) + len(union.parts) + len(union.actions))
    return Admission(allowed, blocked, bool(active or held_inspections or blocked),
                     tuple(sorted({r for rr in reasons.values() for r in rr})), union,
                     tuple((u, tuple(sorted(reasons[u]))) for u in sorted(units)), tuple(materialized))


def admit(ctx, aset, issues, selectors, binding, evidence, grant, *, candidate_raw=None, phase='before', permits=(), authority_context=None):
    """Assess work permission only. An allowed unit is never user_accepted."""
    need(binding.payload()['operation'] == 'step', 'pure_admit_build_only')
    return _evaluate(ctx, ctx, aset, issues, selectors, binding, evidence, grant, candidate_raw, phase, permits, authority_context)


def assess_union(base, candidate, aset, issues, selectors, binding, evidence, grant, *, candidate_raw=None, permits=(), authority_context=None):
    """Check a full built candidate, not fragments/flags from individual units.

    Append-only rights are structural. Candidate-to-builder/raw fidelity and
    CAS/Records publication remain H2-B, never claimed by this pure result.
    """
    need(binding.payload()['operation'] == 'step', 'pure_union_build_only')
    need(base.budget is candidate.budget, 'shared_invocation_budget')
    _aggregate(candidate, issues)
    units = frozenset(binding.payload()['unit_ids'])
    step = binding.payload()['step']
    selected = base.source.selected(units)
    delta = impact(base, candidate)
    if candidate.id != base.id and not (candidate.body['parent_model_id'] == base.id and candidate.body['revision'] == base.body['revision'] + 1 and candidate.body['change_id'] is not None):
        return _empty_result(candidate, units, 'MODEL_SUCCESSOR_PIN', 'rejected')
    if delta.source_changed:
        return _empty_result(candidate, units, 'SOURCE_SWITCH_OUT_OF_SCOPE', 'rejected')
    if not base.elements.keys() <= candidate.elements.keys() or not base.parts.keys() <= candidate.parts.keys() or base.rows.keys() != candidate.rows.keys():
        return _empty_result(candidate, units, 'OUTSIDE_APPEND_ONLY', 'rejected')
    if any(base.element_context[i] != candidate.element_context[i] for i in base.elements):
        return _empty_result(candidate, units, 'EXISTING_OUTPUT_EDIT', 'rejected')
    for rid, old in base.rows.items():
        new = candidate.rows[rid]
        if old['source_ref'] != new['source_ref']:
            return _empty_result(candidate, units, 'MAPPING_SOURCE_CHANGED', 'rejected')
        if semantic(old) != semantic(new) and (old['assessment'] != 'not_assessed' or old['parts'] or old['source_ref']['input_pointer'] not in selected):
            return _empty_result(candidate, units, 'MAPPING_CONTEXT_EDIT', 'rejected')
    for i in candidate.elements.keys() - base.elements.keys():
        refs = candidate.sources_in(candidate.elements[i])
        if not refs or not refs <= selected:
            return _empty_result(candidate, units, 'OUTSIDE_WRITE_SOURCES', 'rejected')
    result = _evaluate(base, candidate, aset, issues, selectors, binding, evidence, grant, candidate_raw, 'post', permits, authority_context)
    # Read permission and source provenance do not authorize changing the
    # meaning of an existing action outside the base work footprint. Pin this
    # boundary to base, so a new Part/workflow cannot authorize its own bridge.
    es, ps = base.source_seed(selected)
    writable = base.closure(es, ps)
    affected_uses = (delta.before.uses | delta.after.uses) & base.elements.keys()
    affected_actions = (delta.before.actions | delta.after.actions) & base.maps['actions'].keys()
    affected_parts = (delta.before.active_parts | delta.after.active_parts) & base.parts.keys()
    outside = not (affected_uses <= writable.uses and affected_actions <= writable.actions and affected_parts <= writable.active_parts)
    impact_reasons = {'IMPACT_OUTSIDE_WRITE_SCOPE'} if outside else set()
    for footprint in (delta.before, delta.after):
        impact_reasons.update('IMPACT_' + r for r in footprint.reasons if r != 'ACTION_WITHOUT_PART' or step == 4)
    for q, s in ((q, s) for q in issues for s in selectors if s.issue_id == q['id']):
        if q['body']['status'] != 'open' or step < s.target_step or any(type(p) is ConstructionPermit and p.valid_for(q, s, units, step) for p in permits):
            continue
        for ctx, footprint in ((base, delta.before), (candidate, delta.after)):
            held = materialize(ctx, s, q)
            if footprint.elements & s.elements or footprint.parts & s.parts or footprint.uses & held.uses or footprint.active_parts & held.active_parts:
                impact_reasons.add('IMPACT_BLOCKING_USE')
    if result.blocked_units or impact_reasons:
        rr = impact_reasons | {'UNION_NOT_ADMITTED'}
        return Admission((), tuple(sorted(units)), True, tuple(sorted(set(result.reason_codes) | rr)), result.footprint,
                         tuple((u, tuple(sorted(set(r) | rr))) for u, r in result.unit_reasons),
                         result.materialized_holds, 'rejected' if outside and not result.blocked_units else 'guard_required')
    return result
