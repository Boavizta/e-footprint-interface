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
SEPARATOR = "<br><br>"


@pytest.fixture
def provider():
    return EfootprintDescriptionProvider(build_html_handlers(UI_TOKENS, "https://docs.example"))


# ---- _merge (the actual unit under test for the four-branch logic) --------

def test_merge_returns_none_when_both_absent(provider):
    assert provider._merge(None, None) is None
    assert provider._merge("", "") is None


def test_merge_resolves_library_only(provider):
    out = provider._merge("library text", None)
    assert out == "library text"
    assert SEPARATOR not in out


def test_merge_escapes_interface_only(provider):
    out = provider._merge(None, "<b>iface</b>")
    assert "&lt;b&gt;" in out
    assert "<b>" not in out
    assert SEPARATOR not in out


def test_merge_joins_library_then_interface_with_separator(provider):
    out = provider._merge("library text", "interface text")
    library_part, _, interface_part = out.partition(SEPARATOR)
    assert library_part == "library text"
    assert interface_part == "interface text"


def test_merge_escapes_interface_text_in_merged_output(provider):
    out = provider._merge("library text", "<b>iface</b>")
    _, _, interface_part = out.partition(SEPARATOR)
    assert "&lt;b&gt;" in interface_part
    assert "<b>" not in interface_part


# ---- field_tooltip end-to-end (validates the (class, param) lookup path) --

def test_field_tooltip_merged_for_known_pair_with_both_sources(provider):
    # `Server.average_carbon_intensity` carries both a library `param_descriptions`
    # entry and a `field_ui_config.json` tooltip; structural check only.
    out = provider.field_tooltip("Server", "average_carbon_intensity")
    assert out is not None
    library_part, sep, interface_part = out.partition(SEPARATOR)
    assert sep == SEPARATOR
    assert library_part and interface_part
    assert not PLACEHOLDER_RE.search(out)


def test_field_tooltip_library_only_for_known_pair_without_interface_text(provider):
    # `Server.power` has a library description but no `field_ui_config.json` tooltip.
    out = provider.field_tooltip("Server", "power")
    assert out is not None
    assert SEPARATOR not in out
    assert not PLACEHOLDER_RE.search(out)


def test_field_tooltip_for_edge_device_group_sub_group_counts_is_library_only(provider):
    # parent_group_memberships is the UI surface for the child-creation flip and carries its own
    # interface tooltip; sub_group_counts/edge_device_counts must stay library-only so the
    # parent-edit form keeps the correct (parent's-perspective) text.
    out = provider.field_tooltip("EdgeDeviceGroup", "sub_group_counts")
    assert out is not None
    assert SEPARATOR not in out


def test_field_tooltip_for_edge_device_group_edge_device_counts_is_library_only(provider):
    out = provider.field_tooltip("EdgeDeviceGroup", "edge_device_counts")
    assert out is not None
    assert SEPARATOR not in out


# ---- placeholder resolution ------------------------------------------------

def test_class_description_resolves_placeholders(provider):
    out = provider.class_description("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_class_description_strips_docstring_indentation(provider):
    # ``inspect.getdoc`` is what dedents — verify by checking the first line
    # doesn't start with whitespace.
    out = provider.class_description("Server")
    assert out
    assert not out.startswith(" "), f"Docstring not dedented: {out!r}"


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


# ---- error path ------------------------------------------------------------

def test_unknown_class_raises(provider):
    with pytest.raises(ValueError):
        provider.class_description("NotAClass")


# ---- singleton import ------------------------------------------------------

def test_module_level_singleton_is_constructed():
    assert isinstance(EFOOTPRINT_DESCRIPTION_PROVIDER, EfootprintDescriptionProvider)
    assert EFOOTPRINT_DESCRIPTION_PROVIDER.class_description("Server") is not None
