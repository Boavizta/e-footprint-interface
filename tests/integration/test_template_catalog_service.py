"""Integration tests for the first-run template-catalog service.

Exercises the merge of the interface-owned introductory registry with the
library's how-to templates and how-to guides (``list_how_to_templates`` /
``list_how_to_guides``) into a single picker group, plus the ``template_id`` →
serialized-System resolution that backs the load endpoint. Runs pure domain — no
Django scaffolding.
"""
import pytest
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.modeling_templates import list_how_to_templates

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES
from model_builder.domain.services import (
    ProgressiveImportService, SCRATCH_ID, build_template_catalog, get_template_system_data)


def _catalog_entries() -> dict:
    """All non-scratch entries keyed by id, flattened across groups."""
    return {entry.id: entry
            for group in build_template_catalog()
            for entry in group.entries
            if entry.category != "scratch"}


def test_catalog_has_a_merged_templates_group_then_scratch():
    groups = {group.id: group for group in build_template_catalog()}
    assert list(groups) == ["templates", "scratch"]


def test_templates_group_lists_introductory_then_how_to_templates():
    groups = {group.id: group for group in build_template_catalog()}
    entries = groups["templates"].entries
    expected = [t.id for t in INTRO_TEMPLATES] + [t.id for t in list_how_to_templates()]
    assert [e.id for e in entries] == expected


def test_introductory_entries_carry_their_picker_chips():
    entries = _catalog_entries()
    for t in INTRO_TEMPLATES:
        entry = entries[t.id]
        assert entry.category == "introductory"
        assert entry.icon and entry.showcased_concepts  # carried through for the picker chips


def test_ecommerce_card_references_the_database_and_server_to_server_guides():
    """The two guides that share the e-commerce scenario both hang off its one card."""
    ecommerce = _catalog_entries()["ecommerce"]
    assert {g.doc_path for g in ecommerce.related_guides} == {
        "database_modeling.md", "server_to_server_interaction.md"}
    assert all(g.name for g in ecommerce.related_guides)  # display label for the footer link


def test_machine_learning_card_references_its_single_guide():
    ml = _catalog_entries()["machine_learning_workflow"]
    assert [g.doc_path for g in ml.related_guides] == ["machine_learning_workflow.md"]


def test_templates_without_a_how_to_page_carry_no_guides():
    entries = _catalog_entries()
    assert entries["ai_chatbot"].related_guides == ()
    assert entries["iot_industrial"].related_guides == ()


def test_scratch_group_is_the_empty_baseline_sentinel():
    groups = {group.id: group for group in build_template_catalog()}
    scratch_entries = groups["scratch"].entries
    assert [e.id for e in scratch_entries] == [SCRATCH_ID]
    assert scratch_entries[0].category == "scratch"


@pytest.mark.parametrize("template_id", ["scratch", "ecommerce", "ai_chatbot", "iot_industrial",
                                         "machine_learning_workflow"])
def test_get_template_system_data_resolves_a_loadable_system(template_id):
    system_data = get_template_system_data(template_id)
    assert "System" in system_data
    # Exercise the resolved JSON through the library loader so a broken path/payload fails here.
    class_obj_dict, _, _ = json_to_system(system_data, launch_system_computations=False)
    assert class_obj_dict["System"]


def test_every_card_resolves_to_a_loadable_template():
    """No card can offer a scenario the load endpoint would 404 on."""
    for template_id in _catalog_entries():
        assert "System" in get_template_system_data(template_id)


def test_machine_learning_template_survives_interface_persistence_round_trip():
    imported = ProgressiveImportService(max_payload_size_mb=30.0).import_system(
        get_template_system_data("machine_learning_workflow"))
    repository = InMemorySystemRepository(initial_data=imported)

    ModelWeb(repository).persist_to_cache()

    reloaded = ModelWeb(repository)
    assert [usage_pattern.name for usage_pattern in reloaded.usage_patterns] == [
        "Weekly retraining pattern",
        "Production inference pattern",
    ]


def test_get_template_system_data_unknown_id_raises():
    with pytest.raises(KeyError):
        get_template_system_data("not-a-template")
