import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

from model_builder.adapters.card_order import ordered_card_lists, stable_rank_merge
from model_builder.adapters.presenters.oob_regions import _render_edge_device_lists, _render_model_canvas
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views import views


def _objects(*web_ids):
    return [SimpleNamespace(web_id=web_id) for web_id in web_ids]


def _web_ids(objects):
    return [obj.web_id for obj in objects]


@pytest.mark.parametrize(
    ("saved_ids", "expected"),
    [
        (["c", "a", "b"], ["c", "a", "b"]),
        ([], ["a", "b", "c"]),
        (["stale", "b"], ["b", "a", "c"]),
        (["b", "b", "a"], ["b", "a", "c"]),
        (["b"], ["b", "a", "c"]),
    ],
)
def test_stable_rank_merge(saved_ids, expected):
    assert _web_ids(stable_rank_merge(_objects("a", "b", "c"), saved_ids)) == expected


def test_ordered_card_lists_combines_web_and_edge_objects_and_orders_all_six_lists():
    card_order = {
        "up-list": ["edge-up", "web-up"],
        "uj-list": ["edge-uj", "web-uj"],
        "external-api-list": ["api"],
        "server-list": ["server"],
        "edge-device-groups-list": ["group"],
        "edge-devices-list": ["device"],
    }
    model_web = SimpleNamespace(
        repository=SimpleNamespace(interface_config={"card_order": card_order}),
        usage_patterns=_objects("web-up"),
        edge_usage_patterns=_objects("edge-up"),
        usage_journeys=_objects("web-uj"),
        edge_usage_journeys=_objects("edge-uj"),
        external_apis=_objects("api"),
        servers=_objects("server"),
        root_edge_device_groups=_objects("group"),
        ungrouped_edge_devices=_objects("device"),
    )

    ordered = ordered_card_lists(model_web)

    assert _web_ids(ordered["ordered_usage_patterns"]) == ["edge-up", "web-up"]
    assert _web_ids(ordered["ordered_usage_journeys"]) == ["edge-uj", "web-uj"]
    assert _web_ids(ordered["ordered_external_apis"]) == ["api"]
    assert _web_ids(ordered["ordered_servers"]) == ["server"]
    assert _web_ids(ordered["ordered_root_edge_device_groups"]) == ["group"]
    assert _web_ids(ordered["ordered_ungrouped_edge_devices"]) == ["device"]


def test_ordered_card_lists_uses_natural_order_when_configuration_is_missing():
    model_web = SimpleNamespace(
        repository=SimpleNamespace(interface_config={}),
        usage_patterns=_objects("first", "second"),
        edge_usage_patterns=[],
        usage_journeys=[],
        edge_usage_journeys=[],
        external_apis=[],
        servers=[],
        root_edge_device_groups=[],
        ungrouped_edge_devices=[],
    )

    assert _web_ids(ordered_card_lists(model_web)["ordered_usage_patterns"]) == ["first", "second"]


class _Workspace:
    def __init__(self, repositories):
        self.repositories = repositories

    def active_slot(self):
        return 0

    def list_slots(self):
        return [0, 1]

    def repository_for(self, slot):
        return self.repositories[slot]


def _model_for(repository, natural_order):
    return SimpleNamespace(
        repository=repository,
        system=SimpleNamespace(name=f"model-{repository.slot}"),
        usage_patterns=_objects(*natural_order),
        edge_usage_patterns=[],
        usage_journeys=[],
        edge_usage_journeys=[],
        external_apis=[],
        servers=[],
        root_edge_device_groups=[],
        ungrouped_edge_devices=[],
    )


def test_workspace_render_context_orders_each_resident_canvas_from_its_own_config(monkeypatch):
    repositories = {
        0: SimpleNamespace(slot=0, interface_config={"card_order": {"up-list": ["a", "b"]}}),
        1: SimpleNamespace(slot=1, interface_config={"card_order": {"up-list": ["b", "a"]}}),
    }
    models = {slot: _model_for(repository, ["b", "a"]) for slot, repository in repositories.items()}
    workspace = _Workspace(repositories)
    monkeypatch.setattr(views, "ModelWeb", lambda repository: models[repository.slot])

    slots = views.build_workspace_slots(workspace, active_model_web=models[0])

    assert _web_ids(slots[0]["ordered_usage_patterns"]) == ["a", "b"]
    assert _web_ids(slots[1]["ordered_usage_patterns"]) == ["b", "a"]


