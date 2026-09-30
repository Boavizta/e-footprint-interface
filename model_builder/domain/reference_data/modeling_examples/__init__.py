"""Interface-owned modeling-example registries.

Exposes the introductory registry. How-to examples are *not* re-exported here —
they are consumed at runtime from the library's public API
(``efootprint.modeling_examples.list_how_to_examples``). The catalog service
(Sub-phase B) merges introductory + how-to for the picker.
"""
from model_builder.domain.reference_data.modeling_examples.introductory.registry import (
    CONCEPTS,
    Concept,
    IntroExample,
    INTRO_EXAMPLES,
    resolve_concept_token,
)

__all__ = [
    "CONCEPTS",
    "Concept",
    "IntroExample",
    "INTRO_EXAMPLES",
    "resolve_concept_token",
]
