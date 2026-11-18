import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from efootprint.constants.units import u

from model_builder.application.ai_bootstrap.dsl import EdgeDeviceSpec, WebEdgeSpec, build_edge_device, build_edge_groups
from model_builder.application.ai_bootstrap.service import Completion, build_answer, generate
from tests.declare import titled

EDGE_ANSWER = (Path(__file__).parents[3] / "ai_sandbox/cases/_handwritten_04_ev_charging.json").read_text()


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


NAMED_SECTIONS = {"servers": {}, "genai_apis": {}, "jobs": {}, "journeys": {"steps": []}, "edge_devices": {},
                  "edge_device_groups": {}, "edge_functions": {"device": "Same"}, "edge_journeys": {"functions": []},
                  "edge_deployments": {"journey": "Same", "new_units": {"value": 1, "per": "month"}}}


@pytest.mark.parametrize("section", list(NAMED_SECTIONS))
def test_duplicate_declarations_fail_before_construction(section):
    obj = {"name": "Same", **NAMED_SECTIONS[section]}
    with pytest.raises(ValueError, match="Duplicate declaration"):
        build_answer(json.dumps({"system_name": "X", section: [obj, obj]}), "web_edge" if "edge" in section else "web")


def test_bad_reference_is_rejected():
    with pytest.raises(ValueError, match="Unknown job"):
        build_answer(json.dumps({"system_name": "X", "journeys": [{"name": "J", "steps": [
            {"name": "Step", "jobs": ["Missing"]}]}]}), "web")


def test_generate_does_not_retry_invalid_answer():
    complete = Mock(return_value=Completion("invalid"))
    with pytest.raises(ValueError):
        generate("Description", "web", complete)
    complete.assert_called_once()


# The answers of the narrative cases state all three values; the derivation, kept for an answer that omits one, is the
# sandbox's for the power and the RAM, and a quarter of the stated storage for the storage.
@titled("ai-bootstrap-edge#edge-device-sizing: an omitted idle power, reserved RAM or reserved storage is "
        "derived from the device's stated power, RAM or storage")
def test_omitted_device_reserves_are_derived():
    gateway = build_edge_device(EdgeDeviceSpec(name="Gateway", power_w=6, ram_gb=2, storage_gb=32), [])
    sensor = build_edge_device(EdgeDeviceSpec(name="Sensor", kind="appliance", power_w=0.05), [])
    stated = build_edge_device(EdgeDeviceSpec(name="Stated", power_w=6, idle_power_w=3, ram_gb=2, base_ram_gb=1,
                                              storage_gb=32, base_storage_gb=10), [])
    unstated = build_edge_device(EdgeDeviceSpec(name="Unstated"), [])

    assert gateway.idle_power.value == 5 * u.W  # the library default, below the stated power
    assert gateway.idle_power.comment == "The library default, within the device's power"
    assert gateway.base_ram_consumption.value == 0.5 * u.GB_ram
    assert gateway.base_ram_consumption.comment == "A quarter of the device's RAM, the library default being more"
    assert gateway.storage.base_storage_need.value == 8 * u.GB_stored
    assert gateway.storage.base_storage_need.comment == (
        "A quarter of the device's storage, the library default being more")
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


@titled("ai-bootstrap-edge#deployments-over-time: a deployment's usage span is its stated one, else its devices' "
        "shortest lifespan, six years at most")
def test_usage_span_defaults_to_the_shortest_lifespan():
    monthly = {"value": 1, "per": "month"}
    answer = {"system_name": "X",
              "edge_devices": [{"name": "Gateway", "lifespan_years": 5}, {"name": "Sensor", "kind": "appliance", "lifespan_years": 7},
                               {"name": "Kiosk", "lifespan_years": 10}],
              "edge_functions": [{"name": "Upload", "device": "Gateway"}, {"name": "Sense", "device": "Sensor"},
                                 {"name": "Show", "device": "Kiosk"}],
              "edge_journeys": [{"name": "Building", "functions": ["Upload", "Sense"]}, {"name": "Mall", "functions": ["Show"]}],
              "edge_deployments": [{"name": "Buildings", "journey": "Building", "new_units": monthly},
                                   {"name": "Malls", "journey": "Mall", "new_units": monthly},
                                   {"name": "Stated", "journey": "Mall", "new_units": monthly, "usage_span_years": 8}]}

    system = build_answer(json.dumps(answer), "web_edge").system

    assert {p.name: p.usage_span.value.to(u.year).magnitude for p in system.edge_usage_patterns} == {
        "Buildings": 5, "Malls": 6, "Stated": 8}


def period(series) -> tuple:
    inputs = series.form_inputs
    return inputs["start_date"], inputs["modeling_duration_value"], inputs["modeling_duration_unit"]


@titled("ai-bootstrap-edge#deployments-over-time: a deployment's stated end date closes its own period; the others "
        "run to the end of 2027")
def test_a_stated_end_date_closes_its_deployment():
    system = build_answer(EDGE_ANSWER, "web_edge").system

    periods = {p.name: period(p.hourly_deployment_starts) for p in system.edge_usage_patterns}

    assert periods == {"Stations in Germany": ("2024-01-01", 4, "year"),
                       "Stations in the Netherlands": ("2024-01-01", 3, "year")}
    dutch = next(p for p in system.edge_usage_patterns if p.name == "Stations in the Netherlands")
    assert "the Dutch rollout has stopped" in dutch.hourly_deployment_starts.comment


def edge_answer(**deployment) -> str:
    """A dashboard on one server, a kiosk kept 20 years, and one deployment of kiosks with the fields given."""
    return json.dumps({
        "system_name": "X", "servers": [{"name": "S"}], "jobs": [{"name": "J", "server": "S"}],
        "journeys": [{"name": "Dashboard", "steps": [{"name": "Open", "jobs": ["J"]}]}],
        "usage_patterns": [{"name": "Team", "journey": "Dashboard", "volume": {"value": 10, "per": "day"}}],
        "edge_devices": [{"name": "Kiosk", "lifespan_years": 20}],
        "edge_functions": [{"name": "Show", "device": "Kiosk"}],
        "edge_journeys": [{"name": "Mall", "functions": ["Show"]}],
        "edge_deployments": [{"name": "Malls", "journey": "Mall", "new_units": {"value": 1, "per": "month"}, **deployment}]})


@titled("ai-bootstrap-edge#deployments-over-time: a web usage beyond the editor's limit is cut and listed; a deployment "
        "beyond it, or misdated, is refused")
def test_periods_beyond_the_editor_limit_are_cut_or_refused():
    # Kiosks deployed 2010 to 2012 and kept 20 years: the web usage would run 23 years, to the last retirement in 2032.
    cut = build_answer(edge_answer(start_date="2010-01-01", end_date="2012-12-31", usage_span_years=20), "web_edge")

    [team] = cut.system.usage_patterns
    assert period(team.hourly_occurrences) == ("2010-01-01", 20, "year")
    [listed] = [r for r in cut.resolutions if r.how == "cut at the editor's limit"]
    assert (listed.requested, listed.resolved) == ("Team: 23 years from 2010-01-01", "20 years")
    with pytest.raises(ValueError, match="more than the editor accepts"):
        build_answer(edge_answer(start_date="2000-01-01"), "web_edge")
    with pytest.raises(ValueError, match="falls after the end"):
        build_answer(edge_answer(start_date="2027-06-01", end_date="2027-01-01"), "web_edge")
