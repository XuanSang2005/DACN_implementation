"""H2-only bounded computation. No provider, filesystem or repository access."""
from dataclasses import dataclass
import json
import re
from hashlib import sha256
from time import monotonic
from .codec_boundary import decode, encode
from .errors import S02Error

VERSION = 's02-h2-local-limits/0.1.0-draft.2'


def fail(reason, *, limit=False):
    raise S02Error('H2_LOCAL_LIMIT' if limit else 'H2_CONTRACT_INVALID', 'schema',
                   'H2 pure policy rejected input', details={'reason': reason, 'limits_version': VERSION})


def need(ok, reason):
    if not ok:
        fail(reason)


@dataclass(frozen=True)
class Limits:
    raw_bytes: int = 1048576
    authority_bytes: int = 1048576
    config_bytes: int = 2097152
    plan_bytes: int = 16777216
    depth: int = 64
    values: int = 100000
    string_bytes: int = 65536
    refs: int = 50000
    obligations: int = 1000
    entities: int = 2000
    nodes: int = 2000
    edges: int = 4000
    parts: int = 4000
    findings: int = 500
    issues: int = 2000
    compute_seconds: int = 30


DEFAULTS = Limits()


def references(value):
    """Count uses, not declarations; atomic refs are never counted twice."""
    total = 0
    todo = [value]
    while todo:
        v = todo.pop()
        if type(v) is list:
            todo.extend(v)
        elif type(v) is dict:
            if set(v) in ({'snapshot_id', 'input_pointer'}, {'local_handle'}, {'base_handle'}):
                total += 1
                continue
            for k, child in v.items():
                if k in ('progress_by_unit',):
                    need(type(child) is dict, 'progress_map')
                    total += len(child)
                    todo.extend(child.values())
                elif k in ('finding_handles', 'questions', 'guard_keys', 'retained_assessment_hashes') or k.endswith('_ids'):
                    if type(child) is list:
                        total += len(child)
                        # These fields are closed lists of string references.
                        todo.extend(x for x in child if type(x) in (dict, list))
                    else:
                        todo.append(child)
                elif k in ('finding_handle', 'issue_key', 'unit_id', 'held_unit_id') or k.endswith('_id'):
                    if type(child) is str:
                        total += 1
                    else:
                        todo.append(child)
                else:
                    todo.append(child)
    return total


class Budget:
    """One invocation budget, explicitly shared by all graph/policy calls.

    Clock is injectable. Deadline is cooperative, not a syscall hard timeout.
    Smaller limits support boundary tests; increasing production caps is rejected.
    """
    def __init__(self, *, clock=monotonic, limits=DEFAULTS):
        need(type(limits) is Limits, 'limits_type')
        for k, ceiling in vars(DEFAULTS).items():
            n = getattr(limits, k)
            need(type(n) is int and 0 < n <= ceiling, 'limits_cannot_increase')
        self.limits = limits
        self.clock = clock
        self.deadline = clock() + limits.compute_seconds
        self.input_values = 0
        self.input_refs = 0
        self._slots = {}
        self._raw_slots = {}

    def check(self):
        if self.clock() > self.deadline:
            fail('compute_seconds', limit=True)

    def cap(self, name, size):
        self.check()
        if size > getattr(self.limits, name):
            fail(name, limit=True)

    def inspect(self, value, *, input_lane=False, slot=None):
        """Bound before encoder recursion; repeated occurrences count separately."""
        prior = self._slots.get(slot) if input_lane and slot is not None else None
        base_values = self.input_values - (prior[1] if prior else 0)
        base_refs = self.input_refs - (prior[2] if prior else 0)
        count = 0
        todo = [(value, 1, frozenset())]
        while todo:
            self.check()
            v, depth, ancestors = todo.pop()
            self.cap('depth', depth)
            count += 1
            self.cap('values', count + (base_values if input_lane else 0))
            if type(v) is str:
                try:
                    size = len(v.encode('utf-8'))
                except UnicodeError:
                    fail('unicode')
                self.cap('string_bytes', size)
            elif type(v) in (dict, list):
                need(id(v) not in ancestors, 'cyclic_input')
                chain = ancestors | {id(v)}
                if type(v) is dict:
                    need(all(type(k) is str for k in v), 'object_keys')
                    for k in v:
                        try:
                            size = len(k.encode('utf-8'))
                        except UnicodeError:
                            fail('unicode_key')
                        self.cap('string_bytes', size)
                    values = v.values()
                else:
                    values = v
                todo.extend((x, depth + 1, chain) for x in values)
        refs = references(value)
        self.cap('refs', refs + (base_refs if input_lane else 0))
        self.check()
        raw = encode(value)  # exact codec: floats/unsupported Unicode fail closed
        self.check()
        if input_lane:
            identity = sha256(raw).hexdigest()
            need(not prior or identity == prior[0], 'input_slot_changed')
            self.input_values = base_values + count
            self.input_refs = base_refs + refs
            if slot is not None:
                self._slots[slot] = (identity, count, refs)
        return value

    def raw_work(self, candidate, analysis):
        need(candidate is None or type(candidate) is bytes, 'candidate_bytes')
        need(type(analysis) is bytes, 'analysis_bytes')
        self.cap('raw_bytes', len(candidate or b'') + len(analysis))

    def serialized(self, value, kind):
        need(kind in ('config', 'plan'), 'serialized_kind')
        self.inspect(value)
        raw = encode(value)
        self.cap(kind + '_bytes', len(raw))
        return raw

    def parse(self, raw, *, slot=None):
        """Pure byte parser. H2-B must stage raw before invoking this method."""
        need(type(raw) is bytes, 'raw_bytes_type')
        self.cap('raw_bytes', len(raw))
        if slot is not None:
            identity = sha256(raw).hexdigest()
            need(slot not in self._raw_slots or self._raw_slots[slot] == identity, 'raw_input_slot_changed')
            self._raw_slots[slot] = identity
        # Lexical guard only; exact codec remains the grammar/numeric oracle.
        try:
            data = raw.decode(json.detect_encoding(raw))
        except UnicodeError:
            return self.inspect(decode(raw), input_lane=True, slot=slot)
        pos = 0
        stack = []
        prior = self._slots.get(slot) if slot is not None else None
        count = self.input_values - (prior[1] if prior else 0)
        token = re.compile(r'(?:-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null)')
        while pos < len(data):
            self.check();char = data[pos]
            if char in ' \t\r\n,:':
                pos += 1;continue
            if char in '{[':
                self.cap('depth', len(stack) + 1)
                count += 1;stack.append(char);pos += 1
            elif char in '}]':
                if not stack:
                    break
                stack.pop();pos += 1
            elif char == '"':
                try:
                    value, end = json.decoder.scanstring(data, pos + 1, True)
                    self.cap('string_bytes', len(value.encode('utf-8')))
                except (ValueError, UnicodeError):
                    break
                look = end
                while look < len(data) and data[look] in ' \t\r\n':
                    look += 1
                is_key = stack and stack[-1] == '{' and look < len(data) and data[look] == ':'
                if not is_key:
                    self.cap('depth', len(stack) + 1);count += 1
                pos = end
            else:
                match = token.match(data, pos)
                if not match:
                    break
                self.cap('depth', len(stack) + 1);count += 1;pos = match.end()
            self.cap('values', count)
        self.check();value = decode(raw);self.check()
        return self.inspect(value, input_lane=True, slot=slot)


def digest(value):
    return sha256(encode(value)).hexdigest()
