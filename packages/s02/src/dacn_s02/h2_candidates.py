"""Pure closed H2 candidate projection/typed handles; no IDs or Records allocated."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from .codec_boundary import decode
from .h1_candidates import schema as h1_schema, KINDS, TARGETS
from .validation import Validator, FORMATS
from .h2_contracts import closed, ident, unique, hash64, integer, BIND_KEYS
from .h2_limits import need, digest

VERSION = 's02-h2-candidate/0.1.0-draft.2'


def schema(step):
    step = integer(step, 1, 4)
    s = h1_schema(step)  # detached copy; no changes to H1 or canonical registry
    s['properties']['candidate_version'] = dict(const=VERSION)
    s['properties']['unit_ids'] = dict(type='array', items=dict(type='string', format='s02-id'), uniqueItems=True, minItems=1)
    s['properties']['scope_request_sha256'] = dict(type='string', pattern='^[a-f0-9]{64}$')
    s['required'] = list(s['properties'])
    return s


def scope_request_hash(binding):
    """Hash intent WITHOUT raw candidate/analysis slots (avoids self-hash cycle)."""
    b = binding.payload() if hasattr(binding, 'payload') else deepcopy(binding)
    closed(b, BIND_KEYS, 'scope_intent')
    return digest({k: v for k, v in b.items() if k not in ('candidate_sha256', 'candidate_length', 'analysis_sha256', 'analysis_length')})


@dataclass(frozen=True)
class Candidate:
    raw: bytes
    sha256: str
    declared_handles: tuple
    base_reference_ids: frozenset
    namespace: str

    def payload(self):
        need(sha256(self.raw).hexdigest() == self.sha256, 'candidate_bytes_identity')
        return decode(self.raw)


def parse_candidate(raw, context, *, step, unit_ids, expected_scope_hash,
                    base_aliases=None, read_context_ids=frozenset(), current_issue_ids=frozenset()):
    """Caller supplies code-owned expected intent/read allowlist/current Issues.

    This validates shape/refs/source/write units, not candidate-to-Model builder
    fidelity or persistence. It grants neither semantic authority nor task waiver.
    """
    budget = context.budget
    v = budget.parse(raw, slot='candidate')
    need(next(Validator(schema(step), format_checker=FORMATS).iter_errors(v), None) is None, 'candidate_closed_projection')
    units = unique(v['unit_ids'])
    need(units == frozenset(unit_ids), 'candidate_units')
    selected = context.source.selected(units)
    hash64(expected_scope_hash)
    need(v['scope_request_sha256'] == expected_scope_hash, 'candidate_scope_pin')
    budget.cap('findings', len(v['proposals']['findings']))
    aliases = deepcopy(base_aliases or {})
    need(type(aliases) is dict and type(read_context_ids) is frozenset and type(current_issue_ids) is frozenset, 'candidate_read_context')
    kinds = {i: KINDS.get(kind) or {'interfaces':'Interface', 'dependencies':'Dependency'}.get(kind) for i, kind in context.kinds.items()}
    kinds.update({p:'Part' for p in context.parts})
    kinds.update({i:'Issue' for i in current_issue_ids})
    for w in context.maps['workflows'].values():
        kinds.update({n['id']:'Node' for n in w['nodes']});kinds.update({e['id']:'Edge' for e in w['edges']})
    need(read_context_ids <= kinds.keys(), 'candidate_read_members')
    for alias, item in aliases.items():
        ident(alias);closed(item, 'id kind', 'base_alias')
        need(item['id'] in kinds and item['kind'] == kinds[item['id']], 'base_alias_type')
    local = {}
    def add(e, kind):
        h = e['handle'];need(h not in local, 'candidate_handle_unique');local[h] = kind
    for coll, kind in KINDS.items():
        for e in v['proposals'].get(coll, []):
            add(e, kind)
            refs = context.source.refs(e['trace']['source_refs'])
            need(refs and refs <= selected, 'candidate_write_sources')
            if kind == 'Workflow':
                for field, typ in (('nodes','Node'),('edges','Edge')):
                    for value in e[field]:
                        add(value, typ)
    for row in v['proposals'].get('mappings', []):
        for p in row['parts']:
            add(p, 'Part')
    for f in v['proposals']['findings']:
        add(f, 'Issue')
        need(context.source.refs(f['trace']['source_refs']), 'finding_source')
    used = set()
    def reference(ref, expected=None):
        if set(ref) == {'local_handle'}:
            kind = local.get(ref['local_handle'])
        else:
            item = aliases.get(ref['base_handle'])
            need(item is not None and item['id'] in read_context_ids, 'base_read_allowlist')
            kind = item['kind'];used.add(item['id'])
        need(kind is not None and (expected is None or kind == expected), 'candidate_typed_handle')
    def finding(h):
        reference(dict(local_handle=h) if h in local else dict(base_handle=h), 'Issue')
    def walk(value, field=''):
        budget.check()
        if type(value) is list:
            for child in value:
                walk(child, field)
        elif type(value) is dict:
            if set(value) == {'snapshot_id','input_pointer'}:
                context.source.source(value)
            elif set(value) in ({'local_handle'}, {'base_handle'}):
                reference(value, TARGETS.get(field))
            else:
                for k, child in value.items():
                    if k in ('finding_handles','questions'):
                        for h in child:
                            finding(h)
                    elif k == 'finding_handle':
                        finding(child)
                    else:
                        walk(child, k)
    walk(v)
    inspected = []
    for row in v['inspection']:
        ptr = context.source.source(row['source_ref'], obligation=True);inspected.append(ptr)
        need(row['read'] != 'not_inspected' or row['verdict'] == 'held', 'candidate_unread_held')
        need(row['verdict'] == 'held' or row['evidence_source_refs'], 'candidate_inspection_basis')
    need(len(inspected) == len(set(inspected)) and set(inspected) == context.source.obligations, 'candidate_inventory')
    unseen = [context.source.source(r, obligation=True) for r in v['unrepresented_source_refs']]
    need(len(unseen) == len(set(unseen)), 'unrepresented_unique')
    if step == 4:
        mapped = [context.source.source(r['source_ref'], obligation=True) for r in v['proposals']['mappings']]
        need(len(mapped) == len(set(mapped)) and set(mapped) == selected, 'candidate_full_selected_family')
    budget.check()
    return Candidate(raw, sha256(raw).hexdigest(), tuple(sorted(local.items())), frozenset(used), 'scope.' + digest(sorted(units)))
