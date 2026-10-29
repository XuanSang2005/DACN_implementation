"""Closed H2-A contracts. Trusted grants are caller inputs, never payload flags."""
from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
from decimal import Decimal
from types import MappingProxyType
import re
from .codec_boundary import encode
from .validation import inventory, resolve_pointer, valid_id
from .h2_limits import Budget, digest, need

POLICY = 's02-h2-scope-rules/0.1.0-draft.2'
WORK = 's02-h2-work/0.1.0-draft.2'
HOLD = 's02-h2-hold/0.1.0-draft.2'
ANALYSIS = 's02-h2-analysis/0.1.0-draft.2'


def closed(v, keys, name):
    need(type(v) is dict and set(v) == set(keys.split()), name + '_fields')


def ident(v):
    need(valid_id(v), 'identifier')
    return v


def text(v):
    need(type(v) is str and bool(v.strip()), 'nonempty_text')
    return v


def hash64(v):
    need(type(v) is str and re.fullmatch('[a-f0-9]{64}', v) is not None, 'sha256')
    return v


def integer(v, lo=0, hi=None):
    # Exact S01 decoder retains JSON numbers as Decimal. Only private metadata
    # is interpreted as an integer; source/business payload is never coerced.
    need(type(v) is int or type(v) is Decimal and v.is_finite() and v == v.to_integral_value(), 'metadata_integer')
    need(v >= lo and (hi is None or v <= hi), 'metadata_integer_range')
    return int(v)


def unique(v):
    need(type(v) is list and all(type(x) is str for x in v) and len(v) == len(set(v)), 'unique_string_refs')
    for x in v:
        ident(x)
    return frozenset(v)


@dataclass(frozen=True)
class Family:
    unit_id: str
    pointer: str
    obligations: frozenset
    kind: str


class SourceInventory:
    """Projection of a caller's checked S01 lookup; not a substitute lookup."""
    def __init__(self, snapshot, source_context_id, archive_sha256, budget):
        budget.check()
        need(type(snapshot) is dict and type(snapshot.get('input')) is dict, 'checked_snapshot')
        self.snapshot_id = ident(snapshot['snapshot_id'])
        self.context_id = ident(source_context_id)
        self.archive_sha256 = hash64(archive_sha256)
        self.snapshot_hash = digest(snapshot)
        self._input = deepcopy(snapshot['input'])
        families = []
        for kind in ('functional_requirements', 'non_functional_requirements', 'constraints'):
            need(type(self._input.get(kind)) is list, 'source_inventory_kind')
            for i, obligation in enumerate(self._input[kind]):
                budget.check()
                need(type(obligation) is dict and type(obligation.get('acceptance_criteria')) is list, 'source_criteria')
                root = '/' + kind + '/' + str(i)
                refs = frozenset([root, *[root + '/acceptance_criteria/' + str(j) for j in range(len(obligation['acceptance_criteria']))]])
                uid = 'unit.' + digest([self.snapshot_id, root])
                families.append(Family(uid, root, refs, kind))
        self.families = tuple(families)
        self.units = MappingProxyType({f.unit_id: f for f in families})
        self.obligations = frozenset(p for f in families for p in f.obligations)
        budget.cap('obligations', len(self.obligations))
        need(self.obligations == inventory(snapshot), 'source_inventory_exact')

    def source(self, v, *, obligation=False):
        closed(v, 'snapshot_id input_pointer', 'source_ref')
        need(v['snapshot_id'] == self.snapshot_id, 'source_snapshot')
        try:
            resolve_pointer(self._input, v['input_pointer'])
        except (KeyError, IndexError, ValueError, TypeError):
            need(False, 'source_pointer')
        if obligation:
            need(v['input_pointer'] in self.obligations, 'source_obligation')
        return v['input_pointer']

    def refs(self, values, *, obligation=False):
        need(type(values) is list, 'source_refs')
        out = [self.source(v, obligation=obligation) for v in values]
        need(len(out) == len(set(out)), 'source_refs_unique')
        return frozenset(out)

    def selected(self, units):
        need(bool(units) and set(units) <= self.units.keys(), 'selected_units')
        return frozenset(p for u in units for p in self.units[u].obligations)


