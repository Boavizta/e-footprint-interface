"""Unit tests for ``build_workspace_slots`` — the per-slot ModelWeb wrapper list.

Focus: the active-slot dedupe. The entry view already holds the active slot's ``ModelWeb`` (for the
shared chrome), so passing it back in must reuse that instance rather than deserialize the same model a
second time — a render builds each model once, not the active one twice.
"""
from model_builder.adapters.views import views


class _FakeWorkspace:
    """Minimal workspace: two slots, slot 0 active; ``repository_for`` just echoes the slot."""

    def active_slot(self):
        return 0

    def list_slots(self):
        return [0, 1]

    def repository_for(self, slot):
        return slot


def _stub_model_web(name):
    return type("MW", (), {"system": type("S", (), {"name": name})()})()


def test_active_slot_reuses_passed_model_web_and_builds_only_the_parked_one(monkeypatch):
    built = []

    def counting_model_web(repo):
        built.append(repo)
        return _stub_model_web(f"slot{repo}")

    monkeypatch.setattr(views, "ModelWeb", counting_model_web)
    active = _stub_model_web("active")

    slots = views.build_workspace_slots(_FakeWorkspace(), active_model_web=active)

    # The active slot reuses the caller's instance; only the parked slot triggers a ModelWeb build.
    assert slots[0]["model_web"] is active
    assert slots[0]["name"] == "active"
    assert built == [1]  # built once, for the parked slot — never for the active slot
    assert slots[1]["model_web"] is not active


def test_without_an_active_model_web_every_slot_is_built(monkeypatch):
    built = []

    def counting_model_web(repo):
        built.append(repo)
        return _stub_model_web(f"slot{repo}")

    monkeypatch.setattr(views, "ModelWeb", counting_model_web)

    slots = views.build_workspace_slots(_FakeWorkspace())

    # Backwards-compatible default: no instance to reuse, so both slots are built.
    assert built == [0, 1]
    assert [s["is_active"] for s in slots] == [True, False]
    assert [s["suffix"] for s in slots] == ["", "-1"]
