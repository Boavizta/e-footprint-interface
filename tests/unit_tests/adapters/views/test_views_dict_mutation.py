import pytest

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.application.use_cases import CreateObjectInput, CreateObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values


def _setup_session(client, system_data: dict) -> None:
    SessionSystemRepository(client.session).save_data(system_data)


def _create_object_in_session(client, post_data: dict, parent_id: str | None = None) -> str:
    repository = SessionSystemRepository(client.session)
    object_type = post_data["type_object_available"]
    parsed_form_data = parse_form_data(post_data, object_type)
    output = CreateObjectUseCase(repository).execute(
        CreateObjectInput(object_type=object_type, form_data=parsed_form_data, parent_id=parent_id)
    )
    return output.created_object_id


def _model_web(client) -> ModelWeb:
    return ModelWeb(SessionSystemRepository(client.session))


def _assert_error_modal_response(response, message: str) -> None:
    body = response.content.decode()
    assert response.status_code == 200
    assert message in body
    assert "openModalDialog" in response["HX-Trigger-After-Settle"]


@pytest.mark.django_db
class TestDictMutationViews:

    def test_device_can_be_linked_updated_and_unlinked(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        device_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Sensor", "EdgeDevice", components=""),
        )
        group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Rack A", "EdgeDeviceGroup"),
        )

        link_response = client.post(
            f"/model_builder/link-dict-entry/{device_id}/", {"parent_id": group_id})

        assert link_response.status_code == 200
        assert "hx-swap-oob='outerHTML:#edge-device-groups-list'" in link_response.content.decode()
        assert "hx-swap-oob='outerHTML:#edge-devices-list'" in link_response.content.decode()

        model_web = _model_web(client)
        group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
        assert group.edge_device_counts[device].value.magnitude == 1
        assert [edge_device.efootprint_id for edge_device in model_web.ungrouped_edge_devices] == []

        update_response = client.post(
            f"/model_builder/update-dict-count/{group_id}/{device_id}/",
            {"count": "3"},
        )

        assert update_response.status_code == 200
        updated_model_web = _model_web(client)
        updated_group = updated_model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        updated_device = updated_model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
        assert updated_group.edge_device_counts[updated_device].value.magnitude == 3

        unlink_response = client.post(f"/model_builder/unlink-dict-entry/{group_id}/{device_id}/")

        assert unlink_response.status_code == 200
        final_model_web = _model_web(client)
        final_group = final_model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        final_device = final_model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
        assert final_device not in final_group.edge_device_counts
        assert [edge_device.efootprint_id for edge_device in final_model_web.ungrouped_edge_devices] == [device_id]

    def test_linking_sub_group_removes_it_from_root_groups(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        parent_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Rack A", "EdgeDeviceGroup"),
        )
        child_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Shelf 1", "EdgeDeviceGroup"),
        )

        response = client.post(
            f"/model_builder/link-dict-entry/{child_group_id}/", {"parent_id": parent_group_id})

        assert response.status_code == 200
        model_web = _model_web(client)
        root_group_ids = [group.efootprint_id for group in model_web.root_edge_device_groups]
        parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_group_id, "EdgeDeviceGroup")
        child_group = model_web.get_efootprint_object_from_efootprint_id(child_group_id, "EdgeDeviceGroup")

        assert root_group_ids == [parent_group_id]
        assert parent_group.sub_group_counts[child_group].value.magnitude == 1

    @pytest.mark.parametrize(
        ("raw_count", "message"),
        [
            ("abc", "Count must be a number."),
            ("-1", "Count must be positive."),
        ],
    )
    def test_update_dict_count_rejects_invalid_count(self, client, default_system_repository, raw_count, message):
        _setup_session(client, default_system_repository.get_system_data())
        device_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Sensor", "EdgeDevice", components=""),
        )
        group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Rack A", "EdgeDeviceGroup"),
        )
        client.post(f"/model_builder/link-dict-entry/{device_id}/", {"parent_id": group_id})

        response = client.post(
            f"/model_builder/update-dict-count/{group_id}/{device_id}/",
            {"count": raw_count},
        )

        _assert_error_modal_response(response, message)
        model_web = _model_web(client)
        group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
        assert group.edge_device_counts[device].value.magnitude == 1

    def test_link_dict_entry_rejects_self_link_for_group(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Rack A", "EdgeDeviceGroup"),
        )

        response = client.post(
            f"/model_builder/link-dict-entry/{group_id}/", {"parent_id": group_id})

        _assert_error_modal_response(response, "A group cannot be linked to itself or one of its descendants.")
        model_web = _model_web(client)
        group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        assert group.sub_group_counts == {}
        assert [root_group.efootprint_id for root_group in model_web.root_edge_device_groups] == [group_id]

    def test_link_dict_entry_rejects_descendant_cycle(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        parent_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
        )
        child_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
        )
        client.post(
            f"/model_builder/link-dict-entry/{child_group_id}/", {"parent_id": parent_group_id})

        response = client.post(
            f"/model_builder/link-dict-entry/{parent_group_id}/", {"parent_id": child_group_id})

        _assert_error_modal_response(response, "A group cannot be linked to itself or one of its descendants.")
        model_web = _model_web(client)
        parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_group_id, "EdgeDeviceGroup")
        child_group = model_web.get_efootprint_object_from_efootprint_id(child_group_id, "EdgeDeviceGroup")
        assert parent_group.sub_group_counts[child_group].value.magnitude == 1
        assert child_group.sub_group_counts == {}
        assert [root_group.efootprint_id for root_group in model_web.root_edge_device_groups] == [parent_group_id]