@dataclass(frozen=True)
class HoldSelector:
    issue_id: str
    issue_key: str
    target_step: int
    kind: str
    sources: frozenset
    elements: frozenset
    parts: frozenset
    impact_known: bool
    code_task_role: str | None

    def __post_init__(self):
        ident(self.issue_id);ident(self.issue_key);integer(self.target_step, 1, 4)
        need(self.kind in ('obligation_families', 'explicit_uses', 'all_source_uses'), 'selector_kind')
        need(type(self.impact_known) is bool and (self.impact_known or self.kind == 'all_source_uses'), 'selector_impact')
        need(self.code_task_role in (None, 'await_builder', 'global_mapping', 'merge_guard'), 'task_role')
        need(all(type(v) is frozenset for v in (self.sources, self.elements, self.parts)), 'immutable_selector_sets')
        for x in self.elements | self.parts:
            ident(x)

    @classmethod
    def parse(cls, value, source, budget, *, input_lane=True):
        need(type(value) is dict, 'hold_object')
        budget.inspect(value, input_lane=input_lane, slot='selector.' + ident(value.get('issue_id')))
        closed(value, 'version issue_id issue_key target_step kind source_refs element_ids mapping_part_ids impact_known code_task_role', 'hold')
        need(value['version'] == HOLD, 'hold_version')
        integer(value['target_step'], 1, 4)
        need(type(value['impact_known']) is bool, 'impact_boolean')
        need(value['kind'] in ('obligation_families', 'explicit_uses', 'all_source_uses'), 'selector_kind')
        need(value['code_task_role'] in (None, 'await_builder', 'global_mapping', 'merge_guard'), 'task_role')
        refs = source.refs(value['source_refs'])
        if value['kind'] == 'obligation_families':
            need(refs and refs <= source.obligations, 'selector_obligations')
        if not value['impact_known']:
            need(value['kind'] == 'all_source_uses', 'unknown_requires_all_source_uses')
        return cls(ident(value['issue_id']), ident(value['issue_key']), integer(value['target_step'], 1, 4), value['kind'], refs,
                   unique(value['element_ids']), unique(value['mapping_part_ids']), value['impact_known'], value['code_task_role'])

    def payload(self, source):
        return dict(version=HOLD, issue_id=self.issue_id, issue_key=self.issue_key, target_step=self.target_step,
                    kind=self.kind, source_refs=[dict(snapshot_id=source.snapshot_id, input_pointer=p) for p in sorted(self.sources)],
                    element_ids=sorted(self.elements), mapping_part_ids=sorted(self.parts), impact_known=self.impact_known, code_task_role=self.code_task_role)


def selectors_hash(selectors, source):
    need(len({s.issue_key for s in selectors}) == len(selectors), 'selector_keys_unique')
    return digest([s.payload(source) for s in sorted(selectors, key=lambda s: s.issue_key)])


BIND_KEYS = '''version purpose provider_id provider_version policy_version store_id session_id
source_context_id snapshot_id archive_sha256 base_model_id base_model_sha256
base_analysis_set_id base_analysis_set_sha256 operation goal step unit_ids current_selectors_sha256
progress_before_sha256 retained_assessment_hashes read_write_intent_sha256 candidate_sha256
candidate_length analysis_sha256 analysis_length guard_keys current_guard_ids assessment_policy_version'''


