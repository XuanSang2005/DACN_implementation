"""H2 context identity and fixed points, isolated from legacy scope helpers."""
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from .codec_boundary import encode
from .profiles import E1
from .scope import make_scope
from .validation import COLLECTIONS, shape
from .h2_limits import digest, need


SET_FIELDS = frozenset(('source_refs', 'parts', *COLLECTIONS))


def semantic(value, field=''):
    """Only declared sets reorder. Workflow nodes/edges and criteria stay ordered."""
    if type(value) is dict:
        return {k: semantic(v, k) for k, v in value.items()}
    if type(value) is list:
        values = [semantic(v) for v in value]
        if field.endswith('_ids') or field in SET_FIELDS:
            return sorted(values, key=encode)
        return values
    return value


@dataclass(frozen=True)
class Footprint:
    model_id: str
    elements: frozenset
    parts: frozenset
    actions: frozenset
    uses: frozenset
    active_parts: frozenset
    source_uses: frozenset
    reasons: tuple

    def scope(self):
        return make_scope(self.model_id, self.elements, self.parts)


class ModelContext:
    """Detached index of a caller's checked E1 Model and checked S01 inventory.

    Shape/local refs/source inventory are guarded here. Run/Change/history/profile
    ownership and checked lookup remain the existing whole-graph verifier's job.
    """
    def __init__(self, model, source, budget):
        self.budget = budget
        self.source = source
        budget.inspect(model)
        shape(model, profile=E1)
        need(model['type'] == 'model' and model['body']['source_context_id'] == source.context_id, 'model_source')
        self._model = deepcopy(model)
        self.id = model['id']
        self.hash = digest(model)
        self.body = self._model['body']
        self.maps = {k: {v['id']: v for v in self.body[k]} for k in COLLECTIONS}
        self.elements = {v['id']: v for k in COLLECTIONS for v in self.body[k]}
        self.kinds = {v['id']: k for k in COLLECTIONS for v in self.body[k]}
        self.rows = {r['id']: r for r in self.body['mappings']}
        self.parts = {p['id']: p for r in self.body['mappings'] for p in r['parts']}
        self.part_rows = {p['id']: r for r in self.body['mappings'] for p in r['parts']}
        all_ids = [x['id'] for k in COLLECTIONS for x in self.body[k]] + [r['id'] for r in self.body['mappings']] + [p['id'] for r in self.body['mappings'] for p in r['parts']]
        all_ids += [x['id'] for w in self.body['workflows'] for k in ('nodes', 'edges') for x in w[k]]
        need(len(all_ids) == len(set(all_ids)), 'graph_ids_unique')
        budget.cap('entities', len(self.elements));budget.cap('parts', len(self.parts))
        budget.cap('nodes', sum(len(w['nodes']) for w in self.body['workflows']))
        budget.cap('edges', sum(len(w['edges']) for w in self.body['workflows']))
        self.source_elements = defaultdict(set)
        self.source_parts = defaultdict(set)
        self.action_parts = defaultdict(set)
        self.action_rules = defaultdict(set)
        self.action_support = defaultdict(list)
        for i, e in self.elements.items():
            budget.check()
            for ptr in self.sources_in(e):
                self.source_elements[ptr].add(i)
        row_sources = []
        for row in self.body['mappings']:
            ptr = source.source(row['source_ref'], obligation=True)
            row_sources.append(ptr)
            need(row['parts'] or row['assessment'] == 'not_assessed' and row['issue_ids'], 'unassessed_row_issue')
            for p in row['parts']:
                self.source_parts[ptr].add(p['id'])
                for a in p['action_ids']:
                    self.local(a, 'actions');self.action_parts[a].add(p['id'])
                for r in p['primary_responsibility_ids'] + p['supporting_responsibility_ids']:
                    self.local(r, 'responsibilities')
                need(p['target'] != 'system' or not p['action_ids'], 'system_part_actions')
        need(len(row_sources) == len(set(row_sources)) and set(row_sources) == source.obligations, 'graph_full_mapping_inventory')
        for a in self.body['actions']:
            for field, target in (('actor_ids', 'actors'), ('permission_rule_ids', 'rules'), ('rule_ids', 'rules'), ('read_data_ids', 'data'), ('write_data_ids', 'data'), ('workflow_ids', 'workflows')):
                for i in a[field]:
                    self.local(i, target)
        for r in self.body['rules']:
            for a in r['action_ids']:
                self.local(a, 'actions');self.action_rules[a].add(r['id'])
        for r in self.body['responsibilities']:
            self.local(r['component_id'], 'components')
            for a in r['action_ids']:
                self.local(a, 'actions')
            for i in r['rule_ids']:
                self.local(i, 'rules')
        for w in self.body['workflows']:
            nodes = {n['id']: n for n in w['nodes']}
            need(w['entry_node_id'] in nodes, 'workflow_entry')
            for n in nodes.values():
                if n['action_id'] is not None:
                    self.local(n['action_id'], 'actions')
            for e in w['edges']:
                need(e['from'] in nodes and e['to'] in nodes, 'workflow_edge')
                source.refs(e['trace']['source_refs'])
        for i in self.body['interfaces']:
            self.local(i['provider_component_id'], 'components')
            for r in i['responsibility_ids']:
                self.local(r, 'responsibilities')
        for d in self.body['dependencies']:
            self.local(d['consumer_component_id'], 'components');self.local(d['provider_component_id'], 'components')
            if d['interface_id']:
                self.local(d['interface_id'], 'interfaces')
            expected = set(d['action_ids']) or {n['action_id'] for wid in d['workflow_ids'] for n in self.local(wid, 'workflows')['nodes'] if n['action_id']}
            need(len(d['support']) == len(expected) and {s['action_id'] for s in d['support']} == expected, 'support_inventory')
            for s in d['support']:
                self.local(s['action_id'], 'actions')
                for i in s['provider_responsibility_ids']:
                    self.local(i, 'responsibilities')
                if s['required_action_ids'] is not None:
                    for a in s['required_action_ids']:
                        self.local(a, 'actions')
                self.action_support[s['action_id']].append((d, s))
        self.part_context = {p: digest(dict(part=semantic(self.parts[p]), row=semantic(self.part_rows[p]))) for p in self.parts}
        self.element_context = {i: digest(semantic(e)) for i, e in self.elements.items()}
        self._cache = {}
        budget.check()

    def sources_in(self, value):
        out = set();todo = [value]
        while todo:
            self.budget.check();v = todo.pop()
            if type(v) is dict:
                if set(v) == {'snapshot_id', 'input_pointer'}:
                    out.add(self.source.source(v))
                else:
                    todo.extend(v.values())
            elif type(v) is list:
                todo.extend(v)
        return out

    def local(self, i, kind):
        need(i in self.maps[kind], 'graph_typed_local_' + kind)
        return self.maps[kind][i]

    def model(self):
        return deepcopy(self._model)

    def source_seed(self, pointers):
        elements = set()
        parts = set()
        for ptr in pointers:
            # Common component/responsibility/data/actor provenance is context,
            # not proof that every action using that context is a source use.
            elements.update(i for i in self.source_elements[ptr] if self.kinds[i] in ('actions', 'rules', 'workflows', 'dependencies'))
            parts.update(self.source_parts[ptr])
        return elements, parts

    def closure(self, elements=(), parts=()):
        budget = self.budget
        budget.check()
        ee = set(elements);pp = set(parts)
        need(ee <= self.elements.keys() and pp <= self.parts.keys(), 'scope_members')
        key = frozenset(ee), frozenset(pp)
        if key in self._cache:
            return self._cache[key]
        queue = deque([('e', i, True) for i in ee] + [('p', p, True) for p in pp])
        seen = set();aa = set();uses = set();active_parts = set();sources = set();reasons = set()
        system_added = False
        while queue:
            budget.check()
            kind, i, active = queue.popleft()
            token = kind, i, active
            if token in seen:
                continue
            seen.add(token)
            if kind == 'p':
                p = self.parts[i];pp.add(i)
                if active:
                    active_parts.add(i)
                sources.add(self.part_rows[i]['source_ref']['input_pointer'])
                queue.extend(('e', a, True) for a in p['action_ids'])
                queue.extend(('e', r, False) for r in p['primary_responsibility_ids'] + p['supporting_responsibility_ids'])
                continue
            e = self.elements[i];typ = self.kinds[i];ee.add(i)
            if active:
                uses.add(i)
                sources.update(self.sources_in(e))
            if e['state'] in ('needs_clarification', 'needs_reanalysis'):
                reasons.add('NEEDS_REANALYSIS')
            if typ == 'actions':
                aa.add(i)
                if not system_added:
                    queue.extend(('p', p, False) for p, value in self.parts.items() if value['target'] == 'system')
                    system_added = True
                queue.extend(('e', r, True) for r in set(e['rule_ids'] + e['permission_rule_ids']) | self.action_rules[i])
                queue.extend(('e', w, True) for w in e['workflow_ids'])
                queue.extend(('e', c, False) for c in e['actor_ids'] + e['read_data_ids'] + e['write_data_ids'])
                matching = self.action_parts[i]
                if not matching:
                    reasons.add('ACTION_WITHOUT_PART')
                queue.extend(('p', p, True) for p in matching)
                for d, support in self.action_support[i]:
                    queue.append(('e', d['id'], True))
                    queue.extend(('e', r, False) for r in support['provider_responsibility_ids'])
                    if support['required_action_ids'] is None:
                        reasons.add('SCOPE_UNDETERMINED')
                    else:
                        queue.extend(('e', a, True) for a in support['required_action_ids'])
            elif typ == 'workflows' and active:
                nodes = {n['id']: n for n in e['nodes']};todo = [e['entry_node_id']];visited = set()
                while todo:
                    budget.check();nid = todo.pop()
                    if nid in visited:
                        continue
                    visited.add(nid);a = nodes[nid]['action_id']
                    if a:
                        queue.append(('e', a, True))
                    todo.extend(edge['to'] for edge in e['edges'] if edge['from'] == nid)
                reachable = {nodes[n]['action_id'] for n in visited if nodes[n]['action_id']}
                if any(iw['id'] in self.elements[a]['workflow_ids'] and a not in reachable for a in aa for iw in [e]):
                    reasons.add('SCOPE_UNDETERMINED')
                if any(p['mode'] not in ('exclusive', 'parallel') for p in e['branch_points']):
                    reasons.add('SCOPE_UNDETERMINED')
            elif typ == 'responsibilities':
                queue.append(('e', e['component_id'], False))
                queue.extend(('e', r, False) for r in e['rule_ids'])
            elif typ == 'interfaces':
                queue.append(('e', e['provider_component_id'], False))
                queue.extend(('e', r, False) for r in e['responsibility_ids'])
            elif typ == 'dependencies':
                queue.extend(('e', c, False) for c in (e['consumer_component_id'], e['provider_component_id']))
                if e['interface_id']:
                    queue.append(('e', e['interface_id'], False))
        need(all(set(self.parts[p]['action_ids']) <= aa for p in pp), 'all_discovered_part_actions')
        # Recheck reachability after the final action union, not only first visit.
        for a in aa:
            for wid in self.elements[a]['workflow_ids']:
                w = self.elements[wid];nodes = {n['id']: n for n in w['nodes']};todo = [w['entry_node_id']];visited = set()
                while todo:
                    budget.check();n = todo.pop()
                    if n in visited:
                        continue
                    visited.add(n);todo.extend(x['to'] for x in w['edges'] if x['from'] == n)
                if a not in {nodes[n]['action_id'] for n in visited}:
                    reasons.add('SCOPE_UNDETERMINED')
        result = Footprint(self.id, frozenset(ee), frozenset(pp), frozenset(aa), frozenset(uses), frozenset(active_parts), frozenset(sources), tuple(sorted(reasons)))
        self._cache[key] = result
        return result

    def reverse_impact(self, changed_elements=(), changed_parts=()):
        """Meaningful changed context triggers readers; discovered context does not.

        Propagate causal actions/Parts to a fixed point without promoting a shared
        unchanged component/data/responsibility into a changed semantic atom.
        """
        triggers = set(changed_elements);part_triggers = set(changed_parts)
        need(triggers <= self.elements.keys() and part_triggers <= self.parts.keys(), 'reverse_members')
        # A changed/new responsibility membership assigns its actions even
        # before a Part references it. Ordinary shared responsibility context
        # still does not pull all its actions into a forward closure.
        triggers.update(a for i in tuple(triggers) if self.kinds[i] == 'responsibilities'
                        for a in self.elements[i]['action_ids'])
        result_e = set(triggers);result_p = set(part_triggers)
        while True:
            self.budget.check();before = frozenset(triggers), frozenset(part_triggers)
            seeds = [('e', a) for a in self.maps['actions']] + [('p', p) for p in self.parts]
            for kind, i in seeds:
                self.budget.check()
                c = self.closure([i] if kind == 'e' else (), [i] if kind == 'p' else ())
                if c.elements & triggers or c.parts & part_triggers:
                    result_e.update(c.elements);result_p.update(c.parts)
                    triggers.update(c.uses);part_triggers.update(c.active_parts)
            if before == (frozenset(triggers), frozenset(part_triggers)):
                break
        return self.closure(triggers, part_triggers) if triggers or part_triggers else self.closure()


