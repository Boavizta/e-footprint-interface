"""Integration tests for object edition flows (use cases + domain), without Django.

Ported/refactored from `tests__old/model_builder/test_views_edition.py`.

Dropped/changed:
- Django request/session + HTTP response assertions: view concerns, not use-case concerns.
- WebApplication/WebApplicationJob: removed from the domain model.
- GenAIModel/GenAIJob: removed; replaced by EcoLogits external API classes.
"""

from __future__ import annotations

import json

from efootprint.builders.external_apis.ecologits.ecologits_external_api import EcoLogitsGenAIExternalAPI
from efootprint.constants.units import u

from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_COUNTRIES, DEFAULT_DEVICES, DEFAULT_NETWORKS
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object, edit_object


def _total_emissions(model_web: ModelWeb) -> float:
    emissions = model_web.system_emissions
    return sum(sum(values) for values in emissions["values"].values())


def _usage_pattern_post_data(name: str, uj_id: str, initial_volume: int) -> dict:
    return create_post_data_from_class_default_values(
        name,
        "UsagePattern",
        usage_journey=uj_id,
        devices=next(iter(DEFAULT_DEVICES.keys())),
        network=next(iter(DEFAULT_NETWORKS.keys())),
        country=next(iter(DEFAULT_COUNTRIES.keys())),
        hourly_usage_journey_starts__initial_volume=initial_volume,
    )


def _pick_ecologits_provider_and_model(index: int) -> tuple[str, str]:
    providers = [str(p) for p in EcoLogitsGenAIExternalAPI.list_values["provider"]]
    provider = providers[index % len(providers)]
    conditional = EcoLogitsGenAIExternalAPI.conditional_list_values["model_name"]["conditional_list_values"]
    model_name = str(conditional[[p for p in conditional.keys() if str(p) == provider][0]][0])
    return provider, model_name


def test_edit_server_updates_nested_storage(default_system_repository):
    server_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Server to edit",
            "Server",
            server_type="autoscaling",
            Storage_form_data=create_post_data_from_class_default_values("Initial Storage", "Storage"),
        ),
    )

    sd = default_system_repository.get_system_data()
    storage_id = sd["Server"][server_id]["storage"]

    storage_form_data = create_post_data_from_class_default_values(
        "Updated Storage",
        "Storage",
        carbon_footprint_fabrication_per_storage_capacity="160.0",
        carbon_footprint_fabrication_per_storage_capacity_unit=str(u.kg / u.TB),
    )

    edit_object(
        default_system_repository,
        server_id,
        "Server",
        {
            "name": "Updated server",
            "carbon_footprint_fabrication": "60",
            "carbon_footprint_fabrication_unit": str(u.kg),
            "Storage_form_data": json.dumps(storage_form_data),
        },
    )

    sd = default_system_repository.get_system_data()
    assert sd["Server"][server_id]["name"] == "Updated server"
    assert sd["Server"][server_id]["carbon_footprint_fabrication"]["value"] == 60.0
    assert sd["Storage"][storage_id]["name"] == "Updated Storage"
    assert sd["Storage"][storage_id]["carbon_footprint_fabrication_per_storage_capacity"]["value"] == 160.0


def test_edit_usage_journey_reorders_steps(default_system_repository):
    uj_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Journey", "UsageJourney", uj_steps=""),
    )
    step_1 = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Step 1", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )
    step_2 = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Step 2", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )
    step_3 = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Step 3", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )

    new_order = [step_2, step_3, step_1]
    edit_object(default_system_repository, uj_id, "UsageJourney", {"uj_steps": ";".join(new_order)})

    sd = default_system_repository.get_system_data()
    assert sd["UsageJourney"][uj_id]["uj_steps"] == new_order

    journey = ModelWeb(default_system_repository).get_web_object_from_efootprint_id(uj_id)
    assert [s.efootprint_id for s in journey.uj_steps] == new_order