@pytest.mark.django_db
def test_canvas_template_renders_all_six_explicit_ordered_lists():
    def cards(prefix):
        return [
            SimpleNamespace(web_id=f"{prefix}-second", efootprint_id=f"{prefix}-second"),
            SimpleNamespace(web_id=f"{prefix}-first", efootprint_id=f"{prefix}-first"),
        ]

    slot_entry = {
        "ordered_usage_patterns": cards("up"),
        "ordered_usage_journeys": cards("uj"),
        "ordered_external_apis": cards("api"),
        "ordered_servers": cards("server"),
        "ordered_root_edge_device_groups": cards("group"),
        "ordered_ungrouped_edge_devices": cards("device"),
    }

    content = render_to_string(
        "model_builder/components/model_canvas_content.html",
        {
            "slot_entry": slot_entry,
            "model_web": SimpleNamespace(creation_constraints={}),
            "slot_suffix": "",
            "is_active_canvas": True,
            "class_help_info": {},
        },
    )

    for prefix in ("up", "uj", "api", "server", "group", "device"):
        assert content.index(f'id="{prefix}-second"') < content.index(f'id="{prefix}-first"')


def _model_web_for_ordered_oob_render():
    def cards(prefix):
        return [
            SimpleNamespace(web_id=f"{prefix}-second", efootprint_id=f"{prefix}-second"),
            SimpleNamespace(web_id=f"{prefix}-first", efootprint_id=f"{prefix}-first"),
        ]

    card_order = {
        "up-list": ["up-first", "up-second"],
        "uj-list": ["uj-first", "uj-second"],
        "external-api-list": ["api-first", "api-second"],
        "server-list": ["server-first", "server-second"],
        "edge-device-groups-list": ["group-first", "group-second"],
        "edge-devices-list": ["device-first", "device-second"],
    }
    return SimpleNamespace(
        repository=SimpleNamespace(slot=0, interface_config={"card_order": card_order}),
        creation_constraints={},
        usage_patterns=cards("up"),
        edge_usage_patterns=[],
        usage_journeys=cards("uj"),
        edge_usage_journeys=[],
        external_apis=cards("api"),
        servers=cards("server"),
        root_edge_device_groups=cards("group"),
        ungrouped_edge_devices=cards("device"),
    )


@pytest.mark.django_db
def test_full_canvas_oob_render_preserves_saved_order_for_all_six_lists():
    content = _render_model_canvas(_model_web_for_ordered_oob_render(), {})

    for prefix in ("up", "uj", "api", "server", "group", "device"):
        assert content.index(f'id="{prefix}-first"') < content.index(f'id="{prefix}-second"')


@pytest.mark.django_db
def test_edge_device_lists_oob_render_preserves_saved_order():
    content = _render_edge_device_lists(_model_web_for_ordered_oob_render(), {})

    for prefix in ("group", "device"):
        assert content.index(f'id="{prefix}-first"') < content.index(f'id="{prefix}-second"')


COMPLETE_CARD_ORDER = {
    "up-list": ["UsagePattern_a"],
    "uj-list": ["UsageJourney_a"],
    "external-api-list": ["ExternalAPI_a"],
    "server-list": ["Server_a"],
    "edge-device-groups-list": ["EdgeDeviceGroup_a"],
    "edge-devices-list": ["EdgeDeviceBase_a"],
}


@pytest.mark.django_db
def test_save_card_order_persists_complete_mapping_and_preserves_siblings_and_other_config(client, minimal_system_data):
    active_repository = SessionSystemRepository(client.session, slot=0)
    active_repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
    active_repository.save_data(deepcopy(minimal_system_data))
    parked_repository = SessionSystemRepository(client.session, slot=1)
    parked_repository.interface_config = {"sankey_diagrams": [{"id": "parked"}]}
    parked_repository.save_data(deepcopy(minimal_system_data))

    response = client.post(
        "/model_builder/save-card-order/",
        data=json.dumps(COMPLETE_CARD_ORDER),
        content_type="application/json",
    )

    assert response.status_code == 204
    active_data = SessionSystemRepository(client.session, slot=0).get_system_data()
    assert active_data["interface_config"] == {
        "sankey_diagrams": [{"id": "deadbeef"}],
        "card_order": COMPLETE_CARD_ORDER,
    }
    parked_data = SessionSystemRepository(client.session, slot=1).get_system_data()
    assert parked_data["interface_config"] == {"sankey_diagrams": [{"id": "parked"}]}


INVALID_PAYLOADS = [
    b"",
    b"{",
    json.dumps({key: value for key, value in COMPLETE_CARD_ORDER.items() if key != "server-list"}).encode(),
    json.dumps({**COMPLETE_CARD_ORDER, "other-list": []}).encode(),
    json.dumps({**COMPLETE_CARD_ORDER, "server-list": "Server_a"}).encode(),
    json.dumps({**COMPLETE_CARD_ORDER, "server-list": [123]}).encode(),
]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_save_card_order_rejects_invalid_payload_without_changing_config(client, minimal_system_data, payload):
    repository = SessionSystemRepository(client.session)
    original_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
    repository.interface_config = deepcopy(original_config)
    repository.save_data(deepcopy(minimal_system_data))

    response = client.generic("POST", "/model_builder/save-card-order/", payload, content_type="application/json")

    assert response.status_code == 400
    saved_data = SessionSystemRepository(client.session).get_system_data()
    assert saved_data["interface_config"] == original_config
