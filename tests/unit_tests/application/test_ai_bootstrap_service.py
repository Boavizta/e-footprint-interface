import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from efootprint.constants.units import u

from model_builder.application.ai_bootstrap.dsl import (
    EdgeDeviceSpec, ModelSpec, WebEdgeSpec, build_edge_device, build_edge_groups)
from model_builder.application.ai_bootstrap.service import Completion, build_answer, generate
from comprehension_harness.python.declare import titled

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


@titled("ai-bootstrap-edge#edge-format: a comment written as a number is read as its text; a boolean, list or "
        "object still fails")
def test_a_comment_written_as_a_number_is_read_as_text():
    def answer(comment):
        return json.dumps({"system_name": "X", "servers": [{"name": "S"}],
                           "jobs": [{"name": "J", "server": "S", "data_stored_kb": 2500,
                                     "comments": {"data_stored_kb": comment}}]})

    for schema in (ModelSpec, WebEdgeSpec):
        assert schema.model_validate(json.loads(answer(2500))).jobs[0].comments == {"data_stored_kb": "2500"}
    for refused in (True, [1], {"a": 1}):
        with pytest.raises(ValidationError, match="valid string"):
            build_answer(answer(refused), "web_edge")


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


@titled("ai-bootstrap-edge#device-groups: a sub-group declared neither as a group nor as a device, or a cycle of "
        "sub-groups, refuses the answer")
@pytest.mark.parametrize("groups", [
    [{"name": "Building", "sub_group_counts": {"Wing": 2}}],
    [{"name": "Building", "sub_group_counts": {"Floor": 4}}, {"name": "Floor", "sub_group_counts": {"Building": 1}}],
])
def test_unknown_or_cyclic_sub_groups_refuse_the_answer(groups):
    spec = edge_groups_spec(*groups)
    with pytest.raises(ValueError, match="Unknown or cyclic edge device groups"):
        build_edge_groups(spec, {d.name: build_edge_device(d, []) for d in spec.edge_devices}, [])


@titled("ai-bootstrap-edge#device-groups: a declared device written as a sub-group counts as that device, "
        "unless the group also lists it")
def test_device_written_as_sub_group_counts_as_that_device():
    spec = edge_groups_spec({"name": "Floor", "device_counts": {"Gateway": 1}, "sub_group_counts": {"Sensor": 5}})
    devices = {d.name: build_edge_device(d, []) for d in spec.edge_devices}
    resolutions = []

    groups = build_edge_groups(spec, devices, resolutions)

    assert groups["Floor"].edge_device_counts[devices["Sensor"]].value == 5 * u.dimensionless
    assert [(r.requested, r.resolved, r.how) for r in resolutions] == [("Floor sub-group Sensor", "device Sensor", "moved")]
    ambiguous = edge_groups_spec({"name": "Floor", "device_counts": {"Sensor": 1}, "sub_group_counts": {"Sensor": 5}})
    with pytest.raises(ValueError, match="both a device and a sub-group"):
        build_edge_groups(ambiguous, devices, [])
    declared = edge_groups_spec({"name": "Floor", "sub_group_counts": {"Sensor": 5}},
                                {"name": "Sensor", "device_counts": {"Gateway": 1}})  # a group named like a device
    kept = []
    assert [g.name for g in build_edge_groups(declared, devices, kept)["Floor"].sub_group_counts] == ["Sensor"]
    assert kept == []


@titled("ai-bootstrap-edge#device-groups: a device no deployment runs, without a function or outside every journey, "
        "is listed as left out")
@pytest.mark.parametrize("spare_function", [[], [{"name": "Idle", "device": "Spare"}]])
def test_a_device_no_deployment_runs_is_listed_as_left_out(spare_function):
    answer = json.loads(edge_answer())
    answer["edge_devices"].append({"name": "Spare", "lifespan_years": 20})
    answer["edge_functions"] += spare_function

    resolutions = build_answer(json.dumps(answer), "web_edge").resolutions

    assert [(r.kind, r.requested, r.resolved, r.how) for r in resolutions if r.kind == "edge device"] == [
        ("edge device", "Spare", "left out of the footprint", "no deployment runs it")]


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


@titled("ai-bootstrap-edge#deployments-over-time: a stated usage span above its devices' shortest lifespan is cut to "
        "it and listed")
