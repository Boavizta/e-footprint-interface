import re
from collections import Counter

import pytest
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern

from comprehension_harness.python.declare import reproduces, titled
from model_builder.adapters.repositories import SessionSystemRepository
from tests.fixtures.system_builders import create_hourly_usage

HOURLY_CHART_URL = "/model_builder/get_explainable_hourly_quantity_chart_and_explanation/"
EMPTY_STORAGE_DICT_ATTRIBUTES = [
    "unitary_power_per_usage_pattern", "energy_per_edge_device_per_usage_pattern",
    "use_footprint_per_edge_device_per_usage_pattern"]


@pytest.fixture
def edge_computer_system_data():
    """An edge computer with its CPU, RAM and storage components, used by one edge usage pattern."""
    edge_computer = EdgeComputer.from_defaults("Edge computer", storage=EdgeStorage.from_defaults("Edge storage"))
    edge_function = EdgeFunction("Edge function", recurrent_edge_device_needs=[
        RecurrentEdgeProcess.from_defaults("Edge process", edge_device=edge_computer)], recurrent_server_needs=[])
    edge_usage_pattern = EdgeUsagePattern(
        "Edge usage pattern",
        edge_usage_journeys=[EdgeUsageJourney.from_defaults("Edge usage journey", edge_functions=[edge_function])],
        network=Network.wifi_network(), country=Countries.FRANCE(), hourly_deployment_starts=create_hourly_usage())
    return system_to_json(
        System("Edge system", usage_patterns=[], edge_usage_patterns=[edge_usage_pattern]), save_computed_state=False)


def _answer(response) -> str:
    """What a fragment request came to, as the user meets it."""
    if response.status_code == 200:
        return "the fragment"
    shown = response.headers.get("HX-Reswap") == "none" and "openModalDialog" in response.headers.get(
        "HX-Trigger-After-Settle", "")
    if not shown:
        return f"a raw {response.status_code}"
    return "the exception modal" if response.status_code == 500 else f"the exception modal, as a {response.status_code}"


@titled("bug-fixes-2026-10#dict-entry-own-template: a dict entry the library leaves empty reads no value, with "
         "its formula and no chart")
@pytest.mark.django_db
def test_empty_calculated_dict_entries_render_no_value_and_no_chart(client, monkeypatch, edge_computer_system_data):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    client.raise_request_exception = False
    SessionSystemRepository(client.session).save_data(edge_computer_system_data)
    edge_computer_id = next(iter(edge_computer_system_data["EdgeComputer"]))
    storage_id = next(iter(edge_computer_system_data["EdgeStorage"]))
    cpu_id = next(iter(edge_computer_system_data["EdgeComputerCPUComponent"]))
    ram_id = next(iter(edge_computer_system_data["EdgeComputerRAMComponent"]))
    usage_pattern_id = next(iter(edge_computer_system_data["EdgeUsagePattern"]))

    panel = client.get(f"/model_builder/open-edit-object-panel/{edge_computer_id}/").content.decode()
    chart_urls = re.findall(rf'hx-get="({re.escape(HOURLY_CHART_URL)}[^"]+)"', panel)
    entry = f"{storage_id}/{{}}/{usage_pattern_id}"
    seen = {
        "empty entries offering a chart": [
            name for name in EMPTY_STORAGE_DICT_ATTRIBUTES if HOURLY_CHART_URL + entry.format(name) in chart_urls],
        "empty entries offering their formula": [
            name for name in EMPTY_STORAGE_DICT_ATTRIBUTES
            if "/model_builder/get_calculated_attribute_explanation/" + entry.format(name) in panel],
        "components still charted": [name for name, component_id in (("cpu", cpu_id), ("ram", ram_id))
                                     if any(url.startswith(f"{HOURLY_CHART_URL}{component_id}/") for url in chart_urls)],
        "charts offered that do not draw": sum(_answer(client.get(url)) != "the fragment" for url in chart_urls),
    }

    assert seen == {
        "empty entries offering a chart": [], "empty entries offering their formula": EMPTY_STORAGE_DICT_ATTRIBUTES,
        "components still charted": ["cpu", "ram"], "charts offered that do not draw": 0}


@reproduces("bug-fixes-2026-10#fragment-views-show-modal: a fragment view that fails answers with the exception "
            "modal, a not-found at its own 404")