@dataclass(frozen=True)
class BindingRequest:
    """Immutable exact bytes; creation validates the closed binding tuple."""
    raw: bytes
    key: str

    @classmethod
    def parse(cls, value, budget):
        budget.inspect(value, input_lane=True, slot='request')
        closed(value, BIND_KEYS, 'binding')
        need(value['version'] == WORK and value['policy_version'] == POLICY and value['assessment_policy_version'] == POLICY, 'binding_version')
        need(value['purpose'] == 'synthetic_test_only' and value['provider_version'] == 'local-synthetic/1', 'provider_purpose_version')
        for k in ('provider_id', 'store_id', 'session_id', 'source_context_id', 'snapshot_id', 'base_model_id', 'base_analysis_set_id'):
            ident(value[k])
        for k in ('archive_sha256', 'base_model_sha256', 'base_analysis_set_sha256', 'current_selectors_sha256', 'progress_before_sha256', 'read_write_intent_sha256', 'analysis_sha256'):
            hash64(value[k])
        for k in ('unit_ids', 'guard_keys', 'current_guard_ids'):
            unique(value[k])
        need(bool(value['unit_ids']), 'binding_units')
        need(type(value['retained_assessment_hashes']) is list and len(value['retained_assessment_hashes']) == len(set(value['retained_assessment_hashes'])), 'retained_unique')
        for x in value['retained_assessment_hashes']:
            hash64(x)
        integer(value['step'], 1, 4)
        need(value['operation'] in ('step', 'revalidate'), 'binding_operation')
        need(value['goal'] in ('build', 'admission', 'retained_output'), 'binding_goal')
        need((value['operation'] == 'step') == (value['goal'] == 'build'), 'operation_goal')
        for k in ('candidate_length', 'analysis_length'):
            integer(value[k])
        if value['candidate_sha256'] is None:
            need(value['candidate_length'] == 0, 'null_candidate_length')
        else:
            hash64(value['candidate_sha256'])
        if value['operation'] == 'revalidate':
            need(value['candidate_sha256'] is None, 'revalidation_no_candidate')
        normalized = dict(value)
        for k in ('unit_ids', 'guard_keys', 'current_guard_ids', 'retained_assessment_hashes'):
            normalized[k] = sorted(value[k])
        raw = encode(normalized)
        return cls(raw, sha256(raw).hexdigest())

    def payload(self):
        from .codec_boundary import decode
        need(type(self.raw) is bytes and sha256(self.raw).hexdigest() == self.key, 'binding_bytes_identity')
        value = decode(self.raw)
        closed(value, BIND_KEYS, 'binding')
        return value


@dataclass(frozen=True)
class AuthorityContext:
    """Expected external process context, supplied independently of work JSON."""
    provider_id: str
    provider_version: str
    control_sha256: str

    def __post_init__(self):
        ident(self.provider_id)
        need(self.provider_version == 'local-synthetic/1', 'authority_context_version')
        hash64(self.control_sha256)


@dataclass(frozen=True)
class AuthorityGrant:
    """TRUSTED CALLER boundary, never decoded from work/analysis/config payload.

    H2-A compares an already supplied decision; provider file I/O belongs to B.
    """
    binding_key: str
    provider_id: str | None
    provider_version: str | None
    control_sha256: str | None
    decision: str
    reason: str

    def __post_init__(self):
        hash64(self.binding_key)
        need(self.decision in ('allow', 'deny', 'unavailable', 'invalid'), 'authority_decision')
        if self.decision in ('allow', 'deny') or self.provider_id is not None:
            ident(self.provider_id)
        if self.decision in ('allow', 'deny') or self.provider_version is not None:
            text(self.provider_version)
        if self.decision in ('allow', 'deny') or self.control_sha256 is not None:
            hash64(self.control_sha256)
        text(self.reason)

    def matches(self, binding, context):
        v = binding.payload()
        return (self.decision == 'allow' and self.binding_key == binding.key and
                self.provider_id == v['provider_id'] and self.provider_version == v['provider_version'] and
                type(context) is AuthorityContext and self.provider_id == context.provider_id and
                self.provider_version == context.provider_version and self.control_sha256 == context.control_sha256)


@dataclass(frozen=True)
class ConstructionPermit:
    """Caller-supplied checked code provenance, not a candidate role exemption."""
    issue_id: str
    issue_key: str
    origin_command_id: str
    origin_run_id: str
    origin_plan_sha256: str
    unit_ids: frozenset
    target_step: int
    role: str

    def __post_init__(self):
        for v in (self.issue_id, self.issue_key, self.origin_command_id, self.origin_run_id):
            ident(v)
        hash64(self.origin_plan_sha256)
        need(type(self.unit_ids) is frozenset and bool(self.unit_ids), 'permit_units')
        for u in self.unit_ids:
            ident(u)
        integer(self.target_step, 1, 4)
        need(self.role in ('await_builder', 'global_mapping'), 'permit_role')
        need(self.role != 'global_mapping' or self.target_step == 4, 'mapping_task_step')

    def valid_for(self, issue, selector, units, step):
        key = 'h2.construct.' + digest([self.origin_command_id, sorted(self.unit_ids), self.target_step, self.role])
        return (self.issue_key == key == selector.issue_key == issue['body']['issue_key'] and
                self.issue_id == selector.issue_id == issue['id'] and issue['body']['kind'] == 'verification' and
                self.role in ('await_builder', 'global_mapping') and selector.code_task_role == self.role and
                self.target_step == selector.target_step and step <= self.target_step and
                set(units) <= self.unit_ids and valid_id(self.origin_command_id) and valid_id(self.origin_run_id) and
                re.fullmatch('[a-f0-9]{64}', self.origin_plan_sha256) is not None)


