"""Versioned H1-only resource bounds. Never applied by the legacy validators."""
import json
import re
import time

from .codec_boundary import decode, encode
from .errors import S02Error

VERSION = 's02-2a-local-limits/0.1.0-draft.1'
DEFAULTS = dict(raw_bytes=1048576, config_bytes=2097152, plan_bytes=16777216,
                depth=64, values=100000, string_bytes=65536, obligations=1000,
                entities=2000, nodes=2000, edges=4000, parts=4000,
                findings=500, issues=2000, refs=50000, compute_seconds=30)


def exceeded(name):
    raise S02Error('LOCAL_LIMIT_EXCEEDED', 'schema', 'H1 local resource limit exceeded',
                   details={'limit': name, 'limits_version': VERSION})


def cap(name, value):
    if value > DEFAULTS[name]: exceeded(name)


class Budget:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.deadline = clock() + DEFAULTS['compute_seconds']

    def check(self):
        if self.clock() > self.deadline: exceeded('compute_seconds')


def bounded_decode(raw, budget):
    """Bound depth/values/string allocation before the exact codec builds a tree.

    This lexical pass does not accept JSON or replace the codec's grammar,
    duplicate-key, number or Unicode oracle. Original bytes remain in staging.
    """
    cap('raw_bytes', len(raw))
    try: text = raw.decode(json.detect_encoding(raw))
    except UnicodeError: return decode(raw)
    stack = []; count = 0; pos = 0
    token = re.compile(r'(?:-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null)')
    while pos < len(text):
        budget.check(); char = text[pos]
        if char in ' \t\r\n,:': pos += 1; continue
        if char in '{[':
            cap('depth', len(stack) + 1); count += 1; stack.append(char); pos += 1
        elif char in '}]':
            if not stack: break
            stack.pop(); pos += 1
        elif char == '"':
            try: value, end = json.decoder.scanstring(text, pos + 1, True)
            except ValueError: break
            try: cap('string_bytes', len(value.encode('utf-8')))
            except UnicodeError:
                encode(value)  # Exact codec rejects unsupported Unicode before any tree materialization.
                raise S02Error('PROCESSING_FAILED','schema','Unsupported candidate Unicode')
            look = end
            while look < len(text) and text[look] in ' \t\r\n': look += 1
            is_key = stack and stack[-1] == '{' and look < len(text) and text[look] == ':'
            if not is_key: cap('depth', len(stack) + 1); count += 1
            pos = end
        else:
            match = token.match(text, pos)
            if not match: break
            cap('depth', len(stack) + 1); count += 1; pos = match.end()
        cap('values', count)
    budget.check(); value = decode(raw); encode(value); budget.check()
    return value


def ref_count(value):
    """Count occurrences, including finding links; declarations are not refs."""
    if type(value) is list: return sum(ref_count(v) for v in value)
    if type(value) is not dict: return 0
    if set(value) in ({'snapshot_id', 'input_pointer'}, {'local_handle'}, {'base_handle'}): return 1
    total = 0
    for key, child in value.items():
        if (key in ('finding_handles', 'questions') or key.endswith('_ids')) and type(child) is list: total += len(child)
        elif (key == 'finding_handle' or key.endswith('_id')) and type(child) is str: total += 1
        else: total += ref_count(child)
    return total


def model_limits(body, issues):
    collections = ('actors', 'actions', 'workflows', 'data', 'rules', 'components',
                   'responsibilities', 'interfaces', 'dependencies')
    cap('entities', sum(len(body[k]) for k in collections))
    cap('nodes', sum(len(w['nodes']) for w in body['workflows']))
    cap('edges', sum(len(w['edges']) for w in body['workflows']))
    cap('parts', sum(len(m['parts']) for m in body['mappings']))
    cap('issues', len(issues)); cap('refs', ref_count([body, *issues]))