@pytest.mark.django_db
def test_failing_fragment_views_show_the_exception_modal(
        client, monkeypatch, edge_computer_system_data, minimal_system_data):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    client.raise_request_exception = False
    SessionSystemRepository(client.session).save_data(edge_computer_system_data)
    edge_computer_id = next(iter(edge_computer_system_data["EdgeComputer"]))
    storage_id = next(iter(edge_computer_system_data["EdgeStorage"]))
    cpu_id = next(iter(edge_computer_system_data["EdgeComputerCPUComponent"]))
    process_id = next(iter(edge_computer_system_data["RecurrentEdgeProcess"]))
    usage_pattern_id = next(iter(edge_computer_system_data["EdgeUsagePattern"]))

    # The chart of an entry the library leaves empty: no panel links to it once fixed, and it still cannot be drawn.
    answers = {"the chart of an empty entry": _answer(client.get(
        f"{HOURLY_CHART_URL}{storage_id}/unitary_power_per_usage_pattern/{usage_pattern_id}"))}
    # Another tab loads a different model into the session: every URL the open panels hold is now stale.
    SessionSystemRepository(client.session).save_data(minimal_system_data)
    answers.update({name: _answer(client.get(url)) for name, url in {
        "a stale hourly chart": f"{HOURLY_CHART_URL}{cpu_id}/energy_per_edge_device/",
        "a stale recurrent chart": f"/model_builder/get_explainable_recurrent_quantity_chart_and_explanation/"
                                   f"{process_id}/recurrent_compute_needed/",
        "a stale explanation": f"/model_builder/get_calculated_attribute_explanation/{storage_id}/"
                               f"energy_per_edge_device/",
        "a stale delete confirmation": f"/model_builder/ask-delete-object/{edge_computer_id}/"}.items()})
    # What a view answers not-found to by itself: nothing the page shows, today.
    not_found = {name: _answer(client.get(url)) for name, url in {
        "a stale Sources row": f"/model_builder/source-table-row-editor/{edge_computer_id}/lifespan/",
        "the help of an unknown class": "/model_builder/open-help-drawer/NotARealClass/"}.items()}

    assert {**answers, **not_found} == {**dict.fromkeys(answers, "the exception modal"),
                                        **dict.fromkeys(not_found, "the exception modal, as a 404")}


@reproduces("bug-fixes-2026-10#explanation-ids-per-item: in a panel of several objects, each formula button opens "
            "a row of its own")
@pytest.mark.django_db
def test_edit_panel_explanation_buttons_target_their_own_row(client, edge_computer_system_data):
    # A second edge usage pattern gives the storage's per-pattern dicts several entries.
    class_obj_dict, _, _ = json_to_system(edge_computer_system_data)
    system = next(iter(class_obj_dict["System"].values()))
    usage_pattern = system.edge_usage_patterns[0]
    system.edge_usage_patterns = [usage_pattern, EdgeUsagePattern(
        "Second edge usage pattern", edge_usage_journeys=list(usage_pattern.edge_usage_journeys),
        network=Network.wifi_network(), country=Countries.FRANCE(), hourly_deployment_starts=create_hourly_usage())]
    system_data = system_to_json(system, save_computed_state=False)
    SessionSystemRepository(client.session).save_data(system_data)
    edge_computer_id = next(iter(system_data["EdgeComputer"]))
    owners = {edge_computer_id: "edge computer", **{next(iter(system_data[class_name])): owner for owner, class_name in (
        ("cpu", "EdgeComputerCPUComponent"), ("ram", "EdgeComputerRAMComponent"), ("storage", "EdgeStorage"))}}

    panel = client.get(f"/model_builder/open-edit-object-panel/{edge_computer_id}/").content.decode()

    buttons = list(re.finditer(
        r'<button[^>]*hx-get="/model_builder/get_(?:eco_logits_)?calculated_attribute_explanation/([^"]+)"[^>]*>',
        panel))
    opened_by, astray = {}, []
    for button, next_button in zip(buttons, buttons[1:] + [None]):
        owner_id, *attribute = button.group(1).strip("/").split("/")
        formula = f"{owners[owner_id]}: {' of '.join(attribute)}"
        attributes = dict(re.findall(r'([\w-]+)="([^"]*)"', button.group(0)))
        row_id = attributes["aria-controls"]
        own_row = panel[button.end():next_button.start() if next_button else len(panel)]
        if not (attributes["hx-target"] == attributes["data-bs-target"] == f"#{row_id}" and f'id="{row_id}"' in own_row):
            astray.append(formula)
        opened_by.setdefault(row_id, []).append(formula)
    id_counts = Counter(re.findall(r'(?<![\w-])id="([^"]+)"', panel))
    seen = {
        "objects whose formula buttons were read": sorted({formula.split(":")[0] for formula in sum(
            opened_by.values(), [])}),
        "ids the panel holds more than once": {
            element_id: count for element_id, count in id_counts.items() if count > 1},
        "rows that several formula buttons open": {
            row_id: formulas for row_id, formulas in opened_by.items() if len(formulas) > 1},
        "formula buttons whose references name no row under them": astray,
    }

    assert seen == {
        "objects whose formula buttons were read": sorted(owners.values()), "ids the panel holds more than once": {},
        "rows that several formula buttons open": {}, "formula buttons whose references name no row under them": []}