EVIDENCE_KEYS = 'version id source_context_id snapshot_id base_model_id base_analysis_set_id step unit_ids selectors_sha256 policy_version inspections independence'


class AnalysisEvidence:
    def __setattr__(self, name, value):
        need(not getattr(self, '_sealed', False), 'immutable_evidence')
        object.__setattr__(self, name, value)

    def __init__(self, raw, source, budget):
        need(type(raw) is bytes, 'analysis_bytes')
        self.raw = raw
        self.hash = sha256(raw).hexdigest()
        self.length = len(raw)
        v = budget.parse(raw, slot='analysis')
        closed(v, EVIDENCE_KEYS, 'analysis')
        need(v['version'] == ANALYSIS and v['policy_version'] == POLICY, 'analysis_version')
        ident(v['id']);ident(v['source_context_id']);ident(v['base_model_id']);ident(v['base_analysis_set_id'])
        need(v['source_context_id'] == source.context_id and v['snapshot_id'] == source.snapshot_id, 'analysis_source')
        integer(v['step'], 1, 4)
        units = unique(v['unit_ids']);source.selected(units);hash64(v['selectors_sha256'])
        need(type(v['inspections']) is list and type(v['independence']) is list, 'analysis_lists')
        inspections = {}
        for row in v['inspections']:
            budget.check()
            closed(row, 'source_ref read verdict basis_source_refs needed_facts reason', 'inspection')
            ptr = source.source(row['source_ref'], obligation=True)
            need(ptr not in inspections, 'inspection_unique')
            need(row['read'] in ('inspected', 'not_inspected'), 'inspection_read')
            need(row['verdict'] in ('usable', 'held', 'not_relevant_with_reason'), 'inspection_verdict')
            basis = source.refs(row['basis_source_refs'])
            need(type(row['needed_facts']) is list and all(type(x) is str and x.strip() for x in row['needed_facts']), 'needed_facts')
            text(row['reason'])
            if row['verdict'] != 'held':
                need(row['read'] == 'inspected' and ptr in basis and not row['needed_facts'], 'usable_inspection_basis')
            inspections[ptr] = dict(read=row['read'], verdict=row['verdict'], basis=basis)
        need(set(inspections) == source.obligations, 'inspection_full_inventory')
        pairs = {}
        for row in v['independence']:
            closed(row, 'issue_key unit_id verdict basis_source_refs reason', 'independence')
            ident(row['issue_key']);need(row['unit_id'] in source.units, 'independence_unit')
            text(row['reason']);need(row['verdict'] in ('independent', 'held', 'unknown'), 'independence_verdict')
            key = row['issue_key'], row['unit_id']
            need(key not in pairs, 'independence_unique')
            pairs[key] = dict(verdict=row['verdict'], basis=source.refs(row['basis_source_refs']))
        self._value = deepcopy(v)
        self._pins = {k: v[k] for k in ('source_context_id', 'snapshot_id', 'base_model_id', 'base_analysis_set_id', 'step', 'selectors_sha256')}
        self.units = units
        self.inspections = MappingProxyType({k: MappingProxyType(v) for k, v in inspections.items()})
        self.pairs = MappingProxyType({k: MappingProxyType(v) for k, v in pairs.items()})
        self._sealed = True

    def matches(self, binding):
        b = binding.payload()
        return (all(b[('current_selectors_sha256' if k == 'selectors_sha256' else k)] == v for k, v in self._pins.items()) and
                set(b['unit_ids']) == self.units and b['analysis_sha256'] == self.hash and b['analysis_length'] == self.length)

    def payload(self):
        return deepcopy(self._value)
