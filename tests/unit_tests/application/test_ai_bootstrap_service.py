import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from model_builder.application.ai_bootstrap.service import Completion, build_answer, generate
from tests.declare import planned_test


def test_generate_calls_once_and_reports_ignored_wrapped_fields():
    complete = Mock(return_value=Completion('Here is JSON:\n```json\n{"system_name":"Example","extra":3}\n```'))
    generated, completion = generate("A service", "web", complete)
    complete.assert_called_once()
    assert complete.call_args.args[1] == "A service"
    assert "each named journey independently" in complete.call_args.args[0]
    assert generated.ignored_fields == ["extra"]
    assert completion is complete.return_value


@pytest.mark.parametrize("answer", ["not json", '{}', '{"system_name":"X","jobs":[{"name":"x"}]}'])
def test_invalid_answers_fail_locally(answer):
    with pytest.raises((ValueError, ValidationError)):
        build_answer(answer, "web")


# @planned ai-bootstrap-edge#edge-builder The edge sections join the table, built under the Web + edge scope.
@pytest.mark.parametrize("section", ["servers", "genai_apis", "jobs", "journeys"])
def test_duplicate_declarations_fail_before_construction(section):
    obj = {"name": "Same"}
    if section == "journeys":
        obj["steps"] = []
    with pytest.raises(ValueError, match="Duplicate declaration"):
        build_answer(json.dumps({"system_name": "X", section: [obj, obj]}), "web")


def test_bad_reference_is_rejected():
    with pytest.raises(ValueError, match="Unknown job"):
        build_answer(json.dumps({"system_name": "X", "journeys": [{"name": "J", "steps": [
            {"name": "Step", "jobs": ["Missing"]}]}]}), "web")


def test_generate_does_not_retry_invalid_answer():
    complete = Mock(return_value=Completion("invalid"))
    with pytest.raises(ValueError):
        generate("Description", "web", complete)
    complete.assert_called_once()


# The answers of the narrative cases state all three values; the derivation is the sandbox's, kept for an answer that
# omits one.
@planned_test("ai-bootstrap-edge#edge-device-sizing: an omitted idle power, reserved RAM or reserved storage is "
              "derived from the device's stated power and RAM")
def test_omitted_device_reserves_are_derived():
    pass


@planned_test("ai-bootstrap-edge#device-groups: a group of sub-groups is built after them, and a device counts once per "
              "unit of every group around it")
def test_nested_groups_multiply_device_counts():
    pass


@planned_test("ai-bootstrap-edge#device-groups: a sub-group no group declares, or a cycle of sub-groups, refuses the answer")
def test_unknown_or_cyclic_sub_groups_refuse_the_answer():
    pass


@planned_test("ai-bootstrap-edge#deployments-over-time: a deployment's usage span is its stated one, else its devices' "
              "shortest lifespan, six years at most")
def test_usage_span_defaults_to_the_shortest_lifespan():
    pass
