"""Presenter turning the domain template catalog into picker-ready view models.

The domain ``build_template_catalog`` returns raw entries carrying
``showcased_concepts`` tokens and the how-to ``related_guides`` that document each
template. Resolving those into display chips (with the class UI label and a
help-drawer target) and mkdocs deep-link URLs needs ``CLASS_UI_CONFIG`` and
``MKDOCS_BASE_URL``, which live in the adapter layer — so it happens here, not in
the domain (constitution §1.1).
"""
from django.conf import settings

from model_builder.adapters.ui_config import CLASS_UI_CONFIG
from model_builder.domain.reference_data.modeling_templates import CONCEPTS
from model_builder.domain.services import build_template_catalog

_CLASS_TOKEN_PREFIX = "{class:"
_CLASS_TOKEN_SUFFIX = "}"


def _resolve_chip(token: str) -> dict:
    """Resolve a ``showcased_concepts`` token to a display chip.

    ``{class:X}`` tokens render with the class UI label and open that class in the
    help drawer (mirroring the ``handle_class`` placeholder). ``CONCEPTS`` keys use
    their own label and optional help target. The registry's ``resolve_concept_token``
    has already validated every token, so lookups here are safe.
    """
    if token.startswith(_CLASS_TOKEN_PREFIX) and token.endswith(_CLASS_TOKEN_SUFFIX):
        class_name = token[len(_CLASS_TOKEN_PREFIX):-len(_CLASS_TOKEN_SUFFIX)]
        label = CLASS_UI_CONFIG.get(class_name, {}).get("label", class_name)
        return {"label": label, "help_class": class_name}
    concept = CONCEPTS[token]
    return {"label": concept.label, "help_class": concept.help_class}


def _doc_url(doc_path: str) -> str:
    slug = doc_path[:-len(".md")] if doc_path.endswith(".md") else doc_path
    return f"{settings.MKDOCS_BASE_URL.rstrip('/')}/{slug}/"


def build_picker_groups() -> list[dict]:
    """Picker view model: ordered groups of cards ready for the template."""
    groups = []
    for group in build_template_catalog():
        entries = []
        for entry in group.entries:
            entries.append({
                "id": entry.id,
                "name": entry.name,
                "description": entry.description,
                "icon": entry.icon,
                "category": entry.category,
                "chips": [_resolve_chip(token) for token in entry.showcased_concepts],
                "guides": [{"name": guide.name, "doc_url": _doc_url(guide.doc_path)}
                           for guide in entry.related_guides],
            })
        groups.append({"id": group.id, "title": group.title, "entries": entries})
    return groups
