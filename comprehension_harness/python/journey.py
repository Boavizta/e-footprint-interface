"""A design journey declared in the browser test that walks it (``comprehension_harness/stack.md`` § 4).

    @journey("Start a modeling with AI", who="…", wants="…", now="2026-01-15T10:00:00Z")
    class TestStartAModelingWithAI:
        def test_describes_a_system(self, page):        # the first case is the reference run
            …
            screen(page, "description-panel", why="…")

``journey`` is a pytest marker on a test class. Around each of its cases this plugin installs the page's
recorder (``journey_page.js``) and, after it, writes one JSON under ``<docs>/design/journeys-generated/
<journey>/cases/``: the ordered screens and, before each, what led to it: the user's actions, the ``event``
calls they fired and the ``narrate`` steps the app crossed. ``comprehension_harness/journey-render.ts`` draws
the page from those files.

The app's ``narrate`` and ``event`` calls run in the server, so a journey runs against a server of the test
process (pytest-django's ``live_server``): this plugin stands in front of the run's collector and keeps the
calls a request crosses. Which action a call answers is said by the request itself: the page numbers its
actions in a cookie, ``jt_action``, and every request carries the number of the action before it. When a
request starts is the web framework's to say, so the project says it: from the framework's own hook it calls
``request_answers(<the request's Cookie header>)``, in the thread that answers the request.

A journey's folder is rewritten from nothing by the process that runs its cases, so the cases of a journey run
in one process: under pytest-xdist with several workers they are skipped, naming the journeys' command.

``screen(page, id, why=…)`` marks a screen at the moment it is reached. The id is the literal:
``<journey>#<id>`` is the screen's address. It captures the DOM as HTML (``captures/<case>/<nn>-<id>.html``,
the stylesheet shared under ``css/``), lists the screen's controls with the role and name the accessibility
tree gives each, and closes the segment of actions and calls that led here. Reaching an id a second time in
one case is a return: the capture is compared with the first and only kept when it differs.

``screen(…, planned={"feature": …, "mockup": …, "what": …})`` says a feature changes the screen: the mockup is
an edited copy of today's capture, as a path from the root, and the feature's spec page draws the two side by
side.

``@planned_case("<feature>", "<screen id>", "<title>")`` on a test of the class with an empty body declares a
case a feature will add at a screen: one criterion of its spec, as a title. A run skips it; the feature's spec
page lists it under the screen, and the plan counts it as a case to write. Written, it keeps its title with
``@titled("<title>")`` (``declare.py``).

``seeded(page)`` ends the fixture part of a case: what was recorded so far is not part of the journey.

``pause_clock(page)`` stops the page's timers; from there ``elapse(page, ms, why)`` is the only way its time
passes, and it is a cause of the journey.

A journey's page fixture is the project's: it opens its context with ``CONTEXT``, what a capture must not
vary with, and with the viewport the project draws its journeys at. The run writes down the viewport its
page has.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from comprehension_harness.python.collector import CONFIG_FILE, plain, title_of
from comprehension_harness.python.declare import has_empty_body

PAGE_SCRIPT = Path(__file__).with_name("journey_page.js")
# What a capture must not vary with, whatever the project. Its viewport is the project's to say, and the page's
# clock is pinned per journey, at its `now`.
CONTEXT = {"timezone_id": "UTC", "locale": "en-US", "color_scheme": "light", "reduced_motion": "reduce"}
# A frame of the page's faked clock, in its milliseconds.
FRAME_MS = 16
ADDRESS = re.compile(r"^[a-z][a-z0-9-]*$")
ACTION_COOKIE = re.compile(r"(?:^|; )jt_action=(\d+)")
STATE_ATTRS = re.compile(r' data-capture-(?:focus|scroll="[^"]*")')
SCROLL_ATTR = re.compile(r' data-capture-scroll="([^"]*)"')
ARIA_ENTRY = re.compile(r'^([a-z]+)(?: "((?:[^"\\]|\\.)*)")?')
STATUS = pytest.StashKey[str]()

# The request a server thread is answering: the number of the action before it, 0 before any.
_request = threading.local()
_runs: dict = {}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70]


def journey(name: str, *, who: str, wants: str, now: str):
    """Declares a journey on a test class: who walks it, what they want from it, and the instant (ISO) every
    case runs at. The cases are the class's tests, the first one the reference run."""
    return pytest.mark.journey(name, who=who, wants=wants, now=now)


