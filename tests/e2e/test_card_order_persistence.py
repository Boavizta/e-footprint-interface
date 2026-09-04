import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def two_server_model_builder(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    first_server = Server.from_defaults("First server", storage=Storage.from_defaults("First storage"))
    second_server = Server.from_defaults("Second server", storage=Storage.from_defaults("Second storage"))
    first_job = Job.from_defaults("First job", server=first_server)
    second_job = Job.from_defaults("Second job", server=second_server)
    step = UsageJourneyStep.from_defaults("Test step", jobs=[first_job, second_job])
    journey = UsageJourney("Test journey", uj_steps=[step])
    usage_pattern = UsagePattern(
        "Test usage pattern",
        usage_journeys={journey: SourceValue(1 * u.dimensionless)},
        devices=[Device.from_defaults("Test device")],
        network=Network.from_defaults("Test network"),
        country=country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz("Europe/Paris"))(),
        hourly_occurrences=create_hourly_usage(),
    )
    system = System("Card order model", usage_patterns=[usage_pattern], edge_usage_patterns=[])
    return load_system_dict_into_browser(model_builder_page, system_to_json(system, save_computed_state=False))


@pytest.mark.e2e
def test_card_order_survives_workspace_switch_reload_and_download_upload(
    two_server_model_builder: ModelBuilderPage,
    tmp_path,
):
    model_builder = two_server_model_builder
    original_order = ["First server", "Second server"]
    reordered = ["Second server", "First server"]

    assert model_builder.card_names_in_list("server-list") == original_order
    model_builder.add_model_by_duplication()
    model_builder.drag_card_to_start("server-list", "Second server")
    assert model_builder.card_names_in_list("server-list") == reordered

    model_builder.switch_to_model(0)
    assert model_builder.card_names_in_list("server-list") == original_order
    model_builder.switch_to_model(1)
    assert model_builder.card_names_in_list("server-list") == reordered

    model_builder.page.reload()
    model_builder.canvas.wait_for(state="visible")
    assert model_builder.active_slot() == "1"
    assert model_builder.card_names_in_list("server-list") == reordered
    model_builder.switch_to_model(0)
    assert model_builder.card_names_in_list("server-list") == original_order
    model_builder.switch_to_model(1)

    download_path = tmp_path / "card-order.e-f.json"
    model_builder.download_active_model(str(download_path))
    model_builder.reset_to_default()
    model_builder.import_json_file(str(download_path))

    assert model_builder.card_names_in_list("server-list") == reordered
