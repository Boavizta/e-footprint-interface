"""Unit tests for the template-picker presenter.

The presenter is the only place that turns raw catalog entries into picker view
models: it resolves ``showcased_concepts`` tokens to display chips (``{class:X}``
via ``CLASS_UI_CONFIG``, ``CONCEPTS`` keys via their label) and builds mkdocs
deep-link URLs from how-to ``doc_path``s. The e2e render only smoke-tests that
this doesn't crash; these tests pin the actual label/URL mapping so a wrong chip
label or malformed doc link fails here.
"""
from django.test import override_settings

from model_builder.adapters.ui_config import CLASS_UI_CONFIG
from model_builder.adapters.presenters.template_picker_presenter import (
    _doc_url, _resolve_chip, build_picker_groups)
from model_builder.domain.reference_data.modeling_templates import CONCEPTS


def test_resolve_chip_class_token_uses_class_ui_label_and_help_target():
    chip = _resolve_chip("{class:Server}")
    assert chip == {"label": CLASS_UI_CONFIG["Server"]["label"], "help_class": "Server"}


def test_resolve_chip_unknown_class_token_falls_back_to_class_name():
    # CLASS_UI_CONFIG has no entry for a not-yet-configured class: label is the bare name.
    chip = _resolve_chip("{class:NotAConfiguredClass}")
    assert chip == {"label": "NotAConfiguredClass", "help_class": "NotAConfiguredClass"}


def test_resolve_chip_concept_token_uses_concept_label_and_help_class():
    concept = CONCEPTS["database"]
    chip = _resolve_chip("database")
    assert chip == {"label": concept.label, "help_class": concept.help_class}


@override_settings(MKDOCS_BASE_URL="https://docs.example.org/")
def test_doc_url_strips_md_and_joins_a_single_slash():
    assert _doc_url("database_modeling.md") == "https://docs.example.org/database_modeling/"


@override_settings(MKDOCS_BASE_URL="https://docs.example.org")
def test_doc_url_handles_base_without_trailing_slash():
    assert _doc_url("server_to_server_interaction.md") == \
        "https://docs.example.org/server_to_server_interaction/"


@override_settings(MKDOCS_BASE_URL="https://docs.example.org")
def test_build_picker_groups_resolves_chips_and_doc_urls():
    groups = {group["id"]: group for group in build_picker_groups()}

    intro_entries = groups["introductory"]["entries"]
    assert intro_entries  # the registry ships at least one introductory template
    for entry in intro_entries:
        assert entry["chips"]  # introductory entries carry showcased concepts
        assert all(chip["label"] for chip in entry["chips"])
        assert entry["doc_url"] is None  # no mkdocs deep-link for introductory templates

    how_to_entries = groups["how_to"]["entries"]
    assert how_to_entries  # the library ships how-to templates
    for entry in how_to_entries:
        assert entry["doc_url"].startswith("https://docs.example.org/")
        assert entry["doc_url"].endswith("/")
