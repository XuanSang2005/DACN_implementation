"""S01 input checks through cross_field, with revision deliberately not_run.

Passing this module is not a committed S01 result, semantic review or S02 handoff.
Only schema_version may be added, and only when the key is absent.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from jsonschema import Draft202012Validator, ValidationError, validators

from .codec import CodecError, JSONValue, ProcessingError, parse_json
from .errors import Error, error, ordered_errors, pointer
from .schema_resource import INPUT_VERSION, SCHEMA_SHA256, load_schema

# Frozen contract profile, independent of runtime Unicode/regex whitespace tables.
W = frozenset(chr(point) for point in (
    0x0009, 0x000A, 0x000B, 0x000C, 0x000D,
    0x001C, 0x001D, 0x001E, 0x001F, 0x0020, 0x0085, 0x00A0, 0x1680,
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007,
    0x2008, 0x2009, 0x200A, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000,
))
GROUPS = ("functional_requirements", "non_functional_requirements", "constraints")
METRICS = ("response_time_p95", "sustainable_throughput", "cpu_utilisation", "scaling_gain")
NORMALIZATION = {"operation": "add", "input_pointer": "/schema_version",
                 "value": "1.0.0", "reason": "LEGACY_SCHEMA_VERSION"}
type Check = Literal["passed", "failed", "not_run"]


def nonblank(value: str) -> bool:
    return any(char not in W for char in value)


def surrounding_whitespace(value: str) -> bool:
    return bool(value) and (value[0] in W or value[-1] in W)


def is_number(value: object) -> bool:
    return type(value) is int or (type(value) is Decimal and value.is_finite())


def is_integer(value: object) -> bool:
    if type(value) is int:
        return True
    if type(value) is not Decimal or not value.is_finite():
        return False
    parts = value.as_tuple()
    return parts.exponent >= 0 or not any(parts.digits[parts.exponent:])


def json_type(value: JSONValue) -> str:
    if value is None:
        return "null"
    if is_number(value):
        return "number"
    return {bool: "boolean", str: "string", list: "array", dict: "object"}[type(value)]


def _pattern_w(validator, pattern, instance, schema):
    if pattern != r"\S":
        raise ProcessingError("Unexpected pattern in the fixed input schema profile")
    if type(instance) is str and not nonblank(instance):
        yield ValidationError("String must contain a code point outside contract W")


_types = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "number": lambda _, value: is_number(value),
    "integer": lambda _, value: is_integer(value),
    "boolean": lambda _, value: type(value) is bool,
    "string": lambda _, value: type(value) is str,
    "object": lambda _, value: type(value) is dict,
    "array": lambda _, value: type(value) is list,
    "null": lambda _, value: value is None,
})
ProfileValidator = validators.extend(
    Draft202012Validator, {"pattern": _pattern_w}, type_checker=_types,
)


def _schema_locations(schema: dict) -> dict[int, str]:
    """Locate actual resource nodes, including nodes reached through $ref."""
    locations = {}

    def visit(node, path):
        if type(node) is dict:
            locations[id(node)] = pointer(path)
            if "pattern" in node and node["pattern"] != r"\S":
                raise ProcessingError("Unexpected pattern in the fixed input schema profile")
            if "$ref" in node and not node["$ref"].startswith("#/"):
                raise ProcessingError("Input schema profile permits local references only")
            for key, child in node.items():
                visit(child, (*path, key))
        elif type(node) is list:
            for index, child in enumerate(node):
                visit(child, (*path, index))

    visit(schema, ())
    return locations


def _expected_types(schema: dict, root: dict) -> list[str]:
    if "$ref" in schema:
        node = root
        for part in schema["$ref"][2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return _expected_types(node, root)
    if "type" in schema:
        types = schema["type"]
        return [types] if type(types) is str else list(types)
    return list(dict.fromkeys(t for child in schema.get("anyOf", [])
                             for t in _expected_types(child, root)))


def _schema_errors(problem: ValidationError, root: dict, locations: dict[int, str]) -> list[Error]:
    path = tuple(problem.absolute_path)
    location = pointer(path)
    value = problem.instance
    keyword = problem.validator

    def issue(code, details, message):
        return [error(code, "schema", location, message, details)]

    if len(path) == 3 and path[0] in GROUPS and path[2] == "priority":
        allowed = ["must"] if path[0] == "constraints" else ["must", "should", "could", None]
        return issue("INVALID_PRIORITY", {"actual": value, "allowed": allowed}, "Priority is not allowed")
    metrics_path = ("design_preferences", "metric_priorities")
    if len(path) == 3 and path[:2] == metrics_path:
        return issue("INVALID_METRIC", {"actual": value, "allowed": list(METRICS)}, "Metric is not allowed")
    if keyword == "anyOf":
        # Relative schema paths start with the anyOf branch index, including
        # branches reached through a local $ref. Only a branch's own type
        # failure at this instance excludes it; nested type errors must survive.
        wrong_type_branches = {
            child.schema_path[0] for child in problem.context
            if child.validator == "type" and tuple(child.absolute_path) == path
            and len(child.schema_path) == 2 and child.schema_path[1] == "type"
        }
        meaningful = [child for child in problem.context
                      if child.schema_path[0] not in wrong_type_branches]
        if meaningful:
            return [item for child in meaningful for item in _schema_errors(child, root, locations)]
        return issue("TYPE_MISMATCH", {"expected_types": _expected_types(problem.schema, root),
                                       "actual_type": json_type(value)}, "JSON type is not allowed")
    if keyword == "type":
        return issue("TYPE_MISMATCH", {"expected_types": _expected_types(problem.schema, root),
                                       "actual_type": json_type(value)}, "JSON type is not allowed")
    if keyword in ("pattern", "minLength") and type(value) is str:
        return issue("EMPTY_OR_WHITESPACE", {"actual": value}, "String is empty or contains only contract W")
    if keyword == "required":
        return [error("MISSING_FIELD", "schema", pointer((*path, name)),
                      "Required field is missing", {"field": name})
                for name in problem.validator_value if name not in value]
    if keyword == "additionalProperties":
        return [error("UNKNOWN_FIELD", "schema", pointer((*path, name)),
                      "Field is outside the input schema", {"field": name})
                for name in value if name not in problem.schema.get("properties", {})]
    if keyword in ("minItems", "maxItems") and path == metrics_path:
        return issue("METRIC_COUNT", {"expected": 4, "actual": len(value)}, "Exactly four metrics are required")
    if keyword == "uniqueItems" and path in (("actors",), metrics_path):
        code = "DUPLICATE_ACTOR" if path == ("actors",) else "DUPLICATE_METRIC"
        seen = {}
        result = []
        for index, item in enumerate(value):
            if type(item) is not str:  # Type/enum error already describes invalid elements.
                continue
            if item in seen:
                result.append(error(code, "schema", pointer((*path, index)),
                                    "Value repeats an earlier element", {"value": item},
                                    related=[pointer((*path, seen[item]))]))
            else:
                seen[item] = index
        return result
    schema_location = locations.get(id(problem.schema))
    if schema_location is None:
        raise ProcessingError("Cannot locate failing keyword in the schema resource")
    return issue("SCHEMA_VIOLATION", {"keyword": keyword,
                                     "schema_pointer": schema_location + pointer([keyword])},
                 "Input violates a schema constraint")


def _cross_field(value: dict[str, JSONValue]) -> list[Error]:
    result = []
    seen = {}
    for group in GROUPS:
        for index, requirement in enumerate(value[group]):
            identifier = requirement["id"]
            location = pointer((group, index, "id"))
            if surrounding_whitespace(identifier):
                result.append(error("ID_SURROUNDING_WHITESPACE", "cross_field", location,
                                    "ID has contract W at its boundary", {"actual": identifier}))
            if identifier in seen:
                result.append(error("DUPLICATE_REQUIREMENT_ID", "cross_field", location,
                                    "ID must be unique across FR, NFR and constraints",
                                    {"requirement_id": identifier}, related=[seen[identifier]]))
            else:
                seen[identifier] = location
    return result


@dataclass
class InputValidation:
    """Internal result only: revision not checked, no commit or handoff claim.

    normalized_input exists only when all three input checks passed.
    input_version and normalizations remain available even if later checks fail.
    """

    checks: dict[str, Check] = field(default_factory=lambda: dict.fromkeys(
        ("parse", "schema", "cross_field", "revision"), "not_run"))
    errors: list[Error] = field(default_factory=list)
    input_version: dict[str, str | None] = field(default_factory=lambda: {
        "origin": "unresolved", "resolved": None})
    normalizations: list[dict[str, str]] = field(default_factory=list)
    input_schema_sha256: str | None = None
    normalized_input: dict[str, JSONValue] | None = None

    @property
    def outcome(self) -> Literal["passed", "rejected", "failed"]:
        if any(item["stage"] == "system" for item in self.errors):
            return "failed"
        if self.errors:
            return "rejected"
        return "passed" if all(self.checks[s] == "passed" for s in ("parse", "schema", "cross_field")) else "failed"


def validate_input(raw: bytes) -> InputValidation:
    """Run parse → version/normalization/schema → cross_field, in this order."""
    result = InputValidation()
    stage = "parse"
    try:
        try:
            value = parse_json(raw)
        except CodecError as exc:
            if exc.code == "PROCESSING_FAILED":
                raise
            result.checks["parse"] = "failed"
            result.errors = [error(exc.code, "parse", None, "Cannot parse input JSON", {"reason": exc.reason})]
            return result
        result.checks["parse"] = "passed"
        stage = "schema"
        if type(value) is not dict:
            result.errors = [error("TYPE_MISMATCH", "schema", "", "Input root must be an object",
                                   {"expected_types": ["object"], "actual_type": json_type(value)})]
        elif "schema_version" not in value:
            value = dict(value)
            value["schema_version"] = INPUT_VERSION
            result.input_version = {"origin": "legacy_default", "resolved": INPUT_VERSION}
            result.normalizations = [dict(NORMALIZATION)]
        else:
            version = value["schema_version"]
            if type(version) is not str or not nonblank(version) or surrounding_whitespace(version):
                code = "INVALID_SCHEMA_VERSION"
            elif version != INPUT_VERSION:
                code = "UNSUPPORTED_SCHEMA_VERSION"
            else:
                code = None
            if code:
                result.errors = [error(code, "schema", "/schema_version", "Input schema version cannot be used",
                                       {"actual": version, "supported": [INPUT_VERSION]})]
            else:
                result.input_version = {"origin": "explicit", "resolved": INPUT_VERSION}
        if not result.errors:
            schema = load_schema()
            result.input_schema_sha256 = SCHEMA_SHA256
            locations = _schema_locations(schema)
            result.errors = ordered_errors(item for problem in ProfileValidator(schema).iter_errors(value)
                                           for item in _schema_errors(problem, schema, locations))
        if result.errors:
            result.checks["schema"] = "failed"
            return result
        result.checks["schema"] = "passed"
        stage = "cross_field"
        result.errors = ordered_errors(_cross_field(value))
        result.checks["cross_field"] = "failed" if result.errors else "passed"
        if not result.errors:
            result.normalized_input = value
        return result
    except Exception as exc:
        # Boundary converts tool/configuration failures, never into input rejection.
        # Do not expose arbitrary library exceptions or payload-bearing tracebacks.
        result.checks[stage] = "failed"
        reason = exc.reason if isinstance(exc, ProcessingError) else "Input checking could not complete reliably"
        result.errors = [error("PROCESSING_FAILED", "system", None, "Input processing failed",
                               {"reason": reason}, target="system")]
        result.normalized_input = None
        return result
