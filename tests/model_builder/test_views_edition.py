from unittest.mock import patch
import os

from django.http import QueryDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.services.generative_ai_ecologits import GenAIModel, GenAIJob
from efootprint.constants.countries import Countries
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.device import Device
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.logger import logger
from efootprint.constants.units import u

from model_builder.addition.views_addition import add_object
from model_builder.class_structure import generate_object_edition_structure
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb
from model_builder.edition.views_edition import edit_object
from model_builder.views_deletion import delete_object
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsEdition(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_edition(self):
        logger.info(f"Creating service")
        service_data = self.create_web_application_data(name="New service", parent_id="uuid-Server-1")
        post_data = QueryDict(mutable=True)
        post_data.update(service_data)

        service_request = self.factory.post("/add-object/Service", data=post_data)
        self._add_session_to_request(service_request, self.system_data)
        response = add_object(service_request, "Service")
        service_id = next(iter(service_request.session["system_data"]["WebApplication"].keys()))
        self.assertEqual(response.status_code, 200)

        logger.info(f"Creating job")
        job_data = self.create_web_application_job_data(
            name="New job", parent_id="uuid-20-min-streaming-on-Youtube", service_id=service_id, server="uuid-Server-1")
        post_data = QueryDict(mutable=True)
        post_data.update(job_data)

        job_request = self.factory.post("/model_builder/add-object/Job/", data=post_data)
        self._add_session_to_request(job_request, service_request.session["system_data"])
        response = add_object(job_request, "Job")
        self.assertEqual(response.status_code, 200)
        new_job_id = next(iter(job_request.session["system_data"]["WebApplicationJob"].keys()))

        model_web = ModelWeb(job_request.session)
        job = model_web.get_web_object_from_efootprint_id(new_job_id)

        job_edition_fields, job_edition_fields_advanced, dynamic_form_data = generate_object_edition_structure(
            job, attributes_to_skip=["service"])

        ref_dynamic_form_data = {"dynamic_lists": []}

        self.assertDictEqual(dynamic_form_data, ref_dynamic_form_data)
        self.assertEqual(job_request.session["system_data"]["WebApplicationJob"][new_job_id]["name"], "New job")

    def test_edit_genai_model_provider_with_recompute_true(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        gpu_server = GPUServer.from_defaults("GPU server", compute=SourceValue(16 * u.gpu), storage=Storage.ssd())
        first_provider = GenAIModel.list_values["provider"][0]
        first_model_name = GenAIModel.conditional_list_values[
            "model_name"]["conditional_list_values"][first_provider][0]
        genai_service = GenAIModel.from_defaults(
            "GenAI service", server=gpu_server, provider=first_provider, model_name=first_model_name)
        genai_job = GenAIJob.from_defaults("genai job", service=genai_service)
        usage_journey = UsageJourney(
            "usage journey", uj_steps=[UsageJourneyStep("step", jobs=[genai_job],
                                                        user_time_spent=SourceValue(1 * u.min))])
        usage_pattern = UsagePatternFromForm.from_defaults(
            "usage pattern", usage_journey=usage_journey, devices=[Device.laptop()], network=Network.wifi_network(),
            country=Countries.FRANCE())
        system = System("Test system", usage_patterns=[usage_pattern], edge_usage_patterns=[])
        logger.info(f"Created GenAI service with provider {first_provider} and model name {first_model_name}")

        post_data = QueryDict(mutable=True)
        second_provider = GenAIModel.list_values["provider"][1]
        second_model_name = GenAIModel.conditional_list_values[
            "model_name"]["conditional_list_values"][second_provider][0]
        edit_data = self.create_genai_model_data(
            name="Gen AI service",provider=second_provider,model_name=second_model_name, recomputation="true")
        edit_data["GenAIModel_server"] = gpu_server.id
        post_data.update(edit_data)

        edit_service_request = self.factory.post(f"/edit-object/{genai_service.id}", data=post_data)
        self._add_session_to_request(
            edit_service_request, system_to_json(system, save_calculated_attributes=False))

        response = edit_object(edit_service_request, genai_service.id)

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_edit_server_and_storage(self, mock_render_exception_modal):
        server_id = "uuid-Server-1"
        storage_id = "uuid-Default-SSD-storage-1"

        post_data = QueryDict(mutable=True)
        post_data.update(
            {"name": ["New server"], "carbon_footprint_fabrication": ["60"], "carbon_footprint_fabrication_unit": "kg",
                "storage_form_data":
                [f'{{"storage_id":"{storage_id}", "name":"server 1 default ssd", '
                 f'"carbon_footprint_fabrication_per_storage_capacity":"160.0",'
                 f'"carbon_footprint_fabrication_per_storage_capacity_unit":"kg/TB"}}']}
        )

        edit_server_request = self.factory.post(f"/edit-object/{server_id}", data=post_data)
        self._add_session_to_request(edit_server_request, self.system_data)
        response = edit_object(edit_server_request, server_id)

        mock_render_exception_modal.assert_not_called()
        self.assertEqual(response.status_code, 200)

        server = edit_server_request.session["system_data"]["Server"][server_id]
        storage = edit_server_request.session["system_data"]["Storage"][storage_id]

        self.assertEqual(server["name"], "New server")
        self.assertEqual(server["carbon_footprint_fabrication"]["value"], 60.0)
        self.assertEqual(storage["name"], "server 1 default ssd")
        self.assertEqual(storage["carbon_footprint_fabrication_per_storage_capacity"]["value"], 160.0)

    def test_edition_with_recompute(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        server_id = "uuid-Server-1"
        storage_id = "uuid-Default-SSD-storage-1"

        post_data = QueryDict(mutable=True)
        post_data.update(
            {"name": ["New server"], "carbon_footprint_fabrication": ["60"], "carbon_footprint_fabrication_unit": "kg",
             "storage_form_data":
                 [f'{{"storage_id":"{storage_id}", "name":"server 1 default ssd", '
                  f'"carbon_footprint_fabrication_per_storage_capacity":"170.0",'
                  f'"carbon_footprint_fabrication_per_storage_capacity_unit":"kg/TB"}}'],
             "recomputation": ["true"],}
        )

        edit_server_request = self.factory.post(f"/edit-object/{server_id}", data=post_data)
        self._add_session_to_request(edit_server_request, self.system_data)
        response = edit_object(edit_server_request, server_id)

        self.assertEqual(response.status_code, 200)

    def test_suppress_one_of_2_usage_patterns_then_update_server_used_by_both(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        logger.info("Deleting first usage pattern")
        up_id = "uuid-Video-watching-in-France-in-the-morning"
        delete_request = self.factory.post(f"/model_builder/delete-object/{up_id}/")
        self._add_session_to_request(delete_request, self.system_data)
        response = delete_object(delete_request, up_id)
        self.assertEqual(response.status_code, 204)

        logger.info("Updating server used by both usage patterns")
        server_id = "uuid-Server-1"
        post_data = QueryDict(mutable=True)
        post_data.update(
            {"name": ["New server"], "average_carbon_intensity": ["60"], "average_carbon_intensity_unit":
                "gram / kilowatt_hour",
             "storage_form_data":
                 [f'{{"storage_id":"uuid-Default-SSD-storage-1", "name":"server 1 default ssd", '
                  f'"carbon_footprint_fabrication_per_storage_capacity":"160.0",'
                  f'"carbon_footprint_fabrication_per_storage_capacity_unit":"kg/TB"}}'],
             "recomputation": ["true"],}
        )
        edit_server_request = self.factory.post(f"/edit-object/{server_id}", data=post_data)
        self._add_session_to_request(edit_server_request, delete_request.session["system_data"])
        response = edit_object(edit_server_request, server_id)
        self.assertEqual(response.status_code, 200)

    def test_reorder_objects(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        new_uj_steps = ("uuid-02e4s-of-upload;uuid-Dailymotion-step;uuid-20-min-streaming-on-Youtube;"
                        "uuid-20-min-streaming-on-TikTok")
        logger.info("Edit daily video usage reordering step 1 to position 2 and step 3 to position 4")
        post_data = QueryDict(mutable=True)
        post_data.update(
            {"UsageJourney_name": ["Daily video usage"],"UsageJourney_uj_steps": [new_uj_steps]})

        edit_usage_journey_request = self.factory.post(f"/edit-object/uuid-Daily-video-usage", data=post_data)
        self._add_session_to_request(edit_usage_journey_request, self.system_data)
        response = edit_object(edit_usage_journey_request, "uuid-Daily-video-usage")
        self.assertEqual(response.status_code, 200)

        model_web = ModelWeb(edit_usage_journey_request.session)
        usage_journey = model_web.get_web_object_from_efootprint_id("uuid-Daily-video-usage")
        uj_steps_ids = [uj_step.efootprint_id for uj_step in usage_journey.uj_steps]
        self.assertEqual(new_uj_steps, ";".join(uj_steps_ids))


    def test_reorder_objects_with_element_remove(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        new_uj_steps = ("uuid-02e4s-of-upload;uuid-Dailymotion-step;uuid-20-min-streaming-on-TikTok")
        logger.info("Edit daily video usage reordering step 1 to position 2 and removing step 3")
        post_data = QueryDict(mutable=True)
        post_data.update(
            {"UsageJourney_name": ["Daily video usage"],"UsageJourney_uj_steps": [new_uj_steps]})

        edit_usage_journey_request = self.factory.post(f"/edit-object/uuid-Daily-video-usage", data=post_data)
        self._add_session_to_request(edit_usage_journey_request, self.system_data)
        response = edit_object(edit_usage_journey_request, "uuid-Daily-video-usage")
        self.assertEqual(response.status_code, 200)

        model_web = ModelWeb(edit_usage_journey_request.session)
        usage_journey = model_web.get_web_object_from_efootprint_id("uuid-Daily-video-usage")
        uj_steps_ids = [uj_step.efootprint_id for uj_step in usage_journey.uj_steps]
        self.assertEqual(new_uj_steps, ";".join(uj_steps_ids))
