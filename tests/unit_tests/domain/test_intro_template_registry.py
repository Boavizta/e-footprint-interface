"""Metadata-consistency tests for the introductory template registry.

Mirrors the library's ``HowToTemplate`` validation: every template's
``json_path`` exists, ``category`` is valid, ``icon`` is present, and every
``showcased_concepts`` token resolves (through ``{class:X}`` validation or the
closed ``CONCEPTS`` mapping). Fails loudly on drift.
"""
import pytest

from model_builder.domain.reference_data.modeling_templates import (
    CONCEPTS,
    INTRO_TEMPLATES,
    resolve_concept_token,
)
from model_builder.domain.reference_data.modeling_templates.introductory.registry import CATEGORY
from efootprint.modeling_templates import get_introductory_template

_params = pytest.mark.parametrize("tpl", INTRO_TEMPLATES, ids=lambda t: t.id)


def test_at_least_three_introductory_templates():
    # The spec ships e-commerce, AI chatbot and industrial IoT.
    assert {tpl.id for tpl in INTRO_TEMPLATES} >= {"ecommerce", "ai_chatbot", "iot_industrial"}


@_params
def test_json_path_exists(tpl):
    assert tpl.json_path.is_file(), f"{tpl.json_path} does not exist"


@_params
def test_metadata_fields_present(tpl):
    for field_name in ("id", "name", "description", "icon"):
        value = getattr(tpl, field_name)
        assert isinstance(value, str) and value.strip(), f"{tpl.id}.{field_name} must be a non-empty string"
    assert tpl.category == CATEGORY, f"{tpl.id} category must be {CATEGORY!r}"


@_params
def test_showcased_concepts_resolve(tpl):
    assert tpl.showcased_concepts, f"{tpl.id} must showcase at least one concept"
    for token in tpl.showcased_concepts:
        # Raises ValueError on an unknown class or concept key.
        assert resolve_concept_token(token)


def test_template_ids_unique():
    ids = [tpl.id for tpl in INTRO_TEMPLATES]
    assert len(ids) == len(set(ids)), f"Duplicate introductory template ids: {ids}"


def test_ecommerce_uses_library_owned_template_json():
    ecommerce = next(tpl for tpl in INTRO_TEMPLATES if tpl.id == "ecommerce")
    assert ecommerce.json_path == get_introductory_template("ecommerce").json_path


def test_resolve_concept_token_rejects_unknown_class():
    with pytest.raises(ValueError):
        resolve_concept_token("{class:NotARealEfootprintClass}")


def test_resolve_concept_token_rejects_unknown_concept():
    with pytest.raises(ValueError):
        resolve_concept_token("definitely_not_a_concept")


def test_concepts_have_labels_and_valid_help_classes():
    for token, concept in CONCEPTS.items():
        assert concept.label.strip(), f"Concept {token!r} must have a non-empty label"
        if concept.help_class is not None:
            # A help_class must point at a real efootprint class.
            assert resolve_concept_token(f"{{class:{concept.help_class}}}")
