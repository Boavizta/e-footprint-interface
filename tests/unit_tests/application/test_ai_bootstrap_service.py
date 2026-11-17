import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from efootprint.constants.units import u

from model_builder.application.ai_bootstrap.dsl import EdgeDeviceSpec, WebEdgeSpec, build_edge_device, build_edge_groups
from model_builder.application.ai_bootstrap.service import Completion, build_answer, generate
from tests.declare import planned_test, titled


def test_generate_calls_once_and_reports_ignored_wrapped_fields():
    complete = Mock(return_value=Completion('Here is JSON:\n```json\n{"system_name":"Example","extra":3}\n```'))
    generated, completion = generate("A service", "web", complete)
    complete.assert_called_once()
    assert complete.call_args.args[1] == "A service"
    assert "each named journey independently" in complete.call_args.args[0]
    assert "edge_devices" not in complete.call_args.args[0]
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
@titled("ai-bootstrap-edge#edge-device-sizing: an omitted idle power, reserved RAM or reserved storage is "
        "derived from the device's stated power and RAM")
def test_omitted_device_reserves_are_derived():
    gateway = build_edge_device(EdgeDeviceSpec(name="Gateway", power_w=6, ram_gb=2, storage_gb=32), [])
    sensor = build_edge_device(EdgeDeviceSpec(name="Sensor", kind="appliance", power_w=0.05), [])
    stated = build_edge_device(EdgeDeviceSpec(name="Stated", power_w=6, idle_power_w=3, ram_gb=2, base_ram_gb=1,
                                              storage_gb=32, base_storage_gb=10), [])
    unstated = build_edge_device(EdgeDeviceSpec(name="Unstated"), [])

    assert gateway.idle_power.value == 5 * u.W  # the library default, below the stated power
    assert gateway.base_ram_consumption.value == 0.5 * u.GB_ram
    assert gateway.storage.base_storage_need.value == 8 * u.GB_stored
    assert sensor.idle_power.value == 0.05 * u.W
    assert (stated.idle_power.value, stated.base_ram_consumption.value, stated.storage.base_storage_need.value) == (
        3 * u.W, 1 * u.GB_ram, 10 * u.GB_stored)
    assert (unstated.idle_power.value, unstated.base_ram_consumption.value) == (5 * u.W, 1 * u.GB_ram)
    assert unstated.storage.base_storage_need.value == 30 * u.GB_stored


def edge_groups_spec(*groups):
    return WebEdgeSpec(system_name="X", edge_devices=[{"name": "Gateway"}, {"name": "Sensor", "kind": "appliance"}],
                       edge_device_groups=list(groups))


@titled("ai-bootstrap-edge#device-groups: a group of sub-groups is built after them, and a device counts once per "
        "unit of every group around it")
def test_nested_groups_multiply_device_counts():
    spec = edge_groups_spec({"name": "Building", "device_counts": {"Gateway": 1}, "sub_group_counts": {"Floor": 4}},
                            {"name": "Floor", "device_counts": {"Sensor": 10}, "comments": {"Sensor": "Ten a floor"}})
    devices = {d.name: build_edge_device(d, []) for d in spec.edge_devices}

    groups = build_edge_groups(spec, devices, [])

    assert groups["Building"].sub_group_counts[groups["Floor"]].value == 4 * u.dimensionless
    assert groups["Floor"].edge_device_counts[devices["Sensor"]].comment == "Ten a floor"
    assert devices["Sensor"].total_nb_of_units.value == 40 * u.dimensionless
    assert devices["Gateway"].total_nb_of_units.value == 1 * u.dimensionless


@titled("ai-bootstrap-edge#device-groups: a sub-group no group declares, or a cycle of sub-groups, refuses the answer")
@pytest.mark.parametrize("groups", [
    [{"name": "Building", "sub_group_counts": {"Wing": 2}}],
    [{"name": "Building", "sub_group_counts": {"Floor": 4}}, {"name": "Floor", "sub_group_counts": {"Building": 1}}],
])
def test_unknown_or_cyclic_sub_groups_refuse_the_answer(groups):
    spec = edge_groups_spec(*groups)
    with pytest.raises(ValueError, match="Unknown or cyclic edge device groups"):
        build_edge_groups(spec, {d.name: build_edge_device(d, []) for d in spec.edge_devices}, [])


@planned_test("ai-bootstrap-edge#deployments-over-time: a deployment's usage span is its stated one, else its devices' "
              "shortest lifespan, six years at most")
def test_usage_span_defaults_to_the_shortest_lifespan():
    pass
