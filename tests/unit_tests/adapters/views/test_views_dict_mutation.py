from copy import deepcopy

import numpy as np
import pytest
from pint import Quantity
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job

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


def _efootprint_obj_by_name(model_web: ModelWeb, class_str: str, name: str):
    return next(obj for obj in model_web.get_efootprint_objects_from_efootprint_type(class_str) if obj.name == name)


def _system_data_with_recurrent_server_need(minimal_system_data: dict) -> dict:
    """Minimal system data extended with a free-floating RecurrentServerNeed and its job graph."""
    storage = Storage.from_defaults("RSN Storage")
    server = Server.from_defaults("RSN Server", storage=storage)
    rsn_job = Job.from_defaults("RSN Job", server=server)
    edge_storage = EdgeStorage.from_defaults("RSN Edge Storage", base_storage_need=SourceValue(100 * u.GB_stored))
    computer = EdgeComputer.from_defaults(
        "RSN Edge Computer", storage=edge_storage, base_compute_consumption=SourceValue(0.1 * u.cpu_core))
    server_need = RecurrentServerNeed(
        "Server Need",
        edge_device=computer,
        recurrent_volume_per_edge_device=SourceRecurrentValues(
            Quantity(np.array([1] * 168, dtype=np.float32), u.occurrence)),
        jobs=[rsn_job],
    )
    fragment = system_to_json(server_need, save_calculated_attributes=False)
    system_data = deepcopy(minimal_system_data)
    for class_key, objs in fragment.items():
        if isinstance(objs, dict):
            system_data.setdefault(class_key, {}).update(objs)
    return system_data


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


