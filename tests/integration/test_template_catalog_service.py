"""Integration tests for the first-run template-catalog service.

Exercises the merge of the interface-owned introductory registry with the
library's how-to public API (``list_how_to_templates`` / ``get_template``) and the
``template_id`` → serialized-System resolution that backs the load endpoint. Runs
pure domain — no Django scaffolding (constitution §1.1).
"""
import pytest
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.modeling_templates import list_how_to_templates

from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES
from model_builder.domain.services import (
    SCRATCH_ID, build_template_catalog, get_template_system_data)


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
    assert [e.id for e in how_to.entries] == [t.id for t in list_how_to_templates()]
    for entry in how_to.entries:
        assert entry.category == "how_to"
        assert entry.doc_path and entry.doc_path.endswith(".md")  # backs the mkdocs deep-link


def test_scratch_group_is_the_empty_baseline_sentinel():
    groups = {group.id: group for group in build_template_catalog()}
    scratch_entries = groups["scratch"].entries
    assert [e.id for e in scratch_entries] == [SCRATCH_ID]
    assert scratch_entries[0].category == "scratch"


@pytest.mark.parametrize("template_id", ["scratch", "ecommerce", "ai_chatbot", "iot_industrial",
                                         "database_modeling", "machine_learning_workflow",
                                         "server_to_server_interaction"])
def test_get_template_system_data_resolves_a_loadable_system(template_id):
    system_data = get_template_system_data(template_id)
    assert "System" in system_data
    # Exercise the resolved JSON through the library loader so a broken path/payload fails here.
    class_obj_dict, _, _ = json_to_system(system_data, launch_system_computations=False)
    assert class_obj_dict["System"]


def test_get_template_system_data_unknown_id_raises():
    with pytest.raises(KeyError):
        get_template_system_data("not-a-template")