def planned_case(feature: str, screen_id: str, title: str):
    """Declares, on a test of a journey with an empty body, a case ``feature`` will add at the screen
    ``screen_id``."""
    if not all(isinstance(name, str) and ADDRESS.match(name) for name in (feature, screen_id)):
        raise ValueError(f"@planned_case({feature!r}, {screen_id!r}, …) takes a feature folder's name, then a screen id")
    if not isinstance(title, str) or not title.strip():
        raise TypeError(f"@planned_case(…) takes the case's title, a string, not {title!r}")
    line = sys._getframe(1).f_lineno

    def declare(function):
        code = function.__code__
        if not has_empty_body(function):
            raise TypeError(f"{code.co_filename}:{code.co_firstlineno} — @planned_case stands on a test with an "
                            f"empty body; a written case carries its title with @titled(…)")
        case = pytest.mark.planned_case(feature, screen_id, title, line=line)
        return pytest.mark.skip(reason=f"planned: {feature} · {screen_id}: {title}")(case(function))

    return declare


def _path(url: str) -> str:
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")


def _digest(text: str, length: int) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:length]


class Run:
    """One case being walked."""

    def __init__(self, meta: dict, folder: Path, case_slug: str):
        self.journey = meta
        self.dir = folder
        self.case_slug = case_slug
        # What the page said, in order: actions, navigations, time let pass.
        self.log: list[dict] = []
        # What the server crossed, each call with the number of the action its request carried.
        self.hits: list[dict] = []
        self.lock = threading.Lock()
        self.screens: list[dict] = []
        self.html: list[str] = []
        self.clock_paused = False
        # A call crossed in a thread no request was announced in: where, for the error that says so.
        self.unannounced: str | None = None

    def check(self) -> None:
        if self.unannounced:
            raise RuntimeError(
                f"journey: {self.unannounced} was crossed in a thread that answers no request the journey was told "
                f"of, so the action it answers is unknown. The project calls request_answers(<Cookie header>) when "
                f"a request starts, from its web framework's hook (journey.py)")

    def drain(self, page) -> list[dict]:
        """What was recorded since the last drain, as causes: the opening, then one per action."""
        # The page's messages come in order: once these two answers are back, every action before them is in.
        page.evaluate("() => 0")
        page.evaluate("() => 0")
        entries, self.log = self.log, []
        with self.lock:
            hits, self.hits = self.hits, []
        causes: list[dict] = []
        by_action: dict[int, dict] = {}

        def cause(kind: str, url: str, **what) -> dict:
            causes.append({"kind": kind, "url": url, **what, "events": [], "steps": [], "navigations": [], "server": []})
            return causes[-1]

        current = None
        for entry in entries:
            if entry["kind"] == "nav":
                if current is None:
                    current = cause("open", _path(entry["url"]))
                else:
                    current["navigations"].append(_path(entry["url"]))
            elif entry["kind"] == "action":
                current = cause("action", entry["url"], type=entry["type"], key=entry["key"], control=entry["control"],
                                on={name: entry[name] for name in ("tag", "text", "title", "ariaLabel")})
                by_action[entry["seq"]] = current
            else:
                current = cause("time", entry["url"], elapsed={"ms": entry["ms"], "why": entry["why"]})
                by_action[entry["seq"]] = current
        for hit in hits:
            answered = by_action.get(hit["seq"])
            if answered is None:
                # A request no action of this segment sent: the page's own, as it opened.
                if not causes or causes[0]["kind"] != "open":
                    causes.insert(0, {"kind": "open", "url": _path(page.url), "events": [], "steps": [],
                                      "navigations": [], "server": []})
                answered = causes[0]
            if hit["kind"] == "event":
                answered["events"].append({"sentence": hit["sentence"], "site": hit["site"], "watch": hit["watch"]})
                continue
            same = next((step for step in answered["steps"] if step["site"]["file"] == hit["site"]["file"]
                         and step["site"]["line"] == hit["site"]["line"]), None)
            if same:
                same["count"] += 1
            else:
                answered["steps"].append({"sentence": hit["sentence"], "site": hit["site"], "count": 1})
        return causes


def _title(item) -> str:
    """A case's title without pytest's ``[case]``: the browser a case ran in is not part of what it tells."""
    return title_of(item).removesuffix(item.name[len(getattr(item, "originalname", None) or item.name):])