def test_a_usage_span_above_the_devices_lifespan_is_cut():
    answer = {"system_name": "X",
              "edge_devices": [{"name": "Gateway", "lifespan_years": 8}, {"name": "Sensor", "kind": "appliance"}],
              "edge_functions": [{"name": "Upload", "device": "Gateway"}, {"name": "Sense", "device": "Sensor"},
                                 {"name": "Relay", "device": "Gateway"}],
              "edge_journeys": [{"name": "Building", "functions": ["Upload", "Sense"]}, {"name": "Hub", "functions": ["Relay"]}],
              "edge_deployments": [{"name": "Buildings", "journey": "Building", "new_units": {"value": 1, "per": "month"},
                                    "usage_span_years": 10},
                                   {"name": "Hubs", "journey": "Hub", "new_units": {"value": 1, "per": "month"},
                                    "usage_span_years": 10}]}

    built = build_answer(json.dumps(answer), "web_edge")

    # Buildings: the sensor's class default lifespan, none being stated; hubs: the gateway's stated one.
    assert {p.name: p.usage_span.value.to(u.year).magnitude for p in built.system.edge_usage_patterns} == {
        "Buildings": 6, "Hubs": 8}
    assert [(r.requested, r.resolved, r.how) for r in built.resolutions if r.kind == "usage span"] == [
        ("Buildings: 10 years", "6 years", "cut to its devices' shortest lifespan"),
        ("Hubs: 10 years", "8 years", "cut to its devices' shortest lifespan")]


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


@titled("ai-bootstrap-edge#deployments-over-time: a growing web usage started in the past reaches its stated volume on "
        "2027-01-01; a flat one starts from it")
def test_a_past_growing_web_usage_is_discounted_to_its_start():
    def team(volume=None, **fields):
        answer = {"system_name": "X", "servers": [{"name": "S"}], "jobs": [{"name": "J", "server": "S"}],
                  "journeys": [{"name": "Dashboard", "steps": [{"name": "Open", "jobs": ["J"]}]}],
                  "usage_patterns": [{"name": "Team", "journey": "Dashboard",
                                      "volume": volume or {"value": 1000, "per": "month"},
                                      "start_date": "2023-01-01", **fields}]}
        built = build_answer(json.dumps(answer), "web")
        return built.system.usage_patterns[0].hourly_occurrences, built.resolutions

    days_to_2027 = (date(2027, 1, 1) - date(2023, 1, 1)).days

    def from_2027(series, days):
        return series.value.magnitude[days_to_2027 * 24:(days_to_2027 + days) * 24].sum()

    growing, _ = team(growth_pct_per_year=40)
    assert from_2027(growing, 30) == pytest.approx(1000, rel=0.005)  # within the rounding to a whole number
    assert growing.form_inputs["initial_volume"] == round(1000 / 1.4 ** (days_to_2027 / 365))
    assert growing.comment == "1,000 a month on 2027-01-01 as stated: 260 a month on 2023-01-01 at 40 % a year."
    weekly, _ = team({"value": 9000, "per": "week"}, growth_pct_per_year=40)
    assert from_2027(weekly, 7) == pytest.approx(9000, rel=0.005)
    assert weekly.comment == "9,000 a week on 2027-01-01 as stated: 333 a day on 2023-01-01 at 40 % a year."
    small, _ = team({"value": 1, "per": "month"}, growth_pct_per_year=40)
    assert from_2027(small, 365) == pytest.approx(12 * 1.4 ** 0.5, rel=0.2)  # per year, rather than 0 a month
    flat, _ = team()
    assert flat.form_inputs["initial_volume"] == 1000 and flat.comment is None
    shrinking, resolutions = team(growth_pct_per_year=-10)  # the editor accepts no negative growth: set flat
    assert shrinking.form_inputs["initial_volume"] == 1000 and shrinking.form_inputs["net_growth_rate_in_percentage"] == 0
    assert [(r.kind, r.requested, r.resolved, r.how) for r in resolutions if r.kind == "growth"] == [
        ("growth", "Team: -10 % a year", "0 % a year", "the editor accepts no negative growth")]


@titled("ai-bootstrap-edge#deployments-over-time: generated values open on the editors' steps: a whole volume per day, "
        "month or year within 0.5 %, a whole growth percent, a weekly need to the hundredth")
