"""Exact JSON values, independent of requirements schema and transport.

Input is immutable bytes; output is ASCII JSON bytes (also valid UTF-8).
Parse retains decoded values, not lexical number/escape/encoding choices.
Callers must retain original bytes separately when they need source evidence.
"""

from __future__ import annotations

import json
from decimal import Decimal, DecimalException
from typing import Literal, NoReturn

import simplejson

type JSONValue = None | bool | str | int | Decimal | list[JSONValue] | dict[str, JSONValue]
type ErrorCode = Literal["INVALID_JSON", "DUPLICATE_JSON_KEY", "PROCESSING_FAILED"]


class CodecError(Exception):
    """Internal failure; code/reason can be mapped by a future S01 adapter.

    No source pointer or byte offset is claimed: json's hook has neither,
    and JSONDecodeError.pos counts decoded characters rather than raw bytes.
    """

    code: ErrorCode

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class InvalidJSONError(CodecError):
    code = "INVALID_JSON"


class DuplicateKeyError(CodecError):
    code = "DUPLICATE_JSON_KEY"

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Duplicate decoded object key: {ascii(key)}")


class ProcessingError(CodecError):
    code = "PROCESSING_FAILED"


class UnsupportedValueError(ProcessingError):
    """Caller supplied a value outside the internal exact JSON types."""


def _unique_object(pairs: list[tuple[str, JSONValue]]) -> dict[str, JSONValue]:
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise DuplicateKeyError(key)
        seen.add(key)
    return dict(pairs)


def _reject_constant(token: str) -> NoReturn:
    raise InvalidJSONError(f"Non-JSON numeric constant: {token}")


def _decimal_token(token: str) -> Decimal:
    try:
        value = Decimal(token)
    except (DecimalException, ValueError, OverflowError) as exc:
        raise ProcessingError("JSON number exceeds Decimal representation limits") from exc
    # Decimal can return NaN instead of raising when InvalidOperation is untrapped.
    if not value.is_finite():
        raise ProcessingError("JSON number exceeds Decimal representation limits")
    return value


def parse_json(raw: bytes) -> JSONValue:
    """Parse any JSON root; all numeric tokens become exact finite Decimal.

    Uses CPython's bytes encoding detection: UTF-8/16/32, with/without BOM.
    No requirements defaults, whitespace profile or root-object check occurs.
    """
    if type(raw) is not bytes:
        raise UnsupportedValueError("parse_json requires bytes")
    try:
        return json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_int=_decimal_token,
            parse_float=_decimal_token,
            parse_constant=_reject_constant,
            strict=True,
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidJSONError("Malformed JSON syntax or invalid byte encoding") from exc
    except (RecursionError, MemoryError, OverflowError) as exc:
        raise ProcessingError("JSON parsing exceeded runtime resource limits") from exc


def _check_string(value: str) -> None:
    previous_high_surrogate = False
    for char in value:
        point = ord(char)
        if previous_high_surrogate and 0xDC00 <= point <= 0xDFFF:
            raise ProcessingError(
                "Adjacent literal surrogate code points cannot be preserved by ASCII JSON escaping"
            )
        previous_high_surrogate = 0xD800 <= point <= 0xDBFF


def _preflight(value: JSONValue, ancestors: set[int]) -> None:
    kind = type(value)
    if kind is str:
        _check_string(value)
        return
    if value is None or kind in (bool, int):
        return
    if kind is Decimal:
        if not value.is_finite():
            raise UnsupportedValueError("JSON numbers must be finite")
        return
    if kind not in (list, dict):
        raise UnsupportedValueError(f"Unsupported internal JSON type: {kind.__name__}")
    identity = id(value)
    if identity in ancestors:
        raise UnsupportedValueError("Cyclic containers are not JSON values")
    ancestors.add(identity)
    try:
        if kind is dict:
            for key, child in value.items():
                if type(key) is not str:
                    raise UnsupportedValueError("JSON object keys must be exact str values")
                _check_string(key)
                _preflight(child, ancestors)
        else:
            for child in value:
                _preflight(child, ancestors)
    finally:
        ancestors.remove(identity)


def serialize_json(value: JSONValue) -> bytes:
    """Serialize a concrete JSON tree without coercion or fallback values.

    Allowed exact types: NoneType, bool, str, int, finite Decimal, list, dict.
    Subclasses, float, tuple, custom objects and cycles are rejected.
    Returns complete bytes only; caller-owned containers must not be mutated
    concurrently during this synchronous operation.
    """
    try:
        _preflight(value, set())
        return simplejson.dumps(
            value,
            use_decimal=True,
            allow_nan=False,
            ignore_nan=False,
            bigint_as_string=False,
            int_as_string_bitcount=None,
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            namedtuple_as_object=False,
            tuple_as_array=False,
            iterable_as_array=False,
            for_json=False,
            default=None,
            sort_keys=False,
            indent=None,
            separators=(",", ":"),
        ).encode("ascii")
    except (RecursionError, MemoryError, OverflowError, DecimalException) as exc:
        raise ProcessingError("JSON serialization exceeded runtime representation limits") from exc
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ProcessingError("Encoder could not represent the checked JSON tree exactly") from exc