def _run_of(page) -> Run:
    if page not in _runs:
        raise RuntimeError("journey: screen() and its kin are called in a case of a @journey(…) class, on its page")
    return _runs[page]


def _first_aria_entry(snapshot: str) -> str | None:
    """The first entry of an aria snapshot, as written before YAML quoted it: an entry holding ``: `` is a
    quoted scalar, ``- 'button "Increase: the count"'``."""
    line = snapshot.strip().split("\n")[0]
    if not line.startswith("- "):
        return None
    entry = line[2:]
    if entry.startswith("'"):
        quoted = re.match(r"^'((?:[^']|'')*)'", entry)
        return quoted.group(1).replace("''", "'") if quoted else entry
    if entry.startswith('"'):
        quoted = re.match(r'^"((?:[^"\\]|\\.)*)"', entry)
        return json.loads(f'"{quoted.group(1)}"') if quoted else entry
    return entry


def _controls_of(page) -> list[dict]:
    controls = []
    for control in page.evaluate("() => window.__jtLib.listControls()"):
        role = name = None
        if not control["pointerOnly"]:
            try:
                snapshot = page.locator(f'[data-jt-c="{control["i"]}"]').aria_snapshot(timeout=2000)
            except Exception:  # Gone, or hidden from the tree: no control there.
                snapshot = ""
            entry = _first_aria_entry(snapshot)
            read = None if entry is None else ARIA_ENTRY.match(entry)
            # An empty snapshot is an element the tree does not hold. One that is there and cannot be read is a gap here.
            if snapshot.strip() and not read:
                raise RuntimeError(f'journey: cannot read the role of control {control["i"]} (<{control["tag"]}> '
                                   f'"{control["text"]}") from its aria snapshot: {snapshot.strip().splitlines()[0]}')
            if read:
                role = read.group(1)
                name = None if read.group(2) is None else re.sub(r"\\(.)", r"\1", read.group(2))
        controls.append({**control, "role": role, "name": name})
    page.evaluate("() => window.__jtLib.clearControlStamps()")
    return controls


def _state_of(html: str, what: str) -> str:
    """Where the focus sits (``focus``) or what is scrolled (``scroll``), as a comparable string."""
    found = []
    for index, line in enumerate(html.split("\n")):
        if what == "focus" and " data-capture-focus" in line:
            found.append(str(index))
        elif what == "scroll" and (scrolled := SCROLL_ATTR.search(line)):
            found.append(f"{index}:{scrolled.group(1)}")
    return " ".join(found)


