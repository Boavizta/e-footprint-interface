"""Metadata-consistency tests for the introductory template registry.

Mirrors the library's ``HowToTemplate`` validation: every template's
``json_path`` exists, ``category`` is valid, ``icon`` is present, and every
``showcased_concepts`` token resolves (through ``{class:X}`` validation or the
closed ``CONCEPTS`` mapping). Fails loudly on drift.
"""
import inspect
import json

import pytest

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.builders.timeseries import (
    ExplainableHourlyQuantitiesFromFormInputs,
    ExplainableRecurrentQuantitiesFromConstant,
)
from efootprint.modeling_templates import get_introductory_template
from model_builder.domain.reference_data.modeling_templates import (
    CONCEPTS,
    INTRO_TEMPLATES,
    resolve_concept_token,
)
from model_builder.domain.reference_data.modeling_templates.introductory.registry import CATEGORY

_params = pytest.mark.parametrize("tpl", INTRO_TEMPLATES, ids=lambda t: t.id)


def test_at_least_three_introductory_templates():
    # The spec ships e-commerce, AI chatbot and industrial IoT.
    assert {tpl.id for tpl in INTRO_TEMPLATES} >= {"ecommerce", "ai_chatbot", "iot_industrial"}


@_params
def test_json_path_exists(tpl):
    assert tpl.json_path.is_file(), f"{tpl.json_path} does not exist"


@_params
def test_template_input_timeseries_are_editable_builders(tpl):
    with open(tpl.json_path) as f:
        class_obj_dict, _, _ = json_to_system(json.load(f))
    system = next(iter(class_obj_dict["System"].values()))

    checked = []
    for obj in [system, *system.all_linked_objects]:
        obj = obj._value if isinstance(obj, ContextualModelingObjectAttribute) else obj
        init_params = inspect.signature(type(obj).__init__).parameters
        for attr_name in init_params:
            if attr_name in ("self", "name") or not hasattr(obj, attr_name):
                continue
            value = getattr(obj, attr_name)
            if isinstance(value, ExplainableHourlyQuantities):
                assert isinstance(value, ExplainableHourlyQuantitiesFromFormInputs), (
                    f"{tpl.id}: {type(obj).__name__}.{attr_name} on {obj.name!r} must use "
                    "ExplainableHourlyQuantitiesFromFormInputs so it is editable in the interface.")
                checked.append((obj, attr_name))
            elif isinstance(value, ExplainableRecurrentQuantities):
                assert isinstance(value, ExplainableRecurrentQuantitiesFromConstant), (
                    f"{tpl.id}: {type(obj).__name__}.{attr_name} on {obj.name!r} must use "
                    "ExplainableRecurrentQuantitiesFromConstant so it is editable in the interface.")
                checked.append((obj, attr_name))
    assert checked, f"{tpl.id}: expected at least one input timeseries to validate."


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
