"""Tests for ``EfootprintDescriptionProvider`` and the module singleton."""
import re

import pytest

from model_builder.adapters.ui_config.efootprint_description_provider import (
    EFOOTPRINT_DESCRIPTION_PROVIDER,
    EfootprintDescriptionProvider,
)
from model_builder.adapters.ui_config.interface_placeholder_handlers import build_html_handlers
from model_builder.adapters.ui_config.ui_token_registry import UI_TOKENS


PLACEHOLDER_RE = re.compile(r"\{(class|param|calc|doc|ui):[^}]+\}")


@pytest.fixture
def provider():
    return EfootprintDescriptionProvider(build_html_handlers(UI_TOKENS, "https://docs.example"))


# ---- field_tooltip merge ---------------------------------------------------

def test_field_tooltip_returns_merged_when_both_present(provider):
    out = provider.field_tooltip("Server", "average_carbon_intensity")
    assert "<br><br>" in out
    library_idx = out.find("Average grid carbon intensity")
    interface_idx = out.find("Common values")
    assert 0 <= library_idx < interface_idx, "Library text must come before interface text"


def test_field_tooltip_returns_library_only_when_interface_absent(provider):
    out = provider.field_tooltip("Server", "power")
    assert out is not None
    assert "Electrical power" in out
    assert "<br><br>" not in out


def test_field_tooltip_returns_interface_only_when_library_absent(provider):
    # Forge a class/param pair where library has no description but interface does.
    # `parent_group_memberships` is no longer a real param after the migration; pick a
    # field whose interface tooltip exists but whose param is not in any param_descriptions.
    # Simulate by calling on a class whose param_descriptions lacks it.
    class FakeKlass:
        param_descriptions = {}

    provider._class_cache["FakeKlass"] = FakeKlass
    # Use `average_carbon_intensity` (interface tooltip exists) on FakeKlass.
    out = provider.field_tooltip("FakeKlass", "average_carbon_intensity")
    assert out is not None
    assert "Common values" in out
    assert "<br><br>" not in out


def test_field_tooltip_returns_none_when_neither_present(provider):
    class EmptyKlass:
        param_descriptions = {}

    provider._class_cache["EmptyKlass"] = EmptyKlass
    assert provider.field_tooltip("EmptyKlass", "no_such_param") is None


def test_field_tooltip_for_edge_device_group_sub_group_counts(provider):
    out = provider.field_tooltip("EdgeDeviceGroup", "sub_group_counts")
    assert out is not None
    assert "<br><br>" in out


def test_field_tooltip_for_edge_device_group_edge_device_counts(provider):
    out = provider.field_tooltip("EdgeDeviceGroup", "edge_device_counts")
    assert out is not None
    assert "<br><br>" in out


# ---- placeholder resolution ------------------------------------------------

def test_class_description_resolves_placeholders(provider):
    out = provider.class_description("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_class_disambiguation_resolves_placeholders(provider):
    out = provider.class_disambiguation("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_class_pitfalls_resolves_placeholders(provider):
    out = provider.class_pitfalls("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_class_interactions_resolves_ui_tokens(provider):
    out = provider.class_interactions("ServerBase")
    assert out is not None
    assert "data-ui-token" in out
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


# ---- inheritance via MRO ---------------------------------------------------

def test_concrete_subclass_inherits_interactions_from_abstract_base(provider):
    # `Server` has no `interactions` entry of its own; should walk up to `ServerBase`.
    out = provider.class_interactions("Server")
    assert out is not None
    assert "data-ui-token" in out


# ---- singleton import ------------------------------------------------------

def test_module_level_singleton_is_constructed():
    assert isinstance(EFOOTPRINT_DESCRIPTION_PROVIDER, EfootprintDescriptionProvider)
    assert EFOOTPRINT_DESCRIPTION_PROVIDER.class_description("Server") is not None
