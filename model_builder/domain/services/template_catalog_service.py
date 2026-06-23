"""Template-catalog domain service for the first-run picker.

Merges the interface-owned introductory registry with the library's how-to
templates (consumed at runtime via ``efootprint.modeling_templates``) and the
first-class "Start from scratch" option into ordered picker groups. Resolving a
``template_id`` to a raw serialized ``System`` dict also lives here so the load
endpoint stays a thin adapter.

The picker is keyed by *loadable template*, but the how-to documentation is keyed
by *guide* — and several guides can share one scenario (the database and
server-to-server guides both read the ``ecommerce`` template). So each card
carries the how-to guides that walk through it, which keeps every how-to page
referenced without duplicating the scenario across cards.

Pure domain: imports only the library and the interface registry, no Django.
``showcased_concepts`` tokens carried on introductory entries are resolved to
display chips in the presentation layer (which alone owns ``CLASS_UI_CONFIG``).
"""
import json
from dataclasses import dataclass
from pathlib import Path

from efootprint.modeling_templates import (
    get_template as get_how_to_template, list_how_to_guides, list_how_to_templates)

from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES

SCRATCH_ID = "scratch"

# The "Start from scratch" baseline — a truly empty named System.
DEFAULT_SYSTEM_DATA_PATH = Path(__file__).resolve().parents[1] / "reference_data" / "default_system_data.json"


@dataclass(frozen=True)
class CatalogGuide:
    """A how-to documentation page that walks through a template's scenario."""
    name: str
    doc_path: str  # e.g. "database_modeling.md"; resolved to an mkdocs URL in the presenter


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    name: str
    description: str
    category: str                       # "introductory" | "how_to" | "scratch"
    icon: str | None = None             # introductory + scratch only (library how-to has none)
    showcased_concepts: tuple[str, ...] = ()   # introductory only
    related_guides: tuple[CatalogGuide, ...] = ()   # how-to pages walking through this template


@dataclass(frozen=True)
class CatalogGroup:
    id: str
    title: str
    entries: tuple[CatalogEntry, ...] = ()


def _guides_by_template_id() -> dict[str, tuple[CatalogGuide, ...]]:
    """Group the library's how-to guides by the template id each one walks through."""
    guides: dict[str, tuple[CatalogGuide, ...]] = {}
    for guide in list_how_to_guides():
        guides[guide.template_id] = guides.get(guide.template_id, ()) + (
            CatalogGuide(guide.name, guide.doc_path),)
    return guides


def build_template_catalog() -> tuple[CatalogGroup, ...]:
    """Ordered picker groups: one merged templates group, then the scratch baseline.

    Introductory templates come first, then the library's deeper how-to templates;
    each card carries the how-to guides that document its scenario.
    """
    guides = _guides_by_template_id()
    introductory = tuple(
        CatalogEntry(t.id, t.name, t.description, t.category, icon=t.icon,
                     showcased_concepts=t.showcased_concepts,
                     related_guides=guides.get(t.id, ()))
        for t in INTRO_TEMPLATES
    )
    how_to = tuple(
        CatalogEntry(t.id, t.name, t.description, t.category, related_guides=guides.get(t.id, ()))
        for t in list_how_to_templates()
    )
    scratch = (
        CatalogEntry(SCRATCH_ID, "Start from scratch",
                     "An empty model. We'll show you where to begin.", "scratch", icon="+"),
    )
    return (
        CatalogGroup("templates", "Templates", introductory + how_to),
        CatalogGroup("scratch", "Or", scratch),
    )


def get_template_system_data(template_id: str) -> dict:
    """Resolve a picker ``template_id`` to its raw serialized ``System`` dict.

    Raises ``KeyError`` for an unknown id so the adapter can map it to a 404.
    """
    if template_id == SCRATCH_ID:
        json_path = DEFAULT_SYSTEM_DATA_PATH
    else:
        intro = next((t for t in INTRO_TEMPLATES if t.id == template_id), None)
        json_path = intro.json_path if intro is not None else get_how_to_template(template_id).json_path

    with open(json_path, "r") as file:
        return json.load(file)
