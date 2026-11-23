"""A journey runs against a server of the test process, so that the run sees the calls each request crosses."""
import random
import uuid

import pytest
from django.core.signals import request_started

from comprehension_harness.python.journey import CONTEXT, request_answers
from tests.e2e.utils import in_process_page

pytestmark = [pytest.mark.e2e]


@pytest.fixture
def page(transactional_db, browser_name, browser_type_launch_args):
    with in_process_page(browser_name, browser_type_launch_args, **CONTEXT) as page:
        yield page


@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server.url


@pytest.fixture(scope="session", autouse=True)
def requests_announced():
    """Django says when a request starts, in the thread that answers it: the journey is told, with its cookies."""
    def announce(sender, environ, **_):
        request_answers(environ.get("HTTP_COOKIE"))

    request_started.connect(announce, weak=False)
    yield
    request_started.disconnect(announce)


@pytest.fixture(autouse=True)
def pinned_server(monkeypatch):
    """What the server draws at random would make two runs of an unchanged app differ: the ids of the objects it
    creates, and the CSRF token it writes on the page."""
    drawn = random.Random(0)
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(int=drawn.getrandbits(128), version=4))
    monkeypatch.setattr("django.middleware.csrf._get_new_csrf_string", lambda: "a" * 32)
