"""Synthetic byte fixtures, not clinic dataset or illustrative envelopes."""

import copy
import json
import re
from collections import namedtuple
from decimal import Decimal, InvalidOperation, localcontext

import pytest
import simplejson

from dacn_s01.codec import (
    DuplicateKeyError, InvalidJSONError, ProcessingError,
    UnsupportedValueError, parse_json, serialize_json,
)


@pytest.mark.parametrize("raw,key", [
    (b'{"a":1,"a":2}', "a"),
    (b'{"x":{"a":null,"a":false}}', "a"),
    (b'[{"a":1,"a":2}]', "a"),
    (b'{"constraints":[{"constraint":{"value":{"a":1,"a":2}}}]}', "a"),
    (br'{"a":1,"\u0061":2}', "a"),
    (br'{"\ud83d\ude00":1,"\ud83d\ude00":2}', "😀"),
    ('{"😀":1,"\\ud83d\\ude00":2}'.encode(), "😀"),
    (br'{"a/b~c":1,"a\/b~c":2}', "a/b~c"),
])
def test_duplicate_keys_are_not_overwritten(raw, key):
    before = raw[:]
    with pytest.raises(DuplicateKeyError) as caught:
        parse_json(raw)
    assert caught.value.code == "DUPLICATE_JSON_KEY"
    assert caught.value.key == key
    assert not hasattr(caught.value, "pointer")
    assert not hasattr(caught.value, "byte_offset")
    assert raw == before


def test_same_key_in_separate_objects_and_exact_unicode_keys():
    result = parse_json('[{"a":1},{"a":2},{"é":true,"é":false}]'.encode())
    assert result[0]["a"] == Decimal("1")
    assert result[1]["a"] == Decimal("2")
    assert list(result[2]) == ["é", "é"]
    assert len(result[2]) == 2


@pytest.mark.parametrize("raw", [
    b'', b' ', b'{', b'{"x":}', b'{"x":1,}', b'[1,]', b'01', b'1.',
    b'+1', b'.1', b'1e', b'1e+', b'true false', b'// comment\n1',
    b'NaN', b'Infinity', b'-Infinity', b'[NaN]', b'{"n":Infinity}',
    b'"raw\nnewline"', b'"\\x41"', b'"\\u12xx"', b'"\xff"',
    b'\xef\xbb\xbf\xef\xbb\xbf{}',
])
def test_invalid_json(raw):
    with pytest.raises(InvalidJSONError) as caught:
        parse_json(raw)
    assert caught.value.code == "INVALID_JSON"
    assert not hasattr(caught.value, "byte_offset")


@pytest.mark.parametrize("raw,expected,kind", [
    (b'null', None, type(None)), (b'true', True, bool), (b'false', False, bool),
    (b'"hi"', "hi", str), (b'[]', [], list), (b'{}', {}, dict),
    (b'1', Decimal("1"), Decimal), (b'1.5', Decimal("1.5"), Decimal),
])
def test_all_root_types_are_codec_values(raw, expected, kind):
    result = parse_json(raw)
    assert type(result) is kind
    assert result == expected


NUMBER_TOKENS = [
    "9007199254740993", "9" * 5001,
    "1234567890.123456789012345678901234567890123456789",
    "1e400", "123456789012345678901234567890e-399", "-0", "-0.000",
    "0.0000000000000000000000000000000000000000000000000000000123456789",
    "1.2300", "1E+50",
]
JSON_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


@pytest.mark.parametrize("token", NUMBER_TOKENS, ids=[
    "above-binary64", "5001-digits", "long-fraction", "exponent-400",
    "negative-exponent", "negative-zero", "negative-zero-fraction",
    "small-fraction", "trailing-zeros", "exponent-plus",
])
def test_exact_number_roundtrip_with_independent_oracles(token):
    # Independent expected value from source, not codec output; no float.
    expected = Decimal(token)
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.Emax = 9
        ctx.Emin = -9
        first = parse_json(token.encode("ascii"))
        assert type(first) is Decimal
        assert first.as_tuple() == expected.as_tuple()
        encoded = serialize_json(first)
        # A JSON numeric token, not a quoted number, null or nonstandard constant.
        assert JSON_NUMBER.fullmatch(encoded.decode("ascii"))
        independent = simplejson.loads(encoded, use_decimal=True, parse_int=Decimal)
        assert type(independent) is Decimal
        assert independent.as_tuple() == expected.as_tuple()
        again = parse_json(encoded)
        assert type(again) is Decimal
        assert again.as_tuple() == expected.as_tuple()
    if len(token) == 5001:
        assert first.as_tuple().digits == (9,) * 5001


def test_preserve_structure_strings_unknowns_and_no_defaults():
    raw = ('{"id":" R1 ","text":"  khám\\n ","priority":null,'
           '"criteria":["second","first","first"],"unknown":null,'
           '"numbers":[true,1,false,0],"é":"é","empty":[],"a/b~c":{}}').encode()
    before = raw[:]
    value = parse_json(raw)
    expected = {"id": " R1 ", "text": "  khám\n ", "priority": None,
                "criteria": ["second", "first", "first"], "unknown": None,
                "numbers": [True, Decimal("1"), False, Decimal("0")],
                "é": "é", "empty": [], "a/b~c": {}}
    assert value == expected
    assert "schema_version" not in value and "details" not in value
    assert "unknown" in value and value["unknown"] is None
    saved = copy.deepcopy(value)
    encoded = serialize_json(value)
    independent = simplejson.loads(encoded, use_decimal=True, parse_int=Decimal)
    assert independent == expected
    assert list(independent) == list(expected)
    assert [type(x) for x in independent["numbers"]] == [bool, Decimal, bool, Decimal]
    assert value == saved and raw == before