def screen(page, id: str, *, why: str, planned: dict | None = None) -> None:
    """Marks a screen of the journey at the moment the case reaches it. Wait for what makes it reached first."""
    run = _run_of(page)
    if not ADDRESS.match(id):
        raise ValueError(f'journey: screen id "{id}" must be kebab-case: it is an address')
    if planned is not None and (not isinstance(planned, dict) or set(planned) != {"feature", "mockup", "what"}
                                or not all(isinstance(value, str) for value in planned.values())):
        raise ValueError(f'journey: screen "{id}" is planned with {{"feature": <its folder\'s name>, "mockup": '
                         f'<the edited capture, from the root>, "what": <what changes>}}')
    before = run.drain(page)
    run.check()
    controls = _controls_of(page)
    running = page.evaluate("() => window.__jtLib.settlePage()")
    # The page's frames are on its clock: paused, they come only when the clock is run.
    if run.clock_paused:
        page.clock.run_for(2 * FRAME_MS)
    else:
        page.evaluate("() => window.__jtLib.twoFrames()")
    captured = page.evaluate("args => window.__jtLib.capturePage(args)", {
        "address": f'{run.journey["slug"]}#{id}', "title": f'{run.journey["name"]} · {id}', "runningAnimations": running})

    css_file = f'css/app-{_digest(captured["css"], 12)}.css'
    if not (run.dir / css_file).exists():
        (run.dir / "css").mkdir(parents=True, exist_ok=True)
        (run.dir / css_file).write_text(captured["css"])
    index = len(run.screens)
    file = f"captures/{run.case_slug}/{index + 1:02d}-{id}.html"
    html = captured["html"].replace("__JOURNEY_CSS__", f"../../{css_file}")

    # A return is judged on the DOM. Where the focus sits and how far a box is scrolled are state the capture
    # writes down as attributes; they are compared apart, so "the same screen, scrolled" is not another screen.
    first_visit = next((i for i, earlier in enumerate(run.screens) if earlier["id"] == id), None)
    identical = moved = None
    if first_visit is not None:
        first = run.html[first_visit]
        identical = STATE_ATTRS.sub("", first) == STATE_ATTRS.sub("", html)
        moved = {what: _state_of(first, what) != _state_of(html, what) for what in ("focus", "scroll")}
    if identical is not True:
        (run.dir / file).parent.mkdir(parents=True, exist_ok=True)
        (run.dir / file).write_text(html)
    run.html.append(html)
    run.screens.append({
        "id": id, "why": why, "url": captured["url"], **({"planned": planned} if planned else {}),
        "capture": None if identical is True else file, "css": css_file, "sha": _digest(html, 16),
        "bytes": len(html.encode()), "counts": captured["counts"], "returnsTo": first_visit,
        "identicalToFirstVisit": identical, "movedSinceFirstVisit": moved, "controls": controls, "before": before,
    })

    # Opt-in evidence for the capture's fidelity: the live screen and the capture opened alone, as images.
    if os.environ.get("JOURNEY_SHOTS") and identical is not True:
        shots = run.dir / "shots" / run.case_slug
        shots.mkdir(parents=True, exist_ok=True)
        base = shots / f"{index + 1:02d}-{id}"
        page.screenshot(path=f"{base}.live.png", animations="disabled", caret="hide")
        viewer = page.context.new_page()
        viewer.goto((run.dir / file).as_uri())
        # Scroll offsets are attributes in a capture; nothing in it applies them (it carries no script).
        viewer.evaluate("""() => {
            for (const el of document.querySelectorAll('[data-capture-scroll]')) {
                const [top, left] = el.getAttribute('data-capture-scroll').split(',').map(Number);
                el.scrollTop = top; el.scrollLeft = left;
            }
        }""")
        viewer.screenshot(path=f"{base}.capture.png", animations="disabled")
        viewer.close()


def seeded(page) -> None:
    """Ends the fixture part of a case: nothing recorded so far belongs to the journey."""
    _run_of(page).drain(page)


def pause_clock(page) -> None:
    """Stops the page's timers at the journey's instant. From here its time passes only through ``elapse``."""
    run = _run_of(page)
    page.clock.pause_at(run.journey["now"])
    run.clock_paused = True


def elapse(page, ms: int, why: str) -> None:
    """Lets ``ms`` of the page's time pass on a paused clock. ``why`` says what that wait is to the user; it
    is a cause of the journey."""
    run = _run_of(page)
    if not run.clock_paused:
        raise RuntimeError("journey: elapse() needs pause_clock() first: on a running clock the time has "
                           "already passed by itself")
    # What the page sends from here on answers this wait, and what it said so far is before it.
    seq = page.evaluate("() => window.__jt.next()")
    run.log.append({"kind": "time", "seq": seq, "ms": ms, "why": why, "url": _path(page.url)})
    page.clock.run_for(ms)


def request_answers(cookie: str | None) -> None:
    """Says that this thread starts answering a request, and gives its ``Cookie`` header: the calls the thread
    crosses from here on answer the action the request carries. The project calls it from its web framework's
    hook for the start of a request."""
    found = ACTION_COOKIE.search(cookie or "")
    _request.action = int(found.group(1)) if found else 0