def test_edit_usage_journey_remove_step_deletes_orphan(default_system_repository):
    uj_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Journey", "UsageJourney", uj_steps=""),
    )
    step_1 = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Step 1", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )
    step_2 = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Step 2", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )
    step_3 = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Step 3", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )

    edit_object(default_system_repository, uj_id, "UsageJourney", {"uj_steps": ";".join([step_1, step_3])})

    sd = default_system_repository.get_system_data()
    assert sd["UsageJourney"][uj_id]["uj_steps"] == [step_1, step_3]
    assert step_2 not in sd.get("UsageJourneyStep", {})


def test_edit_usage_pattern_initial_volume_increases_total_footprint(default_system_repository):
    model_web = ModelWeb(default_system_repository)
    uj_id = model_web.usage_journeys[0].efootprint_id

    up_id = create_object(default_system_repository, _usage_pattern_post_data("Temp UP", uj_id, initial_volume=1000))
    before = _total_emissions(ModelWeb(default_system_repository))

    edit_object(
        default_system_repository,
        up_id,
        "UsagePattern",
        {
            "hourly_usage_journey_starts__start_date": "2025-02-02",
            "hourly_usage_journey_starts__modeling_duration_value": "1",
            "hourly_usage_journey_starts__modeling_duration_unit": "year",
            "hourly_usage_journey_starts__net_growth_rate_in_percentage": "10",
            "hourly_usage_journey_starts__net_growth_rate_timespan": "month",
            "hourly_usage_journey_starts__initial_volume": "20000",
            "hourly_usage_journey_starts__initial_volume_timespan": "month",
        },
    )
    after = _total_emissions(ModelWeb(default_system_repository))

    assert after > before


def test_edit_ecologits_external_api_provider_and_model(default_system_repository):
    provider_1, model_1 = _pick_ecologits_provider_and_model(0)
    provider_2, model_2 = _pick_ecologits_provider_and_model(1)
    assert provider_1 != provider_2

    api_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test GenAI API",
            "EcoLogitsGenAIExternalAPI",
            provider=provider_1,
            model_name=model_1,
        ),
    )

    object_type = ModelWeb(default_system_repository).get_web_object_from_efootprint_id(api_id).class_as_simple_str
    edit_object(
        default_system_repository,
        api_id,
        object_type,
        {"provider": provider_2, "model_name": model_2},
    )

    sd = default_system_repository.get_system_data()
    api_class = next(class_name for class_name, objects in sd.items() if isinstance(objects, dict) and api_id in objects)
    assert sd[api_class][api_id]["provider"]["value"] == provider_2
    assert sd[api_class][api_id]["model_name"]["value"] == model_2


def test_delete_one_of_two_usage_patterns_then_edit_shared_server(default_system_repository):
    """Regression for a legacy scenario: deleting one usage pattern must not break editing shared objects."""
    model_web = ModelWeb(default_system_repository)
    uj_step_id = model_web.usage_journey_steps[0].efootprint_id
    uj_id = model_web.usage_journeys[0].efootprint_id

    server_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Shared Server",
            "Server",
            server_type="autoscaling",
            Storage_form_data=create_post_data_from_class_default_values("Initial Storage", "Storage"),
        ),
    )
    create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Shared Job", "Job", server=server_id),
        parent_id=uj_step_id,
    )

    up_1 = create_object(default_system_repository, _usage_pattern_post_data("UP 1", uj_id, initial_volume=1000))
    up_2 = create_object(default_system_repository, _usage_pattern_post_data("UP 2", uj_id, initial_volume=2000))

    delete_object(default_system_repository, up_1)

    storage_form_data = create_post_data_from_class_default_values("Updated Storage", "Storage")
    edit_object(
        default_system_repository,
        server_id,
        "Server",
        {
            "name": "Shared Server Updated",
            "average_carbon_intensity": "60",
            "average_carbon_intensity_unit": str(u.g / u.kWh),
            "Storage_form_data": json.dumps(storage_form_data),
        },
    )

    sd = default_system_repository.get_system_data()
    assert server_id in sd.get("Server", {})
    assert sd["Server"][server_id]["name"] == "Shared Server Updated"
    assert sd["Server"][server_id]["average_carbon_intensity"]["value"] == 60.0
    assert sd["System"]["uuid-system-1"]["usage_patterns"] == [up_2]