@pytest.mark.django_db
class TestWeightedRelationshipDictMutations:
    """The generalized endpoints serve uj_steps and the two jobs relationships like edge group counts."""

    def test_job_count_update_link_and_unlink_across_steps(self, client, minimal_system_data):
        _setup_session(client, minimal_system_data)
        model_web = _model_web(client)
        journey = _efootprint_obj_by_name(model_web, "UsageJourney", "Test Journey")
        step_id = _efootprint_obj_by_name(model_web, "UsageJourneyStep", "Test Step").id
        job_id = _efootprint_obj_by_name(model_web, "Job", "Test Job").id
        second_step_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Second Step", "UsageJourneyStep", jobs=""),
            parent_id=journey.id,
        )

        update_response = client.post(f"/model_builder/update-dict-count/{step_id}/{job_id}/", {"count": "2.5"})

        assert update_response.status_code == 200
        model_web = _model_web(client)
        step, job = model_web.flat_efootprint_objs_dict[step_id], model_web.flat_efootprint_objs_dict[job_id]
        assert step.jobs[job].value.magnitude == 2.5

        link_response = client.post(f"/model_builder/link-dict-entry/{job_id}/", {"parent_id": second_step_id})

        assert link_response.status_code == 200
        model_web = _model_web(client)
        job = model_web.flat_efootprint_objs_dict[job_id]
        second_step = model_web.flat_efootprint_objs_dict[second_step_id]
        assert second_step.jobs[job].value.magnitude == 1
        assert second_step.jobs[job].label == "Times per step"
        # Per-relationship independence: the multiplier in the first step is untouched.
        assert model_web.flat_efootprint_objs_dict[step_id].jobs[job].value.magnitude == 2.5

        unlink_response = client.post(f"/model_builder/unlink-dict-entry/{step_id}/{job_id}/")

        assert unlink_response.status_code == 200
        model_web = _model_web(client)
        job = model_web.flat_efootprint_objs_dict[job_id]
        assert job not in model_web.flat_efootprint_objs_dict[step_id].jobs
        assert model_web.flat_efootprint_objs_dict[second_step_id].jobs[job].value.magnitude == 1

    def test_step_weight_update_link_and_unlink_across_journeys(self, client, minimal_system_data):
        _setup_session(client, minimal_system_data)
        model_web = _model_web(client)
        journey_id = _efootprint_obj_by_name(model_web, "UsageJourney", "Test Journey").id
        step_id = _efootprint_obj_by_name(model_web, "UsageJourneyStep", "Test Step").id
        second_journey_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Second Journey", "UsageJourney", uj_steps=""),
        )

        update_response = client.post(
            f"/model_builder/update-dict-count/{journey_id}/{step_id}/", {"count": "0.5", "recomputation": "true"})

        assert update_response.status_code == 200
        model_web = _model_web(client)
        step = model_web.flat_efootprint_objs_dict[step_id]
        journey = model_web.flat_efootprint_objs_dict[journey_id]
        assert journey.uj_steps[step].value.magnitude == 0.5
        # The inline count post recomputes immediately: the persisted journey duration honors the new weight.
        assert journey.duration.value == 0.5 * step.user_time_spent.value

        link_response = client.post(f"/model_builder/link-dict-entry/{step_id}/", {"parent_id": second_journey_id})

        assert link_response.status_code == 200
        model_web = _model_web(client)
        step = model_web.flat_efootprint_objs_dict[step_id]
        second_journey = model_web.flat_efootprint_objs_dict[second_journey_id]
        assert second_journey.uj_steps[step].value.magnitude == 1
        assert second_journey.uj_steps[step].label == "Times per journey"
        assert model_web.flat_efootprint_objs_dict[journey_id].uj_steps[step].value.magnitude == 0.5

        unlink_response = client.post(f"/model_builder/unlink-dict-entry/{journey_id}/{step_id}/")

        assert unlink_response.status_code == 200
        model_web = _model_web(client)
        step = model_web.flat_efootprint_objs_dict[step_id]
        assert step not in model_web.flat_efootprint_objs_dict[journey_id].uj_steps
        assert model_web.flat_efootprint_objs_dict[second_journey_id].uj_steps[step].value.magnitude == 1

    def test_count_update_does_not_rerender_sibling_cards(self, client, minimal_system_data):
        """A magnitude-only count edit must not swap the parent card back: doing so would clobber a
        sibling count input the user is editing within the round-trip. The sibling's card (and its
        name) must be absent from the response entirely."""
        _setup_session(client, minimal_system_data)
        model_web = _model_web(client)
        journey = _efootprint_obj_by_name(model_web, "UsageJourney", "Test Journey")
        step_id = _efootprint_obj_by_name(model_web, "UsageJourneyStep", "Test Step").id
        _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Sibling Step", "UsageJourneyStep", jobs=""),
            parent_id=journey.id,
        )

        journey_web_id = _model_web(client).get_web_object_from_efootprint_id(journey.id).web_id

        update_response = client.post(f"/model_builder/update-dict-count/{journey.id}/{step_id}/", {"count": "2"})

        assert update_response.status_code == 200
        body = update_response.content.decode()
        # The sibling's card is not re-rendered (it would carry the sibling's count input), so a value
        # being typed there can't be overwritten when this response lands.
        assert "Sibling Step" not in body
        # No parent journey card outerHTML swap at all.
        assert f"outerHTML:#{journey_web_id}" not in body

    def test_recurrent_server_need_job_count_update_link_and_unlink(self, client, minimal_system_data):
        _setup_session(client, _system_data_with_recurrent_server_need(minimal_system_data))
        model_web = _model_web(client)
        rsn_id = _efootprint_obj_by_name(model_web, "RecurrentServerNeed", "Server Need").id
        rsn_job_id = _efootprint_obj_by_name(model_web, "Job", "RSN Job").id
        step_job_id = _efootprint_obj_by_name(model_web, "Job", "Test Job").id

        update_response = client.post(f"/model_builder/update-dict-count/{rsn_id}/{rsn_job_id}/", {"count": "4"})

        assert update_response.status_code == 200
        model_web = _model_web(client)
        rsn_job = model_web.flat_efootprint_objs_dict[rsn_job_id]
        assert model_web.flat_efootprint_objs_dict[rsn_id].jobs[rsn_job].value.magnitude == 4

        link_response = client.post(f"/model_builder/link-dict-entry/{step_job_id}/", {"parent_id": rsn_id})

        assert link_response.status_code == 200
        model_web = _model_web(client)
        step_job = model_web.flat_efootprint_objs_dict[step_job_id]
        recurrent_server_need = model_web.flat_efootprint_objs_dict[rsn_id]
        assert recurrent_server_need.jobs[step_job].value.magnitude == 1
        assert recurrent_server_need.jobs[step_job].label == "Times per occurrence"

        unlink_response = client.post(f"/model_builder/unlink-dict-entry/{rsn_id}/{step_job_id}/")

        assert unlink_response.status_code == 200
        model_web = _model_web(client)
        step_job = model_web.flat_efootprint_objs_dict[step_job_id]
        assert step_job not in model_web.flat_efootprint_objs_dict[rsn_id].jobs
        # Still linked to its usage journey step, so the job survives the unlink.
        assert step_job.name == "Test Job"
