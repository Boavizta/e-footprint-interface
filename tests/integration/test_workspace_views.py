"""View-layer integration tests for the two-model workspace endpoints.

Exercises switch / add / remove through real Django views + session, plus the two correctness
invariants the feature hinges on:
  - no DOM id collides across the two resident canvases (the headline risk), and
  - a mutation on the active model targets the active canvas's OOB region, never the parked one.

RAISE_EXCEPTIONS=1 so a crashing view surfaces as a non-200 instead of being absorbed into a modal.
"""
import json
from collections import Counter
from html.parser import HTMLParser

import pytest
from efootprint.api_utils.system_to_json import system_to_json

from model_builder.adapters.repositories import SessionSystemRepository, SessionWorkspaceRepository
from model_builder.domain.services import ProgressiveImportService
from model_builder.adapters.repositories.workspace_base import system_id_of


@pytest.fixture(autouse=True)
def raise_view_exceptions(monkeypatch):
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")


def _seed_active_slot(client, system) -> None:
    """Persist a built System into the active slot of the client's session (with-calc, recomputed)."""
    raw = system_to_json(system, save_calculated_attributes=False)
    import_service = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
    with_calc = import_service.import_system(SessionSystemRepository.upgrade_system_data(raw))
    session = client.session
    SessionWorkspaceRepository(session).active_repository().save_data(with_calc)
    session.save()


class _CanvasIdCollector(HTMLParser):
    """Collect element ids found inside each ``#model-canva-{slot}`` subtree.

    Scopes the no-duplicate-id assertion to the two resident canvases (the feature's headline risk),
    not the whole page — pre-existing shared chrome (e.g. two modals extending one modal template)
    legitimately repeats ids outside the canvases and is out of scope here.
    """

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.canvas_stack = []  # (slot, depth_when_opened)
        self.ids_per_canvas = {}

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag not in self.VOID_TAGS:
            self.depth += 1
            canvas_slot = attr.get("data-model-canvas")
            if canvas_slot is not None:
                self.canvas_stack.append((canvas_slot, self.depth))
                self.ids_per_canvas.setdefault(canvas_slot, [])
        if self.canvas_stack and attr.get("id"):
            self.ids_per_canvas[self.canvas_stack[-1][0]].append(attr["id"])

    def handle_endtag(self, tag):
        if tag in self.VOID_TAGS:
            return
        if self.canvas_stack and self.depth == self.canvas_stack[-1][1]:
            self.canvas_stack.pop()
        self.depth -= 1


def _canvas_ids_per_slot(html: str) -> dict:
    collector = _CanvasIdCollector()
    collector.feed(html)
    return collector.ids_per_canvas


@pytest.mark.django_db
def test_add_duplicate_creates_second_slot_with_distinct_system_id(client, minimal_system):
    _seed_active_slot(client, minimal_system)
    original_id = system_id_of(SessionWorkspaceRepository(client.session).repository_for(0).get_system_data())

    response = client.post("/model_builder/add-model/", {"source": "duplicate"})
    assert response.status_code == 200

    workspace = SessionWorkspaceRepository(client.session)
    assert workspace.list_slots() == [0, 1]
    assert workspace.active_slot() == 1  # the new model becomes active
    duplicated_id = system_id_of(workspace.repository_for(1).get_system_data())
    assert duplicated_id != original_id  # distinct system id (web_id prefix invariant)
    assert "Copy of" in workspace.repository_for(1).get_system_data()["System"][duplicated_id]["name"]


@pytest.mark.django_db
def test_add_blank_creates_second_slot(client, minimal_system):
    _seed_active_slot(client, minimal_system)
    response = client.post("/model_builder/add-model/", {"source": "blank"})
    assert response.status_code == 200
    assert SessionWorkspaceRepository(client.session).list_slots() == [0, 1]


