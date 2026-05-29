"""Introductory modeling templates (interface-owned)."""
from model_builder.domain.reference_data.modeling_templates.introductory.registry import (
    CONCEPTS,
    Concept,
    IntroTemplate,
    INTRO_TEMPLATES,
    resolve_concept_token,
)

__all__ = ["CONCEPTS", "Concept", "IntroTemplate", "INTRO_TEMPLATES", "resolve_concept_token"]
