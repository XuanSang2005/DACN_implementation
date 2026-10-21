import copy
from decimal import Decimal, localcontext
import itertools

import pytest
from jsonschema import Draft202012Validator

from dacn_s01 import validation
from dacn_s01.codec import parse_json, serialize_json
from dacn_s01.errors import pointer
from dacn_s01.schema_resource import SchemaResourceError, load_schema
from dacn_s01.validation import ProfileValidator, validate_input


# Oracle explicitly from the contract, not imported from the implementation W.
EXPECTED_W = "\u0009\u000a\u000b\u000c\u000d\u001c\u001d\u001e\u001f\u0020\u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
W_IDS = [f"U+{ord(char):04X}" for char in EXPECTED_W]
GROUPS = ("functional_requirements", "non_functional_requirements", "constraints")
TEXT_PATHS = [("title",), ("context",), ("actors", 0), ("constraints", 0, "constraint", "kind")]
for group in GROUPS:
    TEXT_PATHS += [(group, 0, key) for key in ("id", "text", "title", "group")]
    TEXT_PATHS += [(group, 0, "acceptance_criteria", 0)]
    TEXT_PATHS += [(group, 0, "details", key) for key in ("trigger", "data", "business_rules", "exceptions")]
TEXT_PATHS += [("operating_conditions", key) for key in ("critical_scenarios", "expected_load", "peak_load", "data_volume", "growth", "resource_budget")]
TEXT_PATHS += [("project_details", key) for key in ("scope_exclusions", "external_systems", "data_context")]


