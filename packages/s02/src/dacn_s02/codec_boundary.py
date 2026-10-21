"""Public S01 codec only; local errors, no input-profile validator/coercion."""
from dacn_s01.codec import parse_json, serialize_json, CodecError, DuplicateKeyError
from .errors import S02Error


def decode(raw):
    try:
        return parse_json(raw)
    except CodecError as exc:
        code = "DUPLICATE_KEY" if isinstance(exc, DuplicateKeyError) else exc.code
        stage = "parse" if code in ("INVALID_JSON", "DUPLICATE_KEY") else "schema"
        raise S02Error(code, stage, "Cannot decode exact JSON", details={"reason":ascii(exc.reason)}) from exc


def encode(value):
    try:
        return serialize_json(value)
    except CodecError as exc:
        raise S02Error("PROCESSING_FAILED", "schema", "Cannot encode exact JSON",
                       details={"reason":ascii(exc.reason)}) from exc
