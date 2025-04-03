from unittest.mock import patch
import os

from django.http import QueryDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.logger import logger
from efootprint.constants.units import u

from model_builder.addition.views_addition import add_object
from model_builder.class_structure import generate_object_edition_structure
from model_builder.model_web import ModelWeb
from model_builder.edition.views_edition import edit_object
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsEdition(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join("tests", "model_builder", "default_system_data.json")

    def test_edition(self):
        logger.info(f"Creating service")
        post_data = QueryDict(mutable=True)
        post_data.update({'name': ['New service'],
                            'efootprint_id_of_parent_to_link_to': ['uuid-Server-1'],
                          'type_object_available': ['WebApplication'],
                          'technology': ['php-symfony'], 'base_ram_consumption': ['2'],
                          'bits_per_pixel': ['0.1'], 'static_delivery_cpu_cost': ['4.0'],
                          'ram_buffer_per_user': ['50']}
        )

        service_request = self.factory.post('/add-object/Service', data=post_data)
        self._add_session_to_request(service_request, self.system_data)
        response = add_object(service_request, 'Service')
        service_id = next(iter(service_request.session["system_data"]["WebApplication"].keys()))
        self.assertEqual(response.status_code, 200)

        logger.info(f"Creating job")
        post_data = QueryDict(mutable=True)
        post_data.update(
        {'name': ['New job'], 'server': ['uuid-Server-1'],
         'efootprint_id_of_parent_to_link_to': ['uuid-20-min-streaming-on-Youtube'],
         'service': [service_id],
         'type_object_available': ['WebApplicationJob'],
         'implementation_details': ['aggregation-code-side'],
         'data_transferred': ['150'], 'data_stored': ['100']}
        )

        job_request = self.factory.post('/model_builder/add-object/Job/', data=post_data)
        self._add_session_to_request(job_request, service_request.session["system_data"])
        response = add_object(job_request, "Job")
        self.assertEqual(response.status_code, 200)
        new_job_id = next(iter(job_request.session["system_data"]["WebApplicationJob"].keys()))

        model_web = ModelWeb(job_request.session)
        job = model_web.get_web_object_from_efootprint_id(new_job_id)

        job_edition_structure, dynamic_form_data = generate_object_edition_structure(job)

        ref_job_edition_structure = {'fields': [{'id': 'implementation_details',
             'input_type': 'select',
             'name': 'implementation_details',
             'options': [{'label': 'aggregation-code-side',
                          'value': 'aggregation-code-side'},
                         {'label': 'default', 'value': 'default'},
                         {'label': 'mysql', 'value': 'mysql'},
                         {'label': 'no-index', 'value': 'no-index'},
                         {'label': 'no-pagination', 'value': 'no-pagination'},
                         {'label': 'orm-loop', 'value': 'orm-loop'}],
             'selected': "aggregation-code-side"},
            {'default': 150.0,
             'id': 'data_transferred',
             'input_type': 'input',
             'name': 'data_transferred',
             'unit': 'MB'},
            {'default': 100.0,
             'id': 'data_stored',
             'input_type': 'input',
             'name': 'data_stored',
             'unit': 'kB'}],
             'list_attributes': [],
             'modeling_obj_attributes': [
                 {'attr_name': 'service',
                  'attr_value': model_web.get_web_object_from_efootprint_id(service_id),
                  'existing_objects': [model_web.get_web_object_from_efootprint_id(service_id)],
        'object_type': 'WebApplication'}]
        }

        ref_dynamic_form_data = {'dynamic_lists': []}

        self.assertDictEqual(job_edition_structure, ref_job_edition_structure)
        self.assertDictEqual(dynamic_form_data, ref_dynamic_form_data)

    @patch("model_builder.edition.views_edition.render_exception_modal")
    def test_edit_genai_model(self, mock_render_exception_modal):
        gpu_server = GPUServer.from_defaults("GPU server", compute=SourceValue(16 * u.gpu), storage=Storage.ssd())
        first_provider = GenAIModel.list_values()["provider"][0]
        first_model_name = GenAIModel.conditional_list_values()[
            "model_name"]["conditional_list_values"][first_provider][0]
        genai_service = GenAIModel.from_defaults(
            "GenAI service", server=gpu_server, provider=first_provider, model_name=first_model_name)
        system = System("Test system", usage_patterns=[])
        logger.info(f"Created GenAI service with provider {first_provider} and model name {first_model_name}")

        post_data = QueryDict(mutable=True)
        second_provider = GenAIModel.list_values()["provider"][1]
        second_model_name = GenAIModel.conditional_list_values()[
            "model_name"]["conditional_list_values"][second_provider][0]
        post_data.update(
            {'name': ['Gen AI service'], 'server': [gpu_server.id],
             "provider": [second_provider], "model_name": [second_model_name]}
        )

        edit_service_request = self.factory.post(f'/edit-object/{genai_service.id}', data=post_data)
        self._add_session_to_request(
            edit_service_request,
            {
                "System": {system.id: system.to_json()},
                "GenAIModel": {genai_service.id: genai_service.to_json()},
                "GPUServer": {gpu_server.id: gpu_server.to_json()}})

        response = edit_object(edit_service_request, genai_service.id)
        mock_render_exception_modal.assert_not_called()

    @patch("model_builder.edition.views_edition.render_exception_modal")
    def test_edit_server_and_storage(self, mock_render_exception_modal):
        server_id = "uuid-Server-1"
        storage_id = "uuid-Default-SSD-storage-1"

        post_data = QueryDict(mutable=True)
        post_data.update(
            {'name': ['New server'], 'carbon_footprint_fabrication': ['60'], 'storage_form_data':
                [f'{{"storage_id":"{storage_id}", "name":"server 1 default ssd", "carbon_footprint_fabrication_per_storage_capacity":"160.0"}}']}
        )

        edit_server_request = self.factory.post(f'/edit-object/{server_id}', data=post_data)
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