def test_generated_values_are_rounded_to_the_editors_steps():
    answer = json.loads(edge_answer(new_units={"value": 1, "per": "week"}))
    answer["usage_patterns"][0].update(volume={"value": 3000, "per": "week"}, growth_pct_per_year=2.6)
    answer["edge_functions"][0].update(cpu_cores_avg=0.333, server_calls=[{"jobs": ["J"], "times_per_hour": 0.0417}])

    system = build_answer(json.dumps(answer), "web_edge").system

    [team], [malls] = system.usage_patterns, system.edge_usage_patterns
    team_inputs, mall_inputs = team.hourly_occurrences.form_inputs, malls.hourly_deployment_starts.form_inputs
    assert (team_inputs["initial_volume"], team_inputs["initial_volume_timespan"],
            team_inputs["net_growth_rate_in_percentage"]) == (428, "day", 3)  # a growing week's first day
    assert (mall_inputs["initial_volume"], mall_inputs["initial_volume_timespan"]) == (52, "year")  # not 0.14 a day
    [function] = system.edge_usage_journeys[0].edge_functions
    [process] = function.recurrent_edge_device_needs
    [call] = function.recurrent_server_needs
    assert process.recurrent_compute_needed.form_inputs["constant_value"] == 0.33
    assert call.recurrent_volume_per_edge_device.form_inputs["constant_value"] == 0.04


@titled("ai-bootstrap-edge#deployments-over-time: beyond the editor's limit, web usage starts later or ends sooner, a "
        "deployment keeps the years nearest 2027; misdated refused")
def test_periods_beyond_the_editor_limit_are_cut_or_refused():
    how = "Growth projection holds 10 years at most"

    def build(usage_start=None, **deployment):
        answer = json.loads(edge_answer(**deployment))
        if usage_start:
            answer["usage_patterns"][0]["start_date"] = usage_start
        built = build_answer(json.dumps(answer), "web_edge")
        [team], [malls] = built.system.usage_patterns, built.system.edge_usage_patterns
        listed = {(r.requested, r.resolved, r.how) for r in built.resolutions if r.kind == "usage period"}
        return period(team.hourly_occurrences), period(malls.hourly_deployment_starts), listed

    # Kiosks deployed 2019 to 2020 and kept 10 years: the web usage would run 12 years, to the last retirement in 2030.
    assert build(start_date="2019-01-01", end_date="2020-12-31", usage_span_years=10) == (
        ("2019-01-01", 10, "year"), ("2019-01-01", 2, "year"),
        {("Team: 2019-01-01 to 2030-12-28", "2019-01-01 to 2028-12-28", how)})

    # Kiosks deployed since 2000: the deployment keeps 2027's ten years, and the web usage starts with it.
    assert build(start_date="2000-01-01") == (
        ("2018-01-03", 10, "year"), ("2018-01-03", 10, "year"),
        {("Malls: 2000-01-01 to 2027-12-31", "2018-01-03 to 2027-12-31",
          f"{how}: installations before 2018-01-03 are not counted"),
         ("Team: 2018-01-03 to 2033-12-29", "2018-01-03 to 2027-12-31", how)})

    # Ending after 2027, a deployment keeps the ten years that cover it: its first ten, or the ten ending with 2027.
    assert build(start_date="2020-01-01", end_date="2040-12-31") == (
        ("2020-01-01", 10, "year"), ("2020-01-01", 10, "year"),
        {("Malls: 2020-01-01 to 2040-12-31", "2020-01-01 to 2029-12-28",
          f"{how}: installations after 2029-12-28 are not counted"),
         ("Team: 2020-01-01 to 2035-12-27", "2020-01-01 to 2029-12-28", how)})
    assert build(start_date="2000-01-01", end_date="2040-12-31")[1:] == (
        ("2018-01-03", 10, "year"),
        {("Malls: 2000-01-01 to 2040-12-31", "2018-01-03 to 2027-12-31",
          f"{how}: installations before 2018-01-03 and after 2027-12-31 are not counted"),
         ("Team: 2018-01-03 to 2033-12-29", "2018-01-03 to 2027-12-31", how)})

    # A web usage dated 2012 starts ten years before the end of 2027; the undated deployment follows it unlisted.
    assert build(usage_start="2012-01-01") == (
        ("2018-01-03", 10, "year"), ("2018-01-03", 10, "year"),
        {("Team: from 2012-01-01", "from 2018-01-03", f"{how}: the 10 ending with 2027 are kept"),
         ("Team: 2018-01-03 to 2033-12-29", "2018-01-03 to 2027-12-31", how)})

    # Within ten years but above 120 months: a deployment is 120 months to its end, a web usage ten years from its
    # start, both unlisted.
    assert build(start_date="2018-01-20")[1:] == (
        ("2018-02-22", 120, "month"), {("Team: 2018-02-22 to 2033-12-29", "2018-02-22 to 2028-02-19", how)})
    assert build(usage_start="2018-02-01", start_date="2025-01-01", end_date="2025-12-31", usage_span_years=1) == (
        ("2018-02-01", 10, "year"), ("2025-01-01", 1, "year"), set())
    with pytest.raises(ValueError, match="falls after the end"):
        build_answer(edge_answer(start_date="2027-06-01", end_date="2027-01-01"), "web_edge")
