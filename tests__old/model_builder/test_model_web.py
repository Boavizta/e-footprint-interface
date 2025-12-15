import os

from django.http import QueryDict
from efootprint.logger import logger

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.views_addition import add_object
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests__old import root_test_dir
from tests__old.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestModelWeb(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_get_efootprint_objects_from_efootprint_type(self):
        logger.info(f"Creating service")
        os.environ["RAISE_EXCEPTIONS"] = "True"
        post_data = QueryDict(mutable=True)
        post_data.update({'WebApplication_name': ['New service'],
                            'efootprint_id_of_parent_to_link_to': ['uuid-Server-1'],
                          'type_object_available': ['WebApplication'],
                          'WebApplication_technology': ['php-symfony']}
                         )

        service_request = self.factory.post('/add-object/Service', data=post_data)
        self._add_session_to_request(service_request, self.system_data)
        response = add_object(service_request, 'Service')
        service_id = next(iter(service_request.session["system_data"]["WebApplication"].keys()))
        self.assertEqual(response.status_code, 200)

        logger.info(f"Creating job")
        post_data = QueryDict(mutable=True)
        post_data.update(
            {'WebApplicationJob_name': ['New job'],
                'efootprint_id_of_parent_to_link_to': ['uuid-20-min-streaming-on-Youtube'],
             'WebApplicationJob_service': [service_id],
             'type_object_available': ['WebApplicationJob'],
             'WebApplicationJob_implementation_details': ['aggregation-code-side'],
             'WebApplicationJob_data_transferred': ['150'], 'WebApplicationJob_data_stored': ['100'],
             'WebApplicationJob_data_transferred_unit': ['MB'], 'WebApplicationJob_data_stored_unit': ['MB']}
        )

        job_request = self.factory.post('/model_builder/add-object/Job', data=post_data)
        self._add_session_to_request(job_request, service_request.session["system_data"])
        response = add_object(job_request, "Job")
        self.assertEqual(response.status_code, 200)
        new_job_id = next(iter(job_request.session["system_data"]["WebApplicationJob"].keys()))

        model_web = ModelWeb(SessionSystemRepository(job_request.session))
        all_jobs = model_web.get_efootprint_objects_from_efootprint_type("JobBase")
