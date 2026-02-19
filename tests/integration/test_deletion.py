"""Integration tests for object deletion: standard jobs, services, and edge hardware.

Ported from tests__old/model_builder/test_views_deletion.py.
Dropped:
  - Django request/session scaffolding: not a use-case concern.
  - test_delete_job_linked_to_service_then_service (GenAIJob/GenAIModel): both classes removed.
    Equivalent covered by test_delete_ecologits_job_then_service.
"""
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object


def test_delete_video_streaming_job(minimal_repository):
    """Deleting a VideoStreamingJob (list deletion path) removes it from the UJStep and system_data."""
    uj_step_id = ModelWeb(minimal_repository).usage_journey_steps[0].efootprint_id
    existing_server_id = next(iter(minimal_repository.get_system_data()["Server"]))

    service_id = create_object(
        minimal_repository,
        create_post_data_from_class_default_values("Test VideoStreaming", "VideoStreaming",
                                                   efootprint_id_of_parent_to_link_to=existing_server_id),
    )
    job_id = create_object(
        minimal_repository,
        create_post_data_from_class_default_values("Test VideoStreamingJob", "VideoStreamingJob", service=service_id),
        parent_id=uj_step_id,
    )

    assert "VideoStreamingJob" in minimal_repository.get_system_data()

    delete_object(minimal_repository, job_id)

    sd = minimal_repository.get_system_data()
    assert "VideoStreamingJob" not in sd
    assert job_id not in sd["UsageJourneyStep"][uj_step_id]["jobs"]


def test_delete_ecologits_job_then_service(default_system_repository):
    """Deleting an EcoLogits job then its service clears both from system_data."""
    uj_step_id = ModelWeb(default_system_repository).usage_journey_steps[0].efootprint_id

    api_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test GenAI API", "EcoLogitsGenAIExternalAPI", provider="mistralai", model_name="open-mistral-7b"),
    )
    job_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test GenAI Job", "EcoLogitsGenAIExternalAPIJob", external_api=api_id),
        parent_id=uj_step_id,
    )

    assert "EcoLogitsGenAIExternalAPIJob" in default_system_repository.get_system_data()

    delete_object(default_system_repository, job_id)

    sd = default_system_repository.get_system_data()
    assert "EcoLogitsGenAIExternalAPIJob" not in sd

    delete_object(default_system_repository, api_id)

    sd = default_system_repository.get_system_data()
    assert "EcoLogitsGenAIExternalAPIServer" not in sd


def test_delete_edge_computer_cascades_to_components(default_system_repository):
    """Deleting an EdgeComputer also removes its CPU component, RAM component, and storage."""
    edge_computer_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Computer", "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage"),
        ),
    )

    sd = default_system_repository.get_system_data()
    assert edge_computer_id in sd["EdgeComputer"]
    assert "EdgeComputerCPUComponent" in sd
    assert "EdgeComputerRAMComponent" in sd
    assert "EdgeStorage" in sd

    delete_object(default_system_repository, edge_computer_id)

    sd = default_system_repository.get_system_data()
    assert "EdgeComputer" not in sd
    assert "EdgeComputerCPUComponent" not in sd
    assert "EdgeComputerRAMComponent" not in sd
    assert "EdgeStorage" not in sd


def test_delete_edge_appliance_cascades_to_component(default_system_repository):
    """Deleting an EdgeAppliance also removes its appliance component."""
    edge_appliance_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Edge Appliance", "EdgeAppliance"),
    )

    sd = default_system_repository.get_system_data()
    assert edge_appliance_id in sd["EdgeAppliance"]
    assert "EdgeApplianceComponent" in sd

    delete_object(default_system_repository, edge_appliance_id)

    sd = default_system_repository.get_system_data()
    assert "EdgeAppliance" not in sd
    assert "EdgeApplianceComponent" not in sd
