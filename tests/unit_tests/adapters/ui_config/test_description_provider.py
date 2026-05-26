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
HREF_RE = re.compile(r'href="([^"]+)"')
DOC_ANCHOR_RE = re.compile(r'<a href="([^"]+)" target="_blank" rel="noopener">([^<]+)</a>')
SEPARATOR = "<br><br>"


@pytest.fixture
def provider():
    return EfootprintDescriptionProvider(build_html_handlers(UI_TOKENS, "https://docs.example/"))


# ---- field_tooltip merging (drives the four _merge branches end-to-end) ----

def test_field_tooltip_returns_merged_when_both_sources_present(provider):
    # `Server.average_carbon_intensity` carries both a library `param_descriptions`
    # entry and a `field_ui_config.json` tooltip; structural check only.
    out = provider.field_tooltip("Server", "average_carbon_intensity")
    assert out is not None
    library_part, sep, interface_part = out.partition(SEPARATOR)
    assert sep == SEPARATOR
    assert library_part and interface_part
    assert not PLACEHOLDER_RE.search(out)


def test_field_tooltip_returns_library_only_when_interface_text_missing(provider):
    # `Server.power` has a library description but no `field_ui_config.json` tooltip.
    out = provider.field_tooltip("Server", "power")
    assert out is not None
    assert SEPARATOR not in out
    assert not PLACEHOLDER_RE.search(out)


def test_field_tooltip_returns_none_when_both_sources_absent(provider):
    # `Server.name` has neither a `param_descriptions` entry nor a `field_ui_config.json` tooltip.
    assert provider.field_tooltip("Server", "name") is None


def test_field_tooltip_resolves_placeholders_on_interface_text_in_both_branches(provider):
    # `parent_group_memberships` is the canonical interface-only tooltip with a {class:...}
    # placeholder; field_tooltip routes interface text through the resolver in every branch.
    out = provider.field_tooltip("EdgeDeviceGroup", "parent_group_memberships")
    # No library param for this attr, so this is the interface-only branch.
    assert out is not None
    assert "{class:" not in out
    assert "Edge device group" in out


def test_field_tooltip_for_edge_device_group_sub_group_counts_is_library_only(provider):
    out = provider.field_tooltip("EdgeDeviceGroup", "sub_group_counts")
    assert out is not None
    assert SEPARATOR not in out


def test_field_tooltip_for_edge_device_group_edge_device_counts_is_library_only(provider):
    out = provider.field_tooltip("EdgeDeviceGroup", "edge_device_counts")
    assert out is not None
    assert SEPARATOR not in out


# ---- interface_only_tooltip -----------------------------------------------

def test_interface_only_tooltip_resolves_placeholders(provider):
    out = provider.interface_only_tooltip("parent_group_memberships")
    assert out is not None
    assert "{class:" not in out
    assert "Edge device group" in out


def test_interface_only_tooltip_returns_none_for_unknown_attr(provider):
    assert provider.interface_only_tooltip("not_a_field") is None


# ---- class_doc_link -------------------------------------------------------

def test_class_doc_link_emits_anchor_to_class_slug(provider):
    out = provider.class_doc_link("Server")
    assert DOC_ANCHOR_RE.findall(out) == [("https://docs.example/Server", "Custom server")]
    assert 'target="_blank"' in out


@pytest.mark.parametrize(
    ("class_name", "expected_anchors"),
    [
        ("ServerBase", [
            ("https://docs.example/GPUServer", "AI server"),
            ("https://docs.example/BoaviztaCloudServer", "Cloud server"),
            ("https://docs.example/Server", "Custom server"),
        ]),
        ("EdgeDeviceBase", [
            ("https://docs.example/EdgeComputer", "Edge computer"),
            ("https://docs.example/EdgeAppliance", "Edge appliance"),
            ("https://docs.example/EdgeDevice", "Edge device"),
        ]),
        ("ExternalAPI", [
            ("https://docs.example/EcoLogitsGenAIExternalAPI", "Gen AI external API"),
            ("https://docs.example/EcoLogitsVideoGenExternalAPI", "Gen AI video external API"),
        ]),
    ],
)
def test_class_doc_link_for_abstract_class_links_to_concrete_docs(provider, class_name, expected_anchors):
    out = provider.class_doc_link(class_name)
    assert DOC_ANCHOR_RE.findall(out) == expected_anchors
    assert f"https://docs.example/{class_name}" not in HREF_RE.findall(out)


# ---- class_description ----------------------------------------------------

def test_class_description_resolves_placeholders(provider):
    out = provider.class_description("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_class_description_strips_docstring_indentation(provider):
    out = provider.class_description("Server")
    assert out
    assert not out.startswith(" "), f"Docstring not dedented: {out!r}"


def test_class_description_falls_back_to_json_for_interface_only_abstract_base(provider):
    # `EdgeDeviceBase` has no Python class but carries a JSON-authored `description`.
    out = provider.class_description("EdgeDeviceBase")
    assert out is not None
    assert "{class:" not in out
    # The authored text references EdgeComputer/EdgeAppliance; resolver should
    # have rendered them as anchor labels.
    assert "Edge computer" in out
    assert "Edge appliance" in out


# ---- class_disambiguation / class_pitfalls --------------------------------

def test_class_disambiguation_resolves_placeholders(provider):
    out = provider.class_disambiguation("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_class_disambiguation_returns_none_for_interface_only_abstract_base(provider):
    # No Python class behind `EdgeDeviceBase`, so no class-level attr to read.
    assert provider.class_disambiguation("EdgeDeviceBase") is None


def test_class_pitfalls_resolves_placeholders(provider):
    out = provider.class_pitfalls("Server")
    assert out is not None
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


# ---- class_interactions ---------------------------------------------------

def test_class_interactions_resolves_ui_tokens(provider):
    out = provider.class_interactions("ServerBase")
    assert out is not None
    assert "data-ui-token" in out
    assert not PLACEHOLDER_RE.search(out), f"Unresolved tokens in: {out!r}"


def test_concrete_subclass_inherits_interactions_from_abstract_base(provider):
    # `Server` has no `interactions` entry of its own; should walk up to `ServerBase`.
    out = provider.class_interactions("Server")
    assert out is not None
    assert "data-ui-token" in out


def test_class_interactions_returns_none_when_no_entry_anywhere_in_mro(provider):
    # `UsageJourneyStep` has no `interactions` and neither does its MRO.
    assert provider.class_interactions("UsageJourneyStep") is None


# ---- error path -----------------------------------------------------------

def test_unknown_class_raises(provider):
    with pytest.raises(ValueError):
        provider.class_description("NotAClass")


def test_calc_description_still_raises_for_interface_only_abstract_base(provider):
    # Methods that genuinely require a Python class (calc/param) reject interface-only bases.
    with pytest.raises(ValueError):
        provider.calc_description("EdgeDeviceBase", "anything")


# ---- singleton import -----------------------------------------------------

def test_module_level_singleton_is_constructed():
    assert isinstance(EFOOTPRINT_DESCRIPTION_PROVIDER, EfootprintDescriptionProvider)
    assert EFOOTPRINT_DESCRIPTION_PROVIDER.class_description("Server") is not None
