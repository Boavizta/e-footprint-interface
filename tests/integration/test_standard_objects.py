"""Integration tests for standard web objects: usage journeys, usage patterns, servers, and jobs.

Ported from tests__old/model_builder/test_views_addition_web.py.
Dropped:
  - test_add_web_service_then_web_job: WebApplicationJob class removed.
  - test_add_server_then_ai_model_then_job: GenAIModel class removed; covered by test_create_ecologits_external_api_and_job.
  - test_add_external_api_with_large_model_*: ExternalAPI class removed (replaced by EcoLogitsGenAIExternalAPI).
  - open_edit_object_panel / model_builder_main round-trips: Django view concerns, not use-case concerns.
"""
import pytest

from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_COUNTRIES, DEFAULT_DEVICES, DEFAULT_NETWORKS
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object, edit_object


def _usage_pattern_post_data(name: str, uj_id: str) -> dict:
    return create_post_data_from_class_default_values(
        name, "UsagePattern",
        usage_journey=uj_id,
        devices=next(iter(DEFAULT_DEVICES.keys())),
        network=next(iter(DEFAULT_NETWORKS.keys())),
        country=next(iter(DEFAULT_COUNTRIES.keys())),
        hourly_usage_journey_starts__initial_volume=1000,
    )


def test_create_usage_journey(default_system_repository):
    uj_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("New Usage Journey", "UsageJourney", uj_steps=""),
    )
    assert any(uj.efootprint_id == uj_id for uj in ModelWeb(default_system_repository).usage_journeys)


def test_create_usage_journey_step(default_system_repository):
    uj_id = ModelWeb(default_system_repository).usage_journeys[0].efootprint_id
    nb_steps_before = len(ModelWeb(default_system_repository).usage_journey_steps)

    create_object(
        default_system_repository,
        create_post_data_from_class_default_values("New UJ Step", "UsageJourneyStep", jobs=""),
        parent_id=uj_id,
    )

    assert len(ModelWeb(default_system_repository).usage_journey_steps) == nb_steps_before + 1


def test_create_usage_journey_step_for_unlinked_journey(default_system_repository):
    """Adding a UJStep to a freshly created UJ (not yet in any UsagePattern) must not raise."""
    new_uj_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Standalone Journey", "UsageJourney", uj_steps=""),
    )
    create_object(
        default_system_repository,
        create_post_data_from_class_default_values("First Step", "UsageJourneyStep", jobs=""),
        parent_id=new_uj_id,
    )

    sd = default_system_repository.get_system_data()
    assert len(sd["UsageJourney"][new_uj_id]["uj_steps"]) == 1


def test_usage_pattern_create_edit_delete_flow(default_system_repository):
    uj_id = ModelWeb(default_system_repository).usage_journeys[0].efootprint_id
    nb_patterns_before = len(
        default_system_repository.get_system_data()["System"]["uuid-system-1"]["usage_patterns"])

    up_id = create_object(default_system_repository, _usage_pattern_post_data("New UP", uj_id))

    assert len(default_system_repository.get_system_data()["System"]["uuid-system-1"]["usage_patterns"]) == nb_patterns_before + 1

    edit_object(default_system_repository, up_id, "UsagePattern", {
        "hourly_usage_journey_starts__start_date": "2025-02-02",
        "hourly_usage_journey_starts__modeling_duration_value": "5",
        "hourly_usage_journey_starts__modeling_duration_unit": "month",
        "hourly_usage_journey_starts__initial_volume": "10000",
        "hourly_usage_journey_starts__initial_volume_timespan": "month",
        "hourly_usage_journey_starts__net_growth_rate_in_percentage": "10",
        "hourly_usage_journey_starts__net_growth_rate_timespan": "month",
    })

    sd = default_system_repository.get_system_data()
    assert sd["UsagePattern"][up_id]["hourly_usage_journey_starts"]["form_inputs"]["start_date"][:10] == "2025-02-02"

    delete_object(default_system_repository, up_id)

    sd = default_system_repository.get_system_data()
    assert len(sd["System"]["uuid-system-1"]["usage_patterns"]) == nb_patterns_before


def test_incomplete_modeling_raises_error_when_uj_has_no_steps(default_system_repository):
    uj_step_id = ModelWeb(default_system_repository).usage_journey_steps[0].efootprint_id
    uj_id = ModelWeb(default_system_repository).usage_journeys[0].efootprint_id

    delete_object(default_system_repository, uj_step_id)
    assert "UsageJourneyStep" not in default_system_repository.get_system_data()

    create_object(default_system_repository, _usage_pattern_post_data("New UP", uj_id))

    with pytest.raises(ValueError, match="no usage journey step"):
        ModelWeb(default_system_repository).raise_incomplete_modeling_errors()


def test_usage_pattern_delete_then_gpu_server_create(default_system_repository):
    uj_id = ModelWeb(default_system_repository).usage_journeys[0].efootprint_id
    up_id = create_object(default_system_repository, _usage_pattern_post_data("Temp UP", uj_id))

    delete_object(default_system_repository, up_id)

    server_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "AI Server", "GPUServer", server_type="autoscaling",
            Storage_form_data=create_post_data_from_class_default_values("Server Storage", "Storage"),
        ),
    )

    assert server_id in default_system_repository.get_system_data()["GPUServer"]


def test_create_ecologits_external_api_and_job(default_system_repository):
    uj_step_id = ModelWeb(default_system_repository).usage_journey_steps[0].efootprint_id

    api_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test GenAI API", "EcoLogitsGenAIExternalAPI",
            provider="mistralai", model_name="open-mistral-7b",
        ),
    )
    job_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test GenAI Job", "EcoLogitsGenAIExternalAPIJob", external_api=api_id),
        parent_id=uj_step_id,
    )

    sd = default_system_repository.get_system_data()
    assert api_id in sd.get("EcoLogitsGenAIExternalAPI", {}) or api_id in sd.get("EcoLogitsGenAIExternalAPIServer", {})
    assert job_id in sd["EcoLogitsGenAIExternalAPIJob"]
