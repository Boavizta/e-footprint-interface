"""Interface-owned modeling-template registries.

Aggregates the introductory and "other" registries. How-to templates are *not*
re-exported here — they are consumed at runtime from the library's public API
(``efootprint.modeling_templates.list_how_to_templates``). The catalog service
(Sub-phase B) merges all three categories for the picker.
"""
from model_builder.domain.reference_data.modeling_templates.introductory.registry import (
    CONCEPTS,
    Concept,
    IntroTemplate,
    INTRO_TEMPLATES,
    resolve_concept_token,
)
from model_builder.domain.reference_data.modeling_templates.other.registry import OTHER_TEMPLATES

__all__ = [
    "CONCEPTS",
    "Concept",
    "IntroTemplate",
    "INTRO_TEMPLATES",
    "OTHER_TEMPLATES",
    "resolve_concept_token",
]