@pytest.mark.parametrize("encoding,bom", [
    ("utf-8", b""), ("utf-8", b"\xef\xbb\xbf"),
    ("utf-16-le", b""), ("utf-16-le", b"\xff\xfe"),
    ("utf-16-be", b""), ("utf-16-be", b"\xfe\xff"),
    ("utf-32-le", b""), ("utf-32-le", b"\xff\xfe\x00\x00"),
    ("utf-32-be", b""), ("utf-32-be", b"\x00\x00\xfe\xff"),
])
def test_encoding_and_bom(encoding, bom):
    raw = bom + '{"khám":"😀","n":9007199254740993}'.encode(encoding)
    value = parse_json(raw)
    assert value == {"khám": "😀", "n": Decimal("9007199254740993")}
    assert serialize_json(value).isascii()


@pytest.mark.parametrize("raw,expected", [
    (br'"\ud800"', "\ud800"), (b'"\xed\xa0\x80"', "\ud800"),
    (br'"\ud83d\ude00"', "😀"), (br'"\ufeff"', "\ufeff"),
    (br'"\u200b"', "\u200b"), (br'"\u001c"', "\u001c"),
])
def test_unicode_not_normalized_or_filtered(raw, expected):
    value = parse_json(raw)
    assert value == expected
    output = serialize_json(value)
    assert output.isascii()
    assert json.loads(output) == expected


class WithFallback:
    def for_json(self):
        raise AssertionError("for_json fallback must not execute")

    def __iter__(self):
        raise AssertionError("iterable fallback must not execute")


class IntSubclass(int):
    pass


class StrSubclass(str):
    pass


@pytest.mark.parametrize("value", [
    1.0, float("nan"), float("inf"), float("-inf"),
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"),
    (1, 2), {1, 2}, b"text", bytearray(b"text"), object(), WithFallback(),
    namedtuple("Pair", "x y")(1, 2), IntSubclass(1), StrSubclass("x"),
    {1: "value"}, {None: "value"}, {StrSubclass("x"): "value"},
    {"nested": [1.5]}, {"nested": {"x": Decimal("NaN")}},
])
def test_reject_unsupported_internal_values(value):
    with pytest.raises(UnsupportedValueError) as caught:
        serialize_json(value)
    assert caught.value.code == "PROCESSING_FAILED"


@pytest.mark.parametrize("raw", ["{}", bytearray(b"{}"), memoryview(b"{}"), None])
def test_parse_api_requires_bytes(raw):
    with pytest.raises(UnsupportedValueError):
        parse_json(raw)


def test_cycle_rejected_but_shared_child_allowed():
    cycle = []
    cycle.append(cycle)
    with pytest.raises(UnsupportedValueError, match="Cyclic"):
        serialize_json(cycle)
    assert cycle[0] is cycle
    child = {"a": Decimal("2")}
    assert serialize_json([child, child]) == b'[{"a":2},{"a":2}]'


@pytest.mark.parametrize("trapped", [True, False])
def test_valid_number_beyond_decimal_limit_is_processing_failure(trapped):
    # Legal JSON number grammar; exponent exceeds libmpdec representation.
    token = "1e99999999999999999999999999999999999999999999999"
    assert JSON_NUMBER.fullmatch(token)
    with localcontext() as ctx:
        ctx.traps[InvalidOperation] = trapped
        with pytest.raises(ProcessingError) as caught:
            parse_json(token.encode())
    assert caught.value.code == "PROCESSING_FAILED"
    assert not isinstance(caught.value, InvalidJSONError)


def test_deep_valid_json_reports_resource_limit():
    raw = b"[" * 10000 + b"0" + b"]" * 10000
    with pytest.raises(ProcessingError):
        parse_json(raw)
    value = None
    for _ in range(10000):
        value = [value]
    with pytest.raises(ProcessingError):
        serialize_json(value)


def test_internal_integer_limit_is_explicit_not_string_or_null():
    # Python int->str has a configured digit limit. Payload numbers use Decimal.
    import sys
    assert sys.get_int_max_str_digits() == 4300
    with pytest.raises(ProcessingError):
        serialize_json(10 ** 5000)
    assert serialize_json(9007199254740993) == b"9007199254740993"


def test_selected_real_encoder_is_exercised(pytestconfig):
    assert serialize_json({"n": Decimal("1.25")}) == b'{"n":1.25}'
    selected = pytestconfig.getoption("--encoder-backend")
    other = "python" if selected == "c" else "c"
    assert pytestconfig.encoder_counts[selected] > 0
    assert pytestconfig.encoder_counts[other] == 0


@pytest.mark.parametrize("is_key", [False, True])
def test_literal_surrogate_pair_cannot_silently_collapse(is_key):
    # CPython surrogatepass accepts this byte sequence as two code points.
    # Escaping the pair would instead decode to one astral character.
    raw_string = b'"\xed\xa0\xbd\xed\xb8\x80"'
    raw = b"{" + raw_string + b":null}" if is_key else raw_string
    value = parse_json(raw)
    text = next(iter(value)) if is_key else value
    assert [ord(c) for c in text] == [0xD83D, 0xDE00]
    with pytest.raises(ProcessingError, match="surrogate"):
        serialize_json(value)
    assert [ord(c) for c in text] == [0xD83D, 0xDE00]
