import json

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory

class TestModelingBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = None

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.factory = RequestFactory()

        # Load system data
        with open(self.system_data_path, "r") as f:
            self.system_data = json.load(f)

    @staticmethod
    def _add_session_to_request(request, system_data):
        """Attach a session to the request object using Django's session middleware."""
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session["system_data"] = system_data
        request.session.save()