class Journeys:
    def __init__(self, config):
        self.recorder = config.pluginmanager.get_plugin("narrate-collector")
        settings = json.loads((self.recorder.root / CONFIG_FILE).read_text())
        self.out = self.recorder.root / settings["docs"] / "design" / "journeys-generated"
        # In front of the run's collector: a call a request crosses is the story's and the journey's.
        self.recorder.calls.install_collector(self.collect)
        self.started: set[str] = set()
        # The cases to write, by journey.
        self.todos: dict[str, list[dict]] = {}
        self.is_parallel = getattr(config, "workerinput", {}).get("workercount", 1) > 1
        self.command = " ".join(settings["commands"]["journeys"])

    def pytest_collection_modifyitems(self, items):
        for item in items:
            declared, case = item.get_closest_marker("journey"), item.get_closest_marker("planned_case")
            if case:
                if declared is None:
                    raise pytest.UsageError(f"{item.location[0]}:{case.kwargs['line']} — @planned_case stands on "
                                            f"a test of a @journey(…) class")
                todo = dict(zip(("feature", "screen", "title"), case.args), line=case.kwargs["line"])
                todos = self.todos.setdefault(slug(declared.args[0]), [])
                # A case collected once a browser is one case.
                if todo not in todos:
                    todos.append(todo)
            elif declared and self.is_parallel:
                item.add_marker(pytest.mark.skip(reason=f"a journey's cases run in one process, which rewrites "
                                                        f"its folder: {self.command}"))

    def collect(self, kind, sentence, watch, frame, planned_as) -> None:
        self.recorder.collect(kind, sentence, watch, frame, planned_as)
        # In the test's own thread a call is nobody's action: the case called the code itself.
        if kind not in ("step", "event") or not _runs or threading.current_thread() is threading.main_thread():
            return
        action = getattr(_request, "action", None)
        file = self.recorder.relative(frame.f_code.co_filename)
        if action is None:
            for run in list(_runs.values()):
                run.unannounced = run.unannounced or f"{file}:{frame.f_lineno}"
            return
        site = self.recorder.frame(frame, file)
        value = None
        # The watch is read for causes only: a step's watch is the narrative page's subject.
        if kind == "event" and watch is not None:
            try:
                value = plain(watch())
            except Exception as error:
                value = {"error": f"{type(error).__name__}: {error}"}
        hit = {"seq": action, "kind": kind, "sentence": sentence, "watch": value,
               "site": {"file": file, "line": site["line"], "fn": site["fn"]}}
        for run in list(_runs.values()):
            with run.lock:
                run.hits.append(hit)

    def attach(self, page, item, marker) -> Run:
        name = marker.args[0]
        if page.viewport_size is None:
            raise pytest.UsageError(f'journey "{name}": its page has no fixed viewport, and a capture is drawn at '
                                    f'one: the page fixture opens its context with viewport={{"width": …, "height": …}}')
        meta = {"name": name, "slug": slug(name), **marker.kwargs, "viewport": page.viewport_size,
                "file": Path(str(item.path)).resolve().relative_to(self.recorder.root).as_posix(),
                "todos": sorted(self.todos.get(slug(name), []), key=lambda todo: todo["line"])}
        folder = self.out / meta["slug"]
        if meta["slug"] not in self.started:
            self.started.add(meta["slug"])
            # A stale case or capture would be rendered as if this run had written it.
            for stale in ("cases", "captures", "shots"):
                shutil.rmtree(folder / stale, ignore_errors=True)
            folder.mkdir(parents=True, exist_ok=True)
            # The stylesheet folder is content-addressed and survives; the journey's own record does not.
            (folder / "journey.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        run = Run(meta, folder, slug(_title(item)))
        _runs[page] = run
        page.clock.set_fixed_time(meta["now"])
        page.expose_binding("__jtEmit", lambda source, entries: run.log.extend(entries))
        page.add_init_script(path=PAGE_SCRIPT)
        page.on("framenavigated",
                lambda frame: run.log.append({"kind": "nav", "url": frame.url}) if frame == page.main_frame else None)
        return run

    def detach(self, page, run: Run, item) -> None:
        try:
            after = run.drain(page)
        except Exception:  # A case that failed may have left no page to ask.
            after = []
        del _runs[page]
        line = item.location[1] + 1
        record = {"journey": run.journey, "title": _title(item), "slug": run.case_slug, "line": line,
                  "status": item.stash.get(STATUS, None), "narrate": "installed", "screens": run.screens,
                  "after": [cause for cause in after if cause["kind"] == "action"]}
        (run.dir / "cases").mkdir(parents=True, exist_ok=True)
        (run.dir / "cases" / f"{line:04d}-{run.case_slug}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        run.check()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            item.stash[STATUS] = report.outcome


@pytest.fixture(autouse=True)
def _journey_case(request):
    marker = request.node.get_closest_marker("journey")
    if marker is None:
        yield
        return
    journeys = request.config.pluginmanager.get_plugin("journeys")
    page = request.getfixturevalue("page")
    run = journeys.attach(page, request.node, marker)
    yield
    journeys.detach(page, run, request.node)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    config.addinivalue_line("markers", "journey(name, who, wants, now): the test class walks a design journey (journey.py)")
    config.addinivalue_line("markers", "planned_case(feature, screen, title): a case to write in a journey (journey.py)")
    config.pluginmanager.register(Journeys(config), "journeys")
