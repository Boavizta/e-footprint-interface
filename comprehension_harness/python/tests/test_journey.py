"""The journey helper of the Python stack: what `journey.py` writes for a browser test that walks screens.

A small project, a WSGI app served by a thread of its test process, is run by its own pytest process, as a
journey run is, and its journey folder is read back.
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

from comprehension_harness.python.tests.conftest import REFERENCE_CALLS, ROOT

pytest.importorskip("playwright", reason="a project that has no browser test draws no journey")

SITE = '''
    from shop.narrate import event, narrate

    PAGE = b"""<!doctype html><html><head><title>Basket</title><style>button { color: rgb(1, 2, 3); }</style></head>
    <body><h1>Basket</h1><p id="count">0</p>
    <button id="add" onclick="fetch('/add').then(r => r.text()).then(t => { document.getElementById('count').textContent = t })">Add: one article</button>
    <input id="note" value="">
    <div id="tall" style="height: 100px; overflow: auto"><p style="height: 400px">Terms</p></div>
    </body></html>"""
    articles = []


    def app(environ, start_response):
        if environ["PATH_INFO"] == "/add":
            event("The customer adds an article.", lambda: {"before": len(articles)})
            add()
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [str(len(articles)).encode()]
        if environ["PATH_INFO"] != "/":
            start_response("404 Not Found", [])
            return [b""]
        opened()
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [PAGE]


    def opened():
        narrate("The basket **opens empty**.")
        articles.clear()


    def add():
        for _ in range(2):
            narrate("The basket **counts one more**.")
        articles.append("article")
'''
CONFTEST = '''
    import threading
    from wsgiref.simple_server import WSGIRequestHandler, make_server

    import pytest
    from playwright.sync_api import sync_playwright

    from comprehension_harness.python.journey import CONTEXT, request_answers
    from shop.site import app

    pytest_plugins = ["comprehension_harness.python.collector", "comprehension_harness.python.journey"]


    class Quiet(WSGIRequestHandler):
        def log_message(self, *arguments):
            pass


    def announced(environ, start_response):
        ANNOUNCE
        return app(environ, start_response)


    @pytest.fixture(scope="session")
    def site():
        server = make_server("127.0.0.1", 0, announced, handler_class=Quiet)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{server.server_port}"
        server.shutdown()


    @pytest.fixture
    def page():
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            yield browser.new_context(**CONTEXT).new_page()
            browser.close()
'''
JOURNEY = '''
    from playwright.sync_api import expect

    from comprehension_harness.python.declare import titled
    from comprehension_harness.python.journey import journey, planned_case, screen, seeded

    FEATURE = "gift-cards"


    @journey("Fill a basket", who="A customer", wants="Their articles in the basket", now="2026-01-15T10:00:00Z")
    class TestFillABasket:
        @titled("adds an article")
        def test_adds_an_article(self, page, site):
            page.goto(f"{site}/")
            screen(page, "basket", why="The basket opens empty.")

            page.locator("#add").click()
            expect(page.locator("#count")).to_have_text("1")
            screen(page, "basket", why="The article is counted.")

            page.locator("#note").fill("for a friend")
            page.locator("#tall").evaluate("box => { box.scrollTop = 30 }")
            screen(page, "basket", why="A note is typed, the terms scrolled.")
            screen(page, "basket", why="Nothing happened since.")

        def test_looks_only(self, page, site):
            page.goto(f"{site}/")
            page.locator("#add").click()
            expect(page.locator("#count")).to_have_text("1")
            seeded(page)
            screen(page, "basket", why="What came before was the seed.")
            page.locator("#add").click()
            expect(page.locator("#count")).to_have_text("2")

        @planned_case(FEATURE, "basket", "a gift card shows its balance")
        def test_gift_card(self):
            """To write."""
'''
PROJECT = {
    "comprehension.config.json": json.dumps({"cache": "cache", "docs": "docs", "stack": {"calls": "shop.narrate"},
                                             "commands": {"journeys": ["pytest", "checks"]}}),
    "shop/narrate.py": REFERENCE_CALLS.read_text(),
    "pytest.ini": "[pytest]\n",
    "shop/site.py": SITE,
    "conftest.py": CONFTEST.replace("ANNOUNCE", 'request_answers(environ.get("HTTP_COOKIE"))'),
    "checks/test_basket.py": JOURNEY,
}
FOLDER = "docs/design/journeys-generated/fill-a-basket"


def run_journeys(root, *options) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONPATH": str(ROOT)}
    command = [sys.executable, "-m", "pytest", "checks", "-q", "-p", "no:django", "-p", "no:cacheprovider", "-rs",
               *options]
    return subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True)


def cases_of(root) -> list[dict]:
    return [json.loads(file.read_text()) for file in sorted((root / FOLDER / "cases").iterdir())]


@pytest.fixture(scope="module")
def walked(tmp_path_factory):
    """The project, run once."""
    root = tmp_path_factory.mktemp("shop")
    for file, text in PROJECT.items():
        (root / file).parent.mkdir(parents=True, exist_ok=True)
        (root / file).write_text(textwrap.dedent(text).lstrip("\n"))
    done = run_journeys(root)
    assert done.returncode == 0 and "2 passed, 1 skipped" in done.stdout, done.stdout + done.stderr
    return root


def test_a_journey_is_its_declaration_and_a_case_a_file_named_by_its_line(walked):
    declared = json.loads((walked / FOLDER / "journey.json").read_text())

    assert declared == {
        "name": "Fill a basket", "slug": "fill-a-basket", "who": "A customer", "wants": "Their articles in the basket",
        "now": "2026-01-15T10:00:00Z", "viewport": {"width": 1280, "height": 800}, "file": "checks/test_basket.py",
        "todos": [{"feature": "gift-cards", "screen": "basket", "title": "a gift card shows its balance", "line": 34}]}
    assert [file.name for file in sorted((walked / FOLDER / "cases").iterdir())] == [
        "0011-adds-an-article.json", "0025-test-looks-only.json"]
    first, second = cases_of(walked)
    assert (first["title"], first["line"], first["status"], first["journey"]) == ("adds an article", 11, "passed", declared)
    assert second["title"] == "test_looks_only"


def test_a_call_the_server_crossed_is_filed_under_the_action_that_sent_its_request(walked):
    opened, added, *_ = cases_of(walked)[0]["screens"]

    [opening] = opened["before"]
    assert (opening["kind"], opening["url"], opening["events"]) == ("open", "/", [])
    assert opening["steps"] == [{"sentence": "The basket **opens empty**.", "count": 1,
                                 "site": {"file": "shop/site.py", "line": 27, "fn": "opened"}}]
    [click] = added["before"]
    assert (click["kind"], click["type"], click["url"]) == ("action", "click", "/")
    # The action names the control it landed on, as the screen before it listed it.
    button = opened["controls"][click["control"]]
    assert (button["tag"], button["role"], button["name"]) == ("button", "button", "Add: one article")
    assert click["events"] == [{"sentence": "The customer adds an article.", "watch": {"before": 0},
                                "site": {"file": "shop/site.py", "line": 14, "fn": "app"}}]
    # A step crossed twice is one step, counted.
    assert click["steps"] == [{"sentence": "The basket **counts one more**.", "count": 2,
                               "site": {"file": "shop/site.py", "line": 33, "fn": "add"}}]


def test_a_screen_is_captured_one_tag_a_line_with_its_stylesheet_apart(walked):
    opened = cases_of(walked)[0]["screens"][0]
    capture = (walked / FOLDER / opened["capture"]).read_text()

    assert opened["capture"] == "captures/adds-an-article/01-basket.html"
    assert '<html data-journey-screen="fill-a-basket#basket"\n>' in capture
    assert '<p id="count"\n>0</p\n>' in capture and "<script" not in capture and "<style" not in capture
    assert f'<link rel="stylesheet" href="../../{opened["css"]}"\n>' in capture
    assert "button { color: rgb(1, 2, 3); }" in (walked / FOLDER / opened["css"]).read_text()
    assert opened["counts"]["elements"] == capture.count("\n><") + 1 - capture.count("\n></")


def test_a_return_is_compared_with_the_first_visit_and_kept_only_when_it_differs(walked):
    opened, added, moved, same = cases_of(walked)[0]["screens"]

    assert (opened["returnsTo"], opened["identicalToFirstVisit"], opened["movedSinceFirstVisit"]) == (None, None, None)
    assert (added["returnsTo"], added["identicalToFirstVisit"]) == (0, False)
    assert added["capture"] == "captures/adds-an-article/02-basket.html"
    # What a field holds is the DOM's; where the focus sits and how far a box is scrolled are told apart.
    capture = (walked / FOLDER / moved["capture"]).read_text()
    assert 'value="for a friend" data-capture-focus' in capture and 'data-capture-scroll="30,0"' in capture
    assert moved["movedSinceFirstVisit"] == {"focus": True, "scroll": True}
    assert (same["returnsTo"], same["identicalToFirstVisit"], same["capture"]) == (0, False, "captures/adds-an-article/04-basket.html")


def test_what_came_before_seeded_is_not_the_journey_and_what_follows_the_last_screen_is_kept(walked):
    case = cases_of(walked)[1]

    [only] = case["screens"]
    assert only["before"] == []
    [click] = case["after"]
    assert (click["kind"], click["on"]["text"]) == ("action", "Add: one article")


def test_two_runs_of_an_unchanged_project_write_the_same_captures(walked):
    before = [screen["sha"] for case in cases_of(walked) for screen in case["screens"]]
    (walked / FOLDER / "cases" / "9999-stale.json").write_text("{}")

    assert run_journeys(walked).returncode == 0

    assert [screen["sha"] for case in cases_of(walked) for screen in case["screens"]] == before
    assert len(cases_of(walked)) == 2


def test_the_cases_of_a_parallel_run_are_skipped_and_the_folder_left_as_it_was(walked):
    pytest.importorskip("xdist", reason="a project that does not run its tests in parallel has no such run")
    before = cases_of(walked)

    done = run_journeys(walked, "-n", "2")

    assert done.returncode == 0 and "3 skipped" in done.stdout, done.stdout + done.stderr
    assert "a journey's cases run in one process, which rewrites its folder: pytest checks" in done.stdout
    assert cases_of(walked) == before


def test_a_server_that_does_not_announce_its_requests_fails_the_case_saying_so(project):
    root = project({**PROJECT, "conftest.py": CONFTEST.replace("ANNOUNCE", "pass")})

    done = run_journeys(root)

    assert done.returncode == 1
    assert ("journey: shop/site.py:27 was crossed in a thread that answers no request the journey was told of"
            in done.stdout)


@pytest.mark.parametrize("declaration, said", [
    ('@journey("A", who="a", wants="b", now="2026-01-15T10:00:00Z")\nclass TestA:\n    def test_x(self, page, site):\n'
     '        screen(page, "Basket", why="…")\n', 'screen id "Basket" must be kebab-case'),
    ('@journey("A", who="a", wants="b", now="2026-01-15T10:00:00Z")\nclass TestA:\n    def test_x(self, page, site):\n'
     '        page.goto(site)\n        screen(page, "a", why="…", planned={"feature": "f"})\n',
     'screen "a" is planned with {"feature"'),
    ('def test_x(page):\n    screen(page, "basket", why="…")\n', "are called in a case of a @journey(…) class"),
    ('@planned_case("gift-cards", "basket", "a title")\ndef test_x():\n    pass\n',
     "checks/test_bad.py:4 — @planned_case stands on a test of a @journey(…) class"),
    ('@planned_case("gift-cards", "basket", "a title")\ndef test_x():\n    assert True\n',
     "checks/test_bad.py:4 — @planned_case stands on a test with an empty body"),
    ('@planned_case("Gift cards", "basket", "a title")\ndef test_x():\n    pass\n',
     "takes a feature folder's name, then a screen id"),
])
def test_a_declaration_or_a_call_that_does_not_have_the_shape_fails_the_run(project, declaration, said):
    imports = "from comprehension_harness.python.journey import journey, planned_case, screen\n\n\n"
    root = project({**PROJECT, "checks/test_basket.py": "", "checks/test_bad.py": imports + declaration})

    done = run_journeys(root)

    assert done.returncode != 0 and said in done.stdout + done.stderr, done.stdout + done.stderr
