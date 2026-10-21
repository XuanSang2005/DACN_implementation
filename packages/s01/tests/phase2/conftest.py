"""Small synthetic input, authored independently of the clinic dataset."""

import pytest


@pytest.fixture
def payload():
    def requirement(identifier, priority):
        return {"id": identifier, "text": "  Giữ nguyên nội dung  ", "priority": priority,
                "acceptance_criteria": ["Tiêu chí hai", "Tiêu chí một", "Tiêu chí một"],
                "title": None, "group": "Nhóm", "details": {
                    "trigger": None, "data": "Dữ liệu", "business_rules": "Quy tắc", "exceptions": None}}

    constraint = requirement("C", "must")
    constraint["constraint"] = {"kind": "local", "value": {"arbitrary/~": [None, True, 0, "", " \t"]}}
    return {
        "schema_version": "1.0.0", "title": "Thử nghiệm", "context": "Bối cảnh",
        "actors": ["Người dùng"], "functional_requirements": [requirement("R", None)],
        "non_functional_requirements": [requirement("N", "should")], "constraints": [constraint],
        "design_preferences": {"metric_priorities": ["response_time_p95", "sustainable_throughput", "cpu_utilisation", "scaling_gain"]},
        "operating_conditions": dict.fromkeys(("critical_scenarios", "expected_load", "peak_load", "data_volume", "growth", "resource_budget"), None),
        "project_details": {"scope_exclusions": None, "external_systems": "Ngoài", "data_context": None},
    }


@pytest.fixture
def submit():
    from dacn_s01.codec import serialize_json
    from dacn_s01.validation import validate_input
    return lambda value: validate_input(serialize_json(value))
