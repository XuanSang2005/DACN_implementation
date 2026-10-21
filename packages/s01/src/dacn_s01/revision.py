"""Pure request checks and revision decisions; no IDs, clock, SQL or I/O."""

from dataclasses import dataclass

from .codec import JSONValue, serialize_json
from .errors import Error, error, ordered_errors, pointer
from .validation import is_integer, is_number


def json_equal(left: JSONValue, right: JSONValue) -> bool:
    """Compare exact JSON values under draft.2, rejecting unsafe internal types.

    Preflight uses the same codec as persistence, including cycle/resource limits.
    Equality never compares floats, hashes, serialized bytes or normalized text.
    """
    serialize_json(left)
    serialize_json(right)

    def equal(a, b):
        if is_number(a) and is_number(b):
            return a == b
        if type(a) is not type(b):
            return False
        if type(a) is dict:
            return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
        if type(a) is list:
            return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        return a == b

    return equal(left, right)


def inspect_request(raw: JSONValue) -> tuple[dict | None, list[Error]]:
    """Return representable context and independent request errors.

    Callers may capture representability before input validation, but must only
    publish these errors/run the revision check after input checks have passed.
    Missing fields have no fabricated actual:null. The original is never edited.
    """
    issues = []

    def invalid(name, reason, present=True, value=None):
        details = {"field": "" if name is None else name, "reason": reason}
        if present:
            details["actual"] = value
        issues.append(error("INVALID_REQUEST", "revision", "" if name is None else pointer([name]),
                            "Request cannot be used", details, target="request"))

    if type(raw) is not dict:
        invalid(None, "Request must be an object", value=raw)
        return None, issues
    fields = ("mode", "spec_id", "base_revision")
    for name in fields:
        if name not in raw:
            invalid(name, "Required request field is missing", present=False)
    for name in raw.keys() - set(fields):
        invalid(name, "Unknown request field", value=raw[name])
    if "mode" in raw and (type(raw["mode"]) is not str or raw["mode"] not in ("create", "update")):
        invalid("mode", "Mode must be create or update", value=raw["mode"])
    if "spec_id" in raw and raw["spec_id"] is not None:
        if type(raw["spec_id"]) is not str or not raw["spec_id"]:
            invalid("spec_id", "Spec ID must be a nonempty string or null", value=raw["spec_id"])
    if "base_revision" in raw and raw["base_revision"] is not None:
        if not is_integer(raw["base_revision"]) or raw["base_revision"] < 1:
            invalid("base_revision", "Base revision must be a positive integer or null", value=raw["base_revision"])
    if issues:
        return None, ordered_errors(issues)
    for name in ("spec_id", "base_revision"):
        if raw["mode"] == "create" and raw[name] is not None:
            invalid(name, "Create requires null routing fields", value=raw[name])
        elif raw["mode"] == "update" and raw[name] is None:
            invalid(name, "Update requires a spec ID and base revision", value=raw[name])
    return dict(raw), ordered_errors(issues)


@dataclass(frozen=True)
class RevisionDecision:
    result_kind: str | None
    errors: tuple[Error, ...] = ()


def decide_revision(request: dict, normalized: dict, head: dict | None) -> RevisionDecision:
    """Request must have passed inspect_request; head must come from the transaction.

    This function never fetches a stale head or retries/rebases an update.
    """
    if request["mode"] == "create":
        return RevisionDecision("new_spec")
    if head is None:
        return RevisionDecision(None, (error("SPEC_NOT_FOUND", "revision", "/spec_id",
            "Specification does not exist", {"spec_id": request["spec_id"]}, target="request"),))
    if request["base_revision"] != head["revision"]:
        return RevisionDecision(None, (error("REVISION_CONFLICT", "revision", "/base_revision",
            "Base revision is no longer current", {"expected_revision": head["revision"],
             "provided_revision": request["base_revision"]}, target="request"),))
    return RevisionDecision("unchanged" if json_equal(normalized, head["input"]) else "new_revision")
