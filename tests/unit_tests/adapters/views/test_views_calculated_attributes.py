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


def _assert_success_or_exception_modal(response, url):
    if response.status_code != 200:
        assert response.status_code == 500, url
        assert response.headers.get("HX-Reswap") == "none", url
        assert "openModalDialog" in response.headers.get("HX-Trigger-After-Settle", ""), url


@pytest.mark.xfail(strict=True, reason="bug-fixes-2026-10 Task 9")
@pytest.mark.django_db
def test_empty_calculated_dict_entries_render_no_chart_and_fragment_views_never_fail_silently(
        client, monkeypatch, edge_computer_system_data, minimal_system_data):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    client.raise_request_exception = False
    SessionSystemRepository(client.session).save_data(edge_computer_system_data)
    edge_computer_id = next(iter(edge_computer_system_data["EdgeComputer"]))
    storage_id = next(iter(edge_computer_system_data["EdgeStorage"]))
    cpu_id = next(iter(edge_computer_system_data["EdgeComputerCPUComponent"]))
    ram_id = next(iter(edge_computer_system_data["EdgeComputerRAMComponent"]))
    process_id = next(iter(edge_computer_system_data["RecurrentEdgeProcess"]))
    usage_pattern_id = next(iter(edge_computer_system_data["EdgeUsagePattern"]))

    panel = client.get(f"/model_builder/open-edit-object-panel/{edge_computer_id}/").content.decode()
    chart_urls = re.findall(rf'hx-get="({re.escape(HOURLY_CHART_URL)}[^"]+)"', panel)

    for attr_name in EMPTY_STORAGE_DICT_ATTRIBUTES:
        assert f"{HOURLY_CHART_URL}{storage_id}/{attr_name}/{usage_pattern_id}" not in chart_urls
        assert (f"/model_builder/get_calculated_attribute_explanation/{storage_id}/{attr_name}/{usage_pattern_id}"
                in panel)
    assert any(url.startswith(f"{HOURLY_CHART_URL}{cpu_id}/") for url in chart_urls)
    assert any(url.startswith(f"{HOURLY_CHART_URL}{ram_id}/") for url in chart_urls)
    for url in chart_urls:
        assert client.get(url).status_code == 200, url
    empty_entry_chart_url = f"{HOURLY_CHART_URL}{storage_id}/unitary_power_per_usage_pattern/{usage_pattern_id}"
    _assert_success_or_exception_modal(client.get(empty_entry_chart_url), empty_entry_chart_url)

    # Another tab loads a different model into the session: every URL the open panels hold is now stale.
    SessionSystemRepository(client.session).save_data(minimal_system_data)
    for url in [f"{HOURLY_CHART_URL}{cpu_id}/energy_per_edge_device/",
                f"/model_builder/get_explainable_recurrent_quantity_chart_and_explanation/{process_id}/"
                f"recurrent_compute_needed/",
                f"/model_builder/get_calculated_attribute_explanation/{storage_id}/energy_per_edge_device/",
                f"/model_builder/ask-delete-object/{edge_computer_id}/"]:
        _assert_success_or_exception_modal(client.get(url), url)


@pytest.mark.xfail(strict=True, reason="bug-fixes-2026-10 Task 10")
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
    cpu_id = next(iter(system_data["EdgeComputerCPUComponent"]))
    ram_id = next(iter(system_data["EdgeComputerRAMComponent"]))

    panel = client.get(f"/model_builder/open-edit-object-panel/{edge_computer_id}/").content.decode()

    id_counts = Counter(re.findall(r'(?<![\w-])id="([^"]+)"', panel))
    assert {element_id: count for element_id, count in id_counts.items() if count > 1} == {}
    buttons = list(re.finditer(
        r'<button[^>]*hx-get="(/model_builder/get_(?:eco_logits_)?calculated_attribute_explanation/[^"]+)"[^>]*>',
        panel))
    targets = {}
    for button, next_button in zip(buttons, buttons[1:] + [None]):
        attributes = dict(re.findall(r'([\w-]+)="([^"]*)"', button.group(0)))
        target_id = attributes["aria-controls"]
        assert attributes["hx-target"] == attributes["data-bs-target"] == f"#{target_id}", button.group(1)
        own_row = panel[button.end():next_button.start() if next_button else len(panel)]
        assert f'id="{target_id}"' in own_row, button.group(1)
        targets[button.group(1)] = target_id
    explanation_url = "/model_builder/get_calculated_attribute_explanation/{}/carbon_footprint_manufacturing/"
    assert targets[explanation_url.format(cpu_id)] != targets[explanation_url.format(ram_id)]