def set_value(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def assert_error(result, code, location, details=None, stage="schema", related=()):
    assert result.outcome == "rejected"
    assert result.normalized_input is None
    found = [e for e in result.errors if e["code"] == code and e["pointer"] == location]
    assert len(found) == 1
    item = found[0]
    assert set(item) == {"code", "stage", "target", "pointer", "related_pointers", "message", "details"}
    assert item["stage"] == stage and item["target"] == "input"
    assert item["related_pointers"] == list(related)
    assert item["message"]
    if details is not None:
        assert item["details"] == details
    assert result.checks[stage] == "failed"
    assert result.checks["revision"] == "not_run"


def test_fixed_profile_and_no_default_regex_veto(monkeypatch):
    assert len(EXPECTED_W) == 29 and validation.W == set(EXPECTED_W)

    def veto(*args):
        raise AssertionError("Default regex handler must never run")

    monkeypatch.setitem(Draft202012Validator.VALIDATORS, "pattern", veto)
    engine = ProfileValidator({"type": "string", "pattern": r"\S"})
    assert list(engine.iter_errors("\ufeff")) == []
    assert list(engine.iter_errors("\u200b")) == []
    assert len(list(engine.iter_errors("\u001c"))) == 1


@pytest.mark.parametrize("char", list(EXPECTED_W), ids=W_IDS)
@pytest.mark.parametrize("path", [("title",), ("actors", 0), ("functional_requirements", 0, "id"), ("functional_requirements", 0, "acceptance_criteria", 0)])
def test_all_w_nonblank(payload, submit, char, path):
    set_value(payload, path, char)
    result = submit(payload)
    assert_error(result, "EMPTY_OR_WHITESPACE", pointer(path), {"actual": char})
    assert len(result.errors) == 1
    assert result.checks["cross_field"] == "not_run"


@pytest.mark.parametrize("path", TEXT_PATHS, ids=lambda p: pointer(p))
@pytest.mark.parametrize("blank", ["", "\t\u001c \u3000"])
def test_every_text_position_uses_profile(payload, submit, path, blank):
    set_value(payload, path, blank)
    result = submit(payload)
    assert_error(result, "EMPTY_OR_WHITESPACE", pointer(path), {"actual": blank})
    assert len(result.errors) == 1  # minLength/pattern and anyOf collapsed.


@pytest.mark.parametrize("char", list(EXPECTED_W), ids=W_IDS)
@pytest.mark.parametrize("side", ["left", "right"])
def test_all_w_id_boundaries(payload, submit, char, side):
    identifier = char + "R" if side == "left" else "R" + char
    payload["functional_requirements"][0]["id"] = identifier
    result = submit(payload)
    assert result.checks["schema"] == "passed"
    assert_error(result, "ID_SURROUNDING_WHITESPACE", "/functional_requirements/0/id",
                 {"actual": identifier}, stage="cross_field")


@pytest.mark.parametrize("char", list(EXPECTED_W), ids=W_IDS)
def test_w_inside_id_preserved(payload, submit, char):
    payload["functional_requirements"][0]["id"] = "R" + char + "1"
    result = submit(payload)
    assert result.outcome == "passed"
    assert result.normalized_input["functional_requirements"][0]["id"] == "R" + char + "1"


@pytest.mark.parametrize("char", ["\u200b", "\ufeff"])
@pytest.mark.parametrize("path", TEXT_PATHS, ids=lambda p: pointer(p))
def test_outside_w_not_vetoed(payload, submit, char, path):
    set_value(payload, path, char)
    assert submit(payload).outcome == "passed"


@pytest.mark.parametrize("char", list(EXPECTED_W), ids=W_IDS)
@pytest.mark.parametrize("form", ["only", "left", "right"])
def test_version_uses_same_w(payload, submit, char, form):
    version = char if form == "only" else char + "1.0.0" if form == "left" else "1.0.0" + char
    payload["schema_version"] = version
    result = submit(payload)
    assert_error(result, "INVALID_SCHEMA_VERSION", "/schema_version", {"actual": version, "supported": ["1.0.0"]})
    assert result.input_version == {"origin": "unresolved", "resolved": None}
    assert result.normalizations == []


@pytest.mark.parametrize("version,code", [(None, "INVALID_SCHEMA_VERSION"), (1, "INVALID_SCHEMA_VERSION"),
    (True, "INVALID_SCHEMA_VERSION"), ([], "INVALID_SCHEMA_VERSION"), ({}, "INVALID_SCHEMA_VERSION"),
    ("", "INVALID_SCHEMA_VERSION"), ("2.0.0", "UNSUPPORTED_SCHEMA_VERSION"),
    ("\ufeff1.0.0", "UNSUPPORTED_SCHEMA_VERSION"), ("\u200b", "UNSUPPORTED_SCHEMA_VERSION")])
def test_invalid_version_stops_before_schema_loading(payload, submit, monkeypatch, version, code):
    payload["schema_version"] = version
    payload.pop("title")
    monkeypatch.setattr(validation, "load_schema", lambda: pytest.fail("Gate must stop schema loading"))
    result = submit(payload)
    assert_error(result, code, "/schema_version")
    assert len(result.errors) == 1 and result.input_schema_sha256 is None


def test_preservation_and_legacy_only_default(payload):
    payload.pop("schema_version")
    payload["functional_requirements"][0].pop("title")
    payload["functional_requirements"][0]["id"] = "R\u001c1"
    payload["actors"] = ["Actor", "actor", " Actor", "é", "é"]
    raw = serialize_json(payload)
    result = validate_input(raw)
    assert result.outcome == "passed"
    assert result.checks == {"parse": "passed", "schema": "passed", "cross_field": "passed", "revision": "not_run"}
    assert result.input_version == {"origin": "legacy_default", "resolved": "1.0.0"}
    assert result.normalizations == [{"operation": "add", "input_pointer": "/schema_version", "value": "1.0.0", "reason": "LEGACY_SCHEMA_VERSION"}]
    expected = copy.deepcopy(payload)
    expected["schema_version"] = "1.0.0"
    assert result.normalized_input == expected
    assert "title" not in result.normalized_input["functional_requirements"][0]
    assert raw == serialize_json(payload)
    assert "schema_version" not in parse_json(raw)
    result.normalized_input["actors"].append("changed after result")
    assert "changed after result" not in payload["actors"]


def test_legacy_normalization_retained_on_failure(payload, submit):
    del payload["schema_version"], payload["context"]
    result = submit(payload)
    assert_error(result, "MISSING_FIELD", "/context", {"field": "context"})
    assert len(result.normalizations) == 1 and result.input_version["origin"] == "legacy_default"


@pytest.mark.parametrize("root", [None, [], "hi", True, 1])
def test_non_object_root_is_schema_error(submit, root):
    result = submit(root)
    assert_error(result, "TYPE_MISMATCH", "")
    assert result.checks["parse"] == "passed"
    assert result.input_version == {"origin": "unresolved", "resolved": None}
    assert result.normalizations == []


@pytest.mark.parametrize("raw,code", [(b'{', "INVALID_JSON"), (b'NaN', "INVALID_JSON"),
    (b'{"a":1,"a":2}', "DUPLICATE_JSON_KEY"), (br'{"a":1,"\u0061":2}', "DUPLICATE_JSON_KEY")])
def test_parse_error_mapping(raw, code):
    result = validate_input(raw)
    assert_error(result, code, None, stage="parse")
    assert set(result.errors[0]["details"]) == {"reason"}
    assert result.checks == {"parse": "failed", "schema": "not_run", "cross_field": "not_run", "revision": "not_run"}


@pytest.mark.parametrize("raw", [b"1e999999999999999999999999999999999999999", "not bytes"])
def test_parse_processing_failure_not_rejection(raw):
    result = validate_input(raw)
    assert result.outcome == "failed" and result.normalized_input is None
    assert result.errors[0]["code"] == "PROCESSING_FAILED"
    assert result.errors[0]["stage"] == result.errors[0]["target"] == "system"
    assert result.checks["schema"] == "not_run"


@pytest.mark.parametrize("codepath", ["load", "profile", "engine"])
def test_system_configuration_failure(payload, submit, monkeypatch, codepath):
    payload.pop("schema_version")
    if codepath == "load":
        def broken():
            raise SchemaResourceError("Synthetic broken resource")
        monkeypatch.setattr(validation, "load_schema", broken)
    elif codepath == "profile":
        schema = load_schema()
        schema["properties"]["title"]["pattern"] = "new-pattern"
        monkeypatch.setattr(validation, "load_schema", lambda: schema)
    else:
        def broken(*args):
            raise RuntimeError("private stack/payload must not leak")
        monkeypatch.setattr(validation.ProfileValidator, "iter_errors", broken)
    result = submit(payload)
    assert result.outcome == "failed"
    assert result.checks == {"parse": "passed", "schema": "failed", "cross_field": "not_run", "revision": "not_run"}
    assert result.errors[0]["code"] == "PROCESSING_FAILED"
    assert "private stack" not in str(result.errors)
    assert result.normalized_input is None and len(result.normalizations) == 1


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("priority", [True, 1, "urgent", [], {}])
def test_priority_specialized_errors(payload, submit, group, priority):
    payload[group][0]["priority"] = priority
    result = submit(payload)
    assert_error(result, "INVALID_PRIORITY", f"/{group}/0/priority")
    assert len(result.errors) == 1


@pytest.mark.parametrize("priority", [None, "should", "could"])
def test_constraint_priority_must(payload, submit, priority):
    payload["constraints"][0]["priority"] = priority
    result = submit(payload)
    assert_error(result, "INVALID_PRIORITY", "/constraints/0/priority", {"actual": priority, "allowed": ["must"]})


def test_cross_field_order_independent_of_object_key_order(payload, submit):
    for group in GROUPS:
        payload[group][0]["id"] = " R "
    payload["functional_requirements"].append(copy.deepcopy(payload["functional_requirements"][0]))
    result = submit(dict(reversed(list(payload.items()))))
    for path in ("/functional_requirements/1/id", "/non_functional_requirements/0/id", "/constraints/0/id"):
        assert_error(result, "DUPLICATE_REQUIREMENT_ID", path, {"requirement_id": " R "},
                     stage="cross_field", related=["/functional_requirements/0/id"])
    assert len(result.errors) == 7  # 4 boundary errors + 3 duplicate errors.
    assert [(e["pointer"], e["code"]) for e in result.errors] == sorted((e["pointer"], e["code"]) for e in result.errors)
    assert submit(payload).errors == result.errors


def test_cross_field_not_run_after_schema_failure(payload, submit):
    payload["constraints"][0]["id"] = "R"
    payload["actors"] = [None]
    result = submit(payload)
    assert result.checks["cross_field"] == "not_run"
    assert all(e["stage"] == "schema" for e in result.errors)


def test_actors_repeat_points_to_first(payload, submit):
    payload["actors"] = ["A", "A", "B", "A"]
    result = submit(payload)
    for index in (1, 3):
        assert_error(result, "DUPLICATE_ACTOR", f"/actors/{index}", {"value": "A"}, related=["/actors/0"])
    assert len(result.errors) == 2


def test_metrics_count_duplicate_and_invalid_are_independent(payload, submit):
    payload["design_preferences"]["metric_priorities"] = ["response_time_p95", "response_time_p95", True]
    result = submit(payload)
    assert_error(result, "METRIC_COUNT", "/design_preferences/metric_priorities", {"expected": 4, "actual": 3})
    assert_error(result, "DUPLICATE_METRIC", "/design_preferences/metric_priorities/1", {"value": "response_time_p95"}, related=["/design_preferences/metric_priorities/0"])
    assert_error(result, "INVALID_METRIC", "/design_preferences/metric_priorities/2")
    assert len(result.errors) == 3
    assert type(result.errors[-1]["details"]["actual"]) is bool


def test_all_metric_permutations_valid_and_preserved(payload, submit):
    metrics = payload["design_preferences"]["metric_priorities"]
    for permutation in itertools.permutations(metrics):
        payload["design_preferences"]["metric_priorities"] = list(permutation)
        result = submit(payload)
        assert result.outcome == "passed"
        assert result.normalized_input["design_preferences"]["metric_priorities"] == list(permutation)


@pytest.mark.parametrize("path", [(), ("functional_requirements", 0), ("functional_requirements", 0, "details"),
    ("constraints", 0, "constraint"), ("design_preferences",), ("operating_conditions",), ("project_details",)])
def test_unknown_fields_and_escaped_pointer(payload, submit, path):
    target = payload
    for key in path:
        target = target[key]
    target["extra~/"] = None
    result = submit(payload)
    assert_error(result, "UNKNOWN_FIELD", pointer((*path, "extra~/")), {"field": "extra~/"})
    assert len(result.errors) == 1


@pytest.mark.parametrize("path", [("context",), ("actors",), ("functional_requirements", 0, "acceptance_criteria"),
    ("operating_conditions", "expected_load"), ("constraints", 0, "constraint", "value")])
def test_required_missing_not_actual_null(payload, submit, path):
    target = payload
    for part in path[:-1]:
        target = target[part]
    del target[path[-1]]
    result = submit(payload)
    assert_error(result, "MISSING_FIELD", pointer(path), {"field": path[-1]})
    assert len(result.errors) == 1


@pytest.mark.parametrize("path,types", [(('functional_requirements', 0, 'title'), ['string', 'null']),
    (('functional_requirements', 0, 'details'), ['object', 'null']),
    (('project_details',), ['object', 'null']), (('actors',), ['array'])])
def test_anyof_wrong_type_gives_one_error(payload, submit, path, types):
    set_value(payload, path, 0)
    result = submit(payload)
    assert_error(result, "TYPE_MISMATCH", pointer(path), {"expected_types": types, "actual_type": "number"})
    assert len(result.errors) == 1


def test_empty_arrays_and_schema_pointer(payload, submit):
    payload["non_functional_requirements"] = []
    payload["constraints"] = []
    payload["functional_requirements"][0]["acceptance_criteria"] = []
    assert submit(payload).outcome == "passed"
    for field in ("actors", "functional_requirements"):
        broken = copy.deepcopy(payload)
        broken[field] = []
        result = submit(broken)
        assert_error(result, "SCHEMA_VIOLATION", f"/{field}", {"keyword": "minItems", "schema_pointer": f"/properties/{field}/minItems"})


def test_free_json_is_not_text_validation_and_numbers_stay_exact(payload):
    with localcontext() as context:
        context.prec = 2
        numbers = [Decimal("9" * 5001), Decimal("1e400"), Decimal("0.123456789012345678901234567890123456789"), True, None]
        payload["constraints"][0]["constraint"]["value"] = {"unknown-key": ["", EXPECTED_W, numbers]}
        result = validate_input(serialize_json(payload))
        assert result.outcome == "passed"
        found = result.normalized_input["constraints"][0]["constraint"]["value"]["unknown-key"][2]
        assert [type(v) for v in found] == [Decimal, Decimal, Decimal, bool, type(None)]
        assert [v.as_tuple() for v in found[:3]] == [v.as_tuple() for v in numbers[:3]]


@pytest.mark.parametrize("value,number,integer", [(True, False, False), (False, False, False),
    (1, True, True), (1.0, False, False), (Decimal('1.00'), True, True), (Decimal('1.01'), True, False),
    (Decimal('1e400'), True, True), (Decimal('0E-400'), True, True), (Decimal('NaN'), False, False),
    (Decimal('Infinity'), False, False)])
def test_explicit_type_checker(value, number, integer):
    assert ProfileValidator.TYPE_CHECKER.is_type(value, "number") is number
    assert ProfileValidator.TYPE_CHECKER.is_type(value, "integer") is integer


OPTIONAL_PATHS = [(group, 0, key) for group in GROUPS for key in ("title", "group", "details")]
OPTIONAL_PATHS += [("constraints", 0, "constraint"), ("project_details",)]


@pytest.mark.parametrize("path", OPTIONAL_PATHS)
@pytest.mark.parametrize("present", [True, False])
def test_nullable_optional_and_absence_remain_distinct(payload, submit, path, present):
    node = payload
    for key in path[:-1]:
        node = node[key]
    if present:
        node[path[-1]] = None
    else:
        node.pop(path[-1])
    result = submit(payload)
    assert result.outcome == "passed"
    actual = result.normalized_input
    for key in path[:-1]:
        actual = actual[key]
    assert (path[-1] in actual) is present
    if present:
        assert actual[path[-1]] is None


@pytest.mark.parametrize("ids", [("R", "r", "R 1"), ("é", "é", "E"), ("\ufeffR", "R\u200b", "R")])
def test_id_exact_without_casefold_normalization_or_boundary_veto(payload, submit, ids):
    for group, identifier in zip(GROUPS, ids):
        payload[group][0]["id"] = identifier
    result = submit(payload)
    assert result.outcome == "passed"
    assert tuple(result.normalized_input[group][0]["id"] for group in GROUPS) == ids


@pytest.mark.parametrize("metrics,expected", [([], "METRIC_COUNT"),
    (["response_time_p95"] * 5, "METRIC_COUNT"),
    (["response_time_p95", "sustainable_throughput", "cpu_utilisation", "unknown"], "INVALID_METRIC"),
    (None, "TYPE_MISMATCH"), ("response_time_p95", "TYPE_MISMATCH")])
def test_remaining_metric_boundaries(payload, submit, metrics, expected):
    payload["design_preferences"]["metric_priorities"] = metrics
    result = submit(payload)
    assert result.outcome == "rejected"
    assert expected in {item["code"] for item in result.errors}
    assert result.checks["cross_field"] == "not_run"


def test_empty_root_lists_every_missing_key_once(submit):
    result = submit({})
    expected = ["actors", "constraints", "context", "design_preferences", "functional_requirements",
                "non_functional_requirements", "operating_conditions", "title"]
    assert [item["pointer"] for item in result.errors] == ["/" + name for name in expected]
    assert all(item["code"] == "MISSING_FIELD" for item in result.errors)
    assert len(result.normalizations) == 1
