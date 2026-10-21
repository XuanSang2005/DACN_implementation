"""Synthetic, independent oracles for draft.2 equality and revision checks."""

from copy import deepcopy
from decimal import Decimal, localcontext

import pytest

from dacn_s01.codec import ProcessingError, parse_json
from dacn_s01.revision import decide_revision, inspect_request, json_equal


@pytest.mark.parametrize("left,right,expected", [
    (b'true', b'1', False), (b'false', b'0', False),
    (b'1', b'1.0', True), (b'0', b'-0', True),
    (b'{"x":null}', b'{}', False),
    (b'{"a":1,"b":2}', b'{"b":2,"a":1.0}', True),
    (b'[1,2]', b'[2,1]', False), (b'[1]', b'[1,1]', False),
    (b'" A "', b'"A"', False), (b'"A"', b'"a"', False),
    (b'"\\u00e9"', b'"e\\u0301"', False), (b'"A"', b'"\\u0041"', True),
    (b'9007199254740993', b'9007199254740992', False),
    (b'1.234567890123456789012345678901', b'1.234567890123456789012345678902', False),
    (b'1e400', b'10e399', True), (b'1e-400', b'10e-401', True),
    (b'{"a":[true]}', b'{"a":[1]}', False), (b'null', b'false', False),
])
def test_exact_equality(left, right, expected):
    with localcontext() as context:
        context.prec = 2
        a, b = parse_json(left), parse_json(right)
        before = deepcopy((a, b))
        assert json_equal(a, b) is expected
        assert json_equal(b, a) is expected
        assert (a, b) == before


def test_huge_integer_without_python_int_conversion():
    assert json_equal(parse_json(b'9' * 5001), parse_json(b'9' * 5001 + b'.0'))
    assert not json_equal(parse_json(b'9' * 5001), parse_json(b'8' + b'9' * 5000))
    assert json_equal(1, Decimal('1.000'))


@pytest.mark.parametrize("value", [1.0, float('nan'), (1,), {1: 'bad'}])
def test_unsafe_comparison_never_silently_coerces(value):
    with pytest.raises(ProcessingError):
        json_equal(value, value)


def test_cyclic_comparison_fails_as_processing():
    value = []
    value.append(value)
    with pytest.raises(ProcessingError):
        json_equal(value, value)


@pytest.mark.parametrize("raw,locations", [
    (None, ['']), ([], ['']), ({}, ['/base_revision', '/mode', '/spec_id']),
    ({'mode': True, 'spec_id': '', 'base_revision': False}, ['/base_revision', '/mode', '/spec_id']),
    ({'mode': 'update', 'spec_id': 's', 'base_revision': '1'}, ['/base_revision']),
    ({'mode': 'update', 'spec_id': 's', 'base_revision': Decimal('1.1')}, ['/base_revision']),
    ({'mode': 'update', 'spec_id': 's', 'base_revision': 0}, ['/base_revision']),
    ({'mode': 'create', 'spec_id': None, 'base_revision': None, 'x/~': 123}, ['/x~1~0']),
    ({'mode': 'create', 'spec_id': None, 'base_revision': None, '': 123}, ['/']),
])
def test_unrepresentable_request_preserves_actual_and_missing(raw, locations):
    before = deepcopy(raw)
    projected, errors = inspect_request(raw)
    assert projected is None and raw == before
    assert [e['pointer'] for e in errors] == locations
    assert all(e['code'] == 'INVALID_REQUEST' and e['target'] == 'request' for e in errors)
    for e in errors:
        field = e['details']['field']
        assert ('actual' in e['details']) is (type(raw) is not dict or field in raw)


@pytest.mark.parametrize("context,expected_locations", [
    ({'mode': 'create', 'spec_id': 's', 'base_revision': 1}, ['/base_revision', '/spec_id']),
    ({'mode': 'update', 'spec_id': None, 'base_revision': None}, ['/base_revision', '/spec_id']),
    ({'mode': 'create', 'spec_id': None, 'base_revision': None}, []),
    ({'mode': 'update', 'spec_id': 's', 'base_revision': Decimal('1.0')}, []),
])
def test_representable_request_kept_even_if_routing_invalid(context, expected_locations):
    projected, errors = inspect_request(context)
    assert projected == context
    assert [e['pointer'] for e in errors] == expected_locations


def test_decision_checks_base_before_equality(monkeypatch):
    import dacn_s01.revision as revision
    def must_not_compare(*args):
        raise AssertionError('stale base must stop before equality')
    monkeypatch.setattr(revision, 'json_equal', must_not_compare)
    request = {'mode': 'update', 'spec_id': 's', 'base_revision': 1}
    head = {'revision': 2, 'input': {'title': 'same'}}
    decision = decide_revision(request, head['input'], head)
    assert decision.result_kind is None
    assert decision.errors[0]['code'] == 'REVISION_CONFLICT'
    assert decision.errors[0]['details'] == {'expected_revision': 2, 'provided_revision': 1}


def test_pure_decision_modes():
    create = {'mode': 'create', 'spec_id': None, 'base_revision': None}
    update = {'mode': 'update', 'spec_id': 's', 'base_revision': 2}
    head = {'revision': 2, 'input': {'value': 2}}
    assert decide_revision(create, {'value': 2}, None).result_kind == 'new_spec'
    assert decide_revision(update, {'value': 2}, head).result_kind == 'unchanged'
    assert decide_revision(update, {'value': 1}, head).result_kind == 'new_revision'
    missing = decide_revision(update, {'value': 1}, None)
    assert missing.errors[0]['code'] == 'SPEC_NOT_FOUND'
