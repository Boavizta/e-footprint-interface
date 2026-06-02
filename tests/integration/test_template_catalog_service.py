"""Integration tests for the first-run template-catalog service.

Exercises the merge of the interface-owned introductory registry with the
library's how-to public API (``list_how_to_templates`` / ``get_template``) and the
``template_id`` → serialized-System resolution that backs the load endpoint. Runs
pure domain — no Django scaffolding (constitution §1.1).
"""
import pytest
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.modeling_templates import list_how_to_templates

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES
from model_builder.domain.services import (
    OBSOLETE_HOW_TO_TEMPLATE_IDS, ProgressiveImportService, SCRATCH_ID, build_template_catalog,
    get_template_system_data)


def test_catalog_has_introductory_howto_and_scratch_groups():
    groups = {group.id: group for group in build_template_catalog()}
    assert list(groups) == ["introductory", "how_to", "scratch"]


def test_introductory_group_mirrors_the_registry():
    groups = {group.id: group for group in build_template_catalog()}
    intro = groups["introductory"]
    assert [e.id for e in intro.entries] == [t.id for t in INTRO_TEMPLATES]
    for entry in intro.entries:
        assert entry.category == "introductory"
        assert entry.icon and entry.showcased_concepts  # carried through for the picker chips
        assert entry.doc_path is None


def test_howto_group_merges_library_public_api():
    groups = {group.id: group for group in build_template_catalog()}
    how_to = groups["how_to"]
    expected_ids = [t.id for t in list_how_to_templates()
                    if t.id not in OBSOLETE_HOW_TO_TEMPLATE_IDS]
    assert [e.id for e in how_to.entries] == expected_ids
    for entry in how_to.entries:
        assert entry.category == "how_to"
        assert entry.doc_path and entry.doc_path.endswith(".md")  # backs the mkdocs deep-link


def test_howto_group_excludes_obsolete_web_database_perspective_templates():
    groups = {group.id: group for group in build_template_catalog()}
    how_to_ids = {entry.id for entry in groups["how_to"].entries}
    assert how_to_ids.isdisjoint(OBSOLETE_HOW_TO_TEMPLATE_IDS)


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


@pytest.mark.parametrize("template_id", sorted(OBSOLETE_HOW_TO_TEMPLATE_IDS))
def test_get_template_system_data_obsolete_howto_id_raises(template_id):
    with pytest.raises(KeyError):
        get_template_system_data(template_id)
