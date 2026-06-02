"""Template-catalog domain service for the first-run picker.

Merges the interface-owned introductory registry with the library's how-to
templates (consumed at runtime via ``efootprint.modeling_templates``) and the
first-class "Start from scratch" option into ordered category groups. Resolving a
``template_id`` to a raw serialized ``System`` dict also lives here so the load
endpoint stays a thin adapter.

Pure domain: imports only the library and the interface registry, no Django.
``showcased_concepts`` tokens carried on introductory entries are resolved to
display chips in the presentation layer (which alone owns ``CLASS_UI_CONFIG``).
"""
import json
from dataclasses import dataclass
from pathlib import Path

from efootprint.modeling_templates import get_template as get_how_to_template, list_how_to_templates

from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES

SCRATCH_ID = "scratch"
OBSOLETE_HOW_TO_TEMPLATE_IDS = frozenset({
    "database_modeling",
    "server_to_server_interaction",
})

# The "Start from scratch" baseline — a truly empty named System (Task 1).
DEFAULT_SYSTEM_DATA_PATH = Path(__file__).resolve().parents[1] / "reference_data" / "default_system_data.json"


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    name: str
    description: str
    category: str                       # "introductory" | "how_to" | "scratch"
    icon: str | None = None             # introductory + scratch only (library how-to has none)
    showcased_concepts: tuple[str, ...] = ()   # introductory only
    doc_path: str | None = None         # how-to only, e.g. "database_modeling.md"


@dataclass(frozen=True)
class CatalogGroup:
    id: str
    title: str
    entries: tuple[CatalogEntry, ...] = ()


def build_template_catalog() -> tuple[CatalogGroup, ...]:
    """Ordered picker groups: introductory templates, library how-to guides, then scratch."""
    introductory = tuple(
        CatalogEntry(t.id, t.name, t.description, t.category, icon=t.icon,
                     showcased_concepts=t.showcased_concepts)
        for t in INTRO_TEMPLATES
    )
    how_to = tuple(
        CatalogEntry(t.id, t.name, t.description, t.category, doc_path=t.doc_path)
        for t in list_how_to_templates()
        if t.id not in OBSOLETE_HOW_TO_TEMPLATE_IDS
    )
    scratch = (
        CatalogEntry(SCRATCH_ID, "Start from scratch",
                     "An empty model. We'll show you where to begin.", "scratch", icon="+"),
    )
    return (
        CatalogGroup("introductory", "Start here", introductory),
        CatalogGroup("how_to", "Deep-dive examples (from the docs)", how_to),
        CatalogGroup("scratch", "Or", scratch),
    )


def get_template_system_data(template_id: str) -> dict:
    """Resolve a picker ``template_id`` to its raw serialized ``System`` dict.

    Raises ``KeyError`` for an unknown id so the adapter can map it to a 404.
    """
    if template_id == SCRATCH_ID:
        json_path = DEFAULT_SYSTEM_DATA_PATH
    elif template_id in OBSOLETE_HOW_TO_TEMPLATE_IDS:
        raise KeyError(template_id)
    else:
        intro = next((t for t in INTRO_TEMPLATES if t.id == template_id), None)
        if intro is not None:
            json_path = intro.json_path
        else:
            json_path = get_how_to_template(template_id).json_path

    with open(json_path, "r") as file:
        return json.load(file)
