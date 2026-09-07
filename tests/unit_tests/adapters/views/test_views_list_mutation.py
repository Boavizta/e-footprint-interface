import pytest

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.application.use_cases import CreateObjectInput, CreateObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_COUNTRIES, DEFAULT_NETWORKS
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values


def _setup_session(client, system_data: dict) -> None:
    SessionSystemRepository(client.session).save_data(system_data)


def _create_object_in_session(client, post_data: dict) -> str:
    repository = SessionSystemRepository(client.session)
    object_type = post_data["type_object_available"]
    output = CreateObjectUseCase(repository).execute(
        CreateObjectInput(
            object_type=object_type,
            form_data=parse_form_data(post_data, object_type),
        )
    )
    return output.created_object_id


def _create_edge_pattern(client, name: str, journey_ids: list[str]) -> str:
    return _create_object_in_session(
        client,
        create_post_data_from_class_default_values(
            name,
            "EdgeUsagePattern",
            edge_usage_journeys=";".join(journey_ids),
            network=next(iter(DEFAULT_NETWORKS)),
            country=next(iter(DEFAULT_COUNTRIES)),
            hourly_deployment_starts__initial_volume=1,
        ),
    )


def _pattern_journey_ids(client, pattern_id: str) -> list[str]:
    pattern = ModelWeb(SessionSystemRepository(client.session)).flat_efootprint_objs_dict[pattern_id]
    return [journey.id for journey in pattern.edge_usage_journeys]


@pytest.mark.django_db
class TestListMutationViews:
    def test_edge_journey_edit_panel_renders_usage_pattern_backlinks(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        first_journey_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("First bundle", "EdgeUsageJourney", edge_functions=""),
        )
        second_journey_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Second bundle", "EdgeUsageJourney", edge_functions=""),
        )
        pattern_id = _create_edge_pattern(client, "Field deployment", [first_journey_id])

        response = client.get(f"/model_builder/open-edit-object-panel/{second_journey_id}/")
        body = response.content.decode()

        assert response.status_code == 200
        assert "Used in usage patterns" in body
        assert "Field deployment" in body
        assert f"/model_builder/link-list-entry/{second_journey_id}/" in body
        assert f'value="{pattern_id}"' in body

    def test_list_backlink_can_link_and_unlink_without_removing_last_required_journey(
        self, client, default_system_repository
    ):
        _setup_session(client, default_system_repository.get_system_data())
        first_journey_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("First bundle", "EdgeUsageJourney", edge_functions=""),
        )
        second_journey_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Second bundle", "EdgeUsageJourney", edge_functions=""),
        )
        pattern_id = _create_edge_pattern(client, "Field deployment", [first_journey_id])

        link_response = client.post(
            f"/model_builder/link-list-entry/{second_journey_id}/",
            {"parent_id": pattern_id},
        )

        assert link_response.status_code == 200
        assert _pattern_journey_ids(client, pattern_id) == [first_journey_id, second_journey_id]
        assert f"outerHTML:#list-membership-section-{second_journey_id}" in link_response.content.decode()

        unlink_response = client.post(f"/model_builder/unlink-list-entry/{pattern_id}/{first_journey_id}/")

        assert unlink_response.status_code == 200
        assert _pattern_journey_ids(client, pattern_id) == [second_journey_id]

        rejected_response = client.post(f"/model_builder/unlink-list-entry/{pattern_id}/{second_journey_id}/")

        assert rejected_response.status_code == 200
        assert "requires at least one edge usage journey" in rejected_response.content.decode()
        assert _pattern_journey_ids(client, pattern_id) == [second_journey_id]