@dataclass(frozen=True)
class Impact:
    before: Footprint
    after: Footprint
    changed_elements: frozenset
    changed_parts: frozenset
    changed_rows: frozenset
    source_changed: bool


def impact(before, after):
    """Compare base AND candidate context, including removed relationships."""
    before.budget.check();after.budget.check()
    elements = {i for i in before.elements.keys() | after.elements.keys() if before.element_context.get(i) != after.element_context.get(i)}
    parts = {p for p in before.parts.keys() | after.parts.keys() if before.part_context.get(p) != after.part_context.get(p)}
    rows = {r for r in before.rows.keys() | after.rows.keys() if semantic(before.rows.get(r)) != semantic(after.rows.get(r))}
    source_changed = (before.source.context_id, before.source.snapshot_id, before.source.archive_sha256, before.source.snapshot_hash) != (after.source.context_id, after.source.snapshot_id, after.source.archive_sha256, after.source.snapshot_hash)
    if source_changed:
        elements.update(before.elements.keys() | after.elements.keys());parts.update(before.parts.keys() | after.parts.keys())
    return Impact(before.reverse_impact(elements & before.elements.keys(), parts & before.parts.keys()),
                  after.reverse_impact(elements & after.elements.keys(), parts & after.parts.keys()),
                  frozenset(elements), frozenset(parts), frozenset(rows), source_changed)