@pytest.mark.django_db
def test_add_model_error_surfaces_oob_modal_without_wiping_the_builder(client, minimal_system, monkeypatch):
    """A failing add-model returns the OOB exception modal with ``HX-Reswap: none`` so the modal
    overlays the (untouched) builder instead of the empty response body wiping #main-content-block.

    Guards the @render_exception_modal_if_error path for full-builder-target views (add/remove),
    which the decorator only serves correctly because of the HX-Reswap: none header. The autouse
    fixture forces RAISE_EXCEPTIONS=1 (errors bubble); unset it so the decorator renders the modal.
    """
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    _seed_active_slot(client, minimal_system)

    # source=import with no uploaded file raises ValueError("Invalid file format ...") in the view.
    response = client.post("/model_builder/add-model/", {"source": "import"})
    body = response.content.decode()

    assert response.status_code == 200
    assert response["HX-Reswap"] == "none"                       # the main swap is suppressed...
    assert 'id="modal-container"' in body and "hx-swap-oob" in body  # ...so the modal lands OOB
    assert 'id="model-builder-modal"' in body
    assert "Invalid file format" in body                         # the exception message reaches the modal
    assert "openModalDialog" in response["HX-Trigger-After-Settle"]
    # Canvas-wipe guard: the builder is NOT re-rendered, so no canvas markup is in the response body...
    assert "data-model-canvas" not in body
    # ...and the workspace is untouched (still a single slot, nothing half-added).
    assert SessionWorkspaceRepository(client.session).list_slots() == [0]


@pytest.mark.django_db
def test_no_dom_id_collides_across_two_resident_canvases(client, minimal_system):
    """The headline correctness risk: both canvases render in one document, so a duplicated structural
    or object-card id would silently break HTMX/leaderlines. The add response renders both canvases."""
    _seed_active_slot(client, minimal_system)
    response = client.post("/model_builder/add-model/", {"source": "duplicate"})
    assert response.status_code == 200

    ids_per_slot = _canvas_ids_per_slot(response.content.decode())
    assert set(ids_per_slot) == {"0", "1"}, "expected exactly two resident canvases"

    for slot, ids in ids_per_slot.items():
        within = {element_id: count for element_id, count in Counter(ids).items() if count > 1}
        assert within == {}, f"canvas {slot} repeats ids within itself: {within}"

    shared = set(ids_per_slot["0"]) & set(ids_per_slot["1"])
    assert shared == set(), f"ids collide across the two resident canvases: {sorted(shared)}"


@pytest.mark.django_db
def test_switch_model_flips_active_slot_and_emits_canvas_toggle(client, minimal_system):
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # active is now slot 1
    assert SessionWorkspaceRepository(client.session).active_slot() == 1

    # Every switch lands on the resident builder (the comparison view is dismissed client-side first),
    # so the switch always rebinds the shared chrome via OOB (so the visible canvas's chrome updates).
    response = client.post("/model_builder/switch-model/", {"slot": "0"})
    assert response.status_code == 200
    assert SessionWorkspaceRepository(client.session).active_slot() == 0  # persisted for refresh
    assert json.loads(response["HX-Trigger"]) == {"switchModelCanvas": {"slot": 0}}
    assert b"hx-swap-oob" in response.content and b"system-name" in response.content

    # The reverse switch behaves identically — there is no chrome-less switch path anymore.
    response = client.post("/model_builder/switch-model/", {"slot": "1"})
    assert response.status_code == 200
    assert SessionWorkspaceRepository(client.session).active_slot() == 1
    assert json.loads(response["HX-Trigger"]) == {"switchModelCanvas": {"slot": 1}}
    assert b"hx-swap-oob" in response.content and b"system-name" in response.content


@pytest.mark.django_db
def test_remove_model_returns_to_single_model(client, minimal_system):
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    assert SessionWorkspaceRepository(client.session).list_slots() == [0, 1]

    response = client.post("/model_builder/remove-model/", {"slot": "1"})
    assert response.status_code == 200
    workspace = SessionWorkspaceRepository(client.session)
    assert workspace.list_slots() == [0]
    assert workspace.active_slot() == 0


