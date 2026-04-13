import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

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


def _extract_select_html(response_body: str, select_id: str) -> str:
    marker = f'id="{select_id}"'
    start = response_body.index(marker)
    select_start = response_body.rfind("<select", 0, start)
    select_end = response_body.index("</select>", start) + len("</select>")
    return response_body[select_start:select_end]


@pytest.mark.django_db
class TestViewsEdition:

    def test_open_edit_object_panel_for_edge_device_renders_group_memberships(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        device_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Shared Sensor", "EdgeDevice", components=""),
        )
        group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Alpha", "EdgeDeviceGroup"),
        )
        model_web = _model_web(client)
        device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
        group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        group.edge_device_counts[device] = SourceValue(4 * u.dimensionless)
        model_web.persist_to_cache()

        response = client.get(f"/model_builder/open-edit-object-panel/{device_id}/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "Group membership" in body
        assert "Alpha" in body
        assert f"/model_builder/update-dict-count/{group_id}/{device_id}/" in body
        assert f"/model_builder/unlink-dict-entry/{group_id}/{device_id}/" in body

    def test_open_edit_object_panel_for_group_excludes_illegal_sub_group_choices(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        campus_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Campus", "EdgeDeviceGroup"),
        )
        building_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
        )
        floor_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
        )
        room_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Room", "EdgeDeviceGroup"),
        )
        annex_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Annex", "EdgeDeviceGroup"),
        )
        del annex_id

        model_web = _model_web(client)
        campus = model_web.get_efootprint_object_from_efootprint_id(campus_id, "EdgeDeviceGroup")
        building = model_web.get_efootprint_object_from_efootprint_id(building_id, "EdgeDeviceGroup")
        floor = model_web.get_efootprint_object_from_efootprint_id(floor_id, "EdgeDeviceGroup")
        room = model_web.get_efootprint_object_from_efootprint_id(room_id, "EdgeDeviceGroup")
        campus.sub_group_counts[building] = SourceValue(1 * u.dimensionless)
        building.sub_group_counts[floor] = SourceValue(1 * u.dimensionless)
        floor.sub_group_counts[room] = SourceValue(2 * u.dimensionless)
        model_web.persist_to_cache()

        response = client.get(f"/model_builder/open-edit-object-panel/{floor_id}/")

        body = response.content.decode()
        subgroup_select_html = _extract_select_html(body, "select-new-object-EdgeDeviceGroup_sub_group_counts")
        assert response.status_code == 200
        assert "Group members" in body
        assert ">Annex<" in subgroup_select_html
        assert ">Campus<" not in subgroup_select_html
        assert ">Building<" not in subgroup_select_html
        assert ">Floor<" not in subgroup_select_html
        assert ">Room<" in subgroup_select_html

    def test_edit_group_refreshes_root_groups_and_ungrouped_devices_lists(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        parent_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
        )
        child_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
        )
        device_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Lobby Sensor", "EdgeDevice", components=""),
        )

        response = client.post(
            f"/model_builder/edit-object/{parent_group_id}/",
            {
                "EdgeDeviceGroup_name": "Building",
                "EdgeDeviceGroup_sub_group_counts": f'{{"{child_group_id}": 2}}',
                "EdgeDeviceGroup_edge_device_counts": f'{{"{device_id}": 4}}',
            },
        )

        body = response.content.decode()
        assert response.status_code == 200
        assert "hx-swap-oob='outerHTML:#edge-device-groups-list'" in body
        assert "hx-swap-oob='outerHTML:#edge-devices-list'" in body

        model_web = _model_web(client)
        parent = model_web.get_efootprint_object_from_efootprint_id(parent_group_id, "EdgeDeviceGroup")
        child = model_web.get_efootprint_object_from_efootprint_id(child_group_id, "EdgeDeviceGroup")
        device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")

        assert parent.sub_group_counts[child].value.magnitude == 2
        assert parent.edge_device_counts[device].value.magnitude == 4
        assert [group.efootprint_id for group in model_web.root_edge_device_groups] == [parent_group_id]
        assert [edge_device.efootprint_id for edge_device in model_web.ungrouped_edge_devices] == []