@pytest.mark.django_db
def test_mutation_on_active_model_targets_the_active_canvas(client, minimal_system):
    """A constraint-flip mutation emits the model_canvas OOB region; with two slots it must target the
    ACTIVE slot's #model-canva-{slot}, never the parked one (HTMX OOB is first-match-by-id)."""
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.adapters.presenters.oob_regions import _render_model_canvas

    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # active is slot 1

    workspace = SessionWorkspaceRepository(client.session)
    active_model = ModelWeb(workspace.active_repository())
    oob_html = _render_model_canvas(active_model, {})
    assert "innerHTML:#model-canva-1" in oob_html
    assert "#model-canva-0" not in oob_html


@pytest.mark.django_db
def test_compare_renders_dashboard_with_both_models_and_headline_delta(client, minimal_system):
    """With two models, /compare/ renders the comparison dashboard: both model cards, the headline Δ card,
    and the decomposition. The endpoint runs the real System.compare_to through ComparisonService.

    Compare is a pure HX fragment (plain render, never htmx_render), so it returns the same standalone
    dashboard fragment whether or not the HX-Request header is present — no full-page base.html branch.
    """
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 = "Copy of Test System"

    response = client.get("/model_builder/compare/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    html = response.content.decode()
    assert "comparison-dashboard" in html
    assert "Test System" in html and "Copy of Test System" in html
    assert "What explains the difference" in html
    assert "What differs between the models" in html
    # Chart payloads are emitted for the JS to draw (shared-scale paired bars + cumulative overlay).
    assert "data-paired-chart" in html and "data-cumulative-chart" in html


@pytest.mark.django_db
def test_compare_non_htmx_get_returns_the_standalone_fragment_not_a_blank_page(client, minimal_system):
    """A non-HX GET to /compare/ (a stray direct hit) returns the same standalone dashboard fragment, not
    a blank base.html page. Compare uses plain render (not htmx_render), so it never falls through to the
    non-HX → base.html branch — there is no full-page Compare route and no dead `dashboard` flag."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 = "Copy of Test System"

    response = client.get("/model_builder/compare/")  # no HX-Request header
    assert response.status_code == 200
    html = response.content.decode()
    # The dashboard fragment itself (its #comparison-page wrapper + KPI/chart markup), not a blank <main>.
    assert 'id="comparison-page"' in html
    assert "comparison-dashboard" in html
    assert "data-paired-chart" in html
    # It is the bare fragment, NOT the full page: base.html's shell (navbar / main-content-block) is absent.
    assert "main-content-block" not in html


@pytest.mark.django_db
def test_compare_reflects_an_edit_to_a_model_with_no_stale_results(client, minimal_system):
    """An edit to either model must show up the next time Compare is opened — the dashboard is rebuilt
    fresh from the current session each visit (no cached comparison)."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 active

    # Rename the active (second) model through the real edit flow.
    client.post("/model_builder/save-system-name/", {"name": "Edge caching variant"})

    response = client.get("/model_builder/compare/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    html = response.content.decode()
    assert "Edge caching variant" in html  # the edit is reflected, not a stale "Copy of …"


@pytest.mark.django_db
def test_compare_with_one_model_returns_an_empty_response(client, minimal_system):
    """A direct hit on /compare/ with only one model returns an empty response rather than erroring
    (disabled-instead-of-error; the Compare tab is disabled in the UI in this state). The dashboard
    swaps into the resident #comparison-view sibling, so rendering a builder there would nest a builder
    inside the comparison block — the empty response is the no-op the disabled tab implies."""
    _seed_active_slot(client, minimal_system)
    response = client.get("/model_builder/compare/")
    assert response.status_code == 200
    assert response.content == b""


@pytest.mark.django_db
def test_compare_with_an_incomplete_second_model_returns_an_empty_response(client, minimal_system):
    """A blank second model has no computable footprint, so /compare/ must NOT run the comparison
    (which would read a non-existent footprint and 500) — it returns an empty response (the dashboard
    target stays empty), and the Compare tab is disabled in the UI (disabled-instead-of-error)."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "blank"})  # slot 1 = blank, not computable

    response = client.get("/model_builder/compare/")
    assert response.status_code == 200  # never 500s on an incomplete model
    assert response.content == b""      # no comparison rendered (and no builder nested inside the view)


@pytest.mark.django_db
def test_per_model_export_round_trips_into_a_target_slot(client, minimal_system):
    """Each slot exports the single-model format and re-imports into the active slot unchanged
    (object ids preserved); the second slot's export carries its own system."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "blank"})  # slot 1 active, blank

    # Export slot 0 (the seeded model) explicitly by slot.
    exported = client.get("/model_builder/download-json/?slot=0")
    assert exported.status_code == 200
    exported_doc = json.loads(b"".join(exported.streaming_content) if exported.streaming
                              else exported.content)
    assert "System" in exported_doc and "efootprint_version" in exported_doc
    assert "interface_config" not in exported_doc or isinstance(exported_doc["interface_config"], dict)


@pytest.mark.django_db
def test_entry_view_collapses_workspace_when_a_parked_slot_cache_expired(client, minimal_system):
    """A returning user whose parked model's cache lapsed lands on the survivor, not a 500.

    The session index outlives the slots' cache payloads (Redis/Postgres TTLs are far shorter than the
    session). Regression: build_workspace_slots hydrated the now-empty slot and read .system on its
    un-hydrated ModelWeb, raising SessionExpiredError outside model_builder_main's try/except -> 500.
    """
    from model_builder.adapters.repositories.cache_backend import CacheBackend

    _seed_active_slot(client, minimal_system)                        # slot 0 (the model that survives)
    client.post("/model_builder/add-model/", {"source": "blank"})   # slot 1 (parked model that expires)
    session = client.session
    workspace = SessionWorkspaceRepository(session)
    assert workspace.list_slots() == [0, 1]
    workspace.set_active_slot(0)
    session.save()

    # Drop slot 1's payload from both caches while the session index still lists it (TTL expiry).
    CacheBackend().delete(workspace.repository_for(1)._cache_key())

    response = client.get("/model_builder/")

    assert response.status_code == 200  # was a 500 before the index↔cache reconciliation
    # The dead slot is reconciled out of the index; the workspace collapses to the surviving model.
    assert SessionWorkspaceRepository(client.session).list_slots() == [0]


@pytest.mark.django_db
def test_entry_view_reseeds_when_every_slot_cache_expired(client, minimal_system):
    """The real returning-user case: a few days idle expires *both* slots (identical TTLs), so nothing
    survives. The entry view must drop the dead parked slot, re-seed the empty active slot to the
    scratch baseline, and render — not 500. The blank model offered on the recovery page is that
    re-seed, not recovered data.
    """
    from model_builder.adapters.repositories.cache_backend import CacheBackend

    _seed_active_slot(client, minimal_system)                        # slot 0
    client.post("/model_builder/add-model/", {"source": "blank"})   # slot 1
    session = client.session
    workspace = SessionWorkspaceRepository(session)
    workspace.set_active_slot(0)
    session.save()
    assert workspace.list_slots() == [0, 1]

    # Both payloads expire from both caches while the session index still lists both slots.
    CacheBackend().delete(workspace.repository_for(0)._cache_key())
    CacheBackend().delete(workspace.repository_for(1)._cache_key())

    response = client.get("/model_builder/")

    assert response.status_code == 200  # was a 500 (build_workspace_slots crashed on the empty slots)
    # Collapsed to a single slot, whose now-empty active model was re-seeded to the scratch baseline.
    workspace_after = SessionWorkspaceRepository(client.session)
    assert workspace_after.list_slots() == [0]
    assert workspace_after.active_repository().has_system_data()
