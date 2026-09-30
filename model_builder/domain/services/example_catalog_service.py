"""Example-catalog domain service for the first-run picker.

Merges the interface-owned introductory registry with the library's how-to
examples (consumed at runtime via ``efootprint.modeling_examples``) and the
first-class "Start from scratch" option into ordered picker groups. Resolving a
``example_id`` to a raw serialized ``System`` dict also lives here so the load
endpoint stays a thin adapter.

The picker is keyed by *loadable example*, but the how-to documentation is keyed
by *guide* — and several guides can share one scenario (the database and
server-to-server guides both read the ``ecommerce`` example). So each card
carries the how-to guides that walk through it, which keeps every how-to page
referenced without duplicating the scenario across cards.

Pure domain: imports only the library and the interface registry, no Django.
``showcased_concepts`` tokens carried on introductory entries are resolved to
display chips in the presentation layer (which alone owns ``CLASS_UI_CONFIG``).
"""
import json
from dataclasses import dataclass
from pathlib import Path

from efootprint.modeling_examples import (
    get_example as get_how_to_example, list_how_to_guides, list_how_to_examples)

from model_builder.domain.reference_data.modeling_examples import INTRO_EXAMPLES

SCRATCH_ID = "scratch"
UPLOAD_ID = "upload"

# The "Start from scratch" baseline — a truly empty named System.
DEFAULT_SYSTEM_DATA_PATH = Path(__file__).resolve().parents[1] / "reference_data" / "default_system_data.json"


@dataclass(frozen=True)
class CatalogGuide:
    """A how-to documentation page that walks through an example's scenario."""
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
    related_guides: tuple[CatalogGuide, ...] = ()   # how-to pages walking through this example


@dataclass(frozen=True)
class CatalogGroup:
    id: str
    title: str
    entries: tuple[CatalogEntry, ...] = ()


def _guides_by_example_id() -> dict[str, tuple[CatalogGuide, ...]]:
    """Group the library's how-to guides by the example id each one walks through."""
    guides: dict[str, tuple[CatalogGuide, ...]] = {}
    for guide in list_how_to_guides():
        guides[guide.example_id] = guides.get(guide.example_id, ()) + (
            CatalogGuide(guide.name, guide.doc_path),)
    return guides


def build_example_catalog() -> tuple[CatalogGroup, ...]:
    """Ordered picker groups: one merged examples group, then the scratch baseline.

    Introductory examples come first, then the library's deeper how-to examples;
    each card carries the how-to guides that document its scenario.
    """
    guides = _guides_by_example_id()
    introductory = tuple(
        CatalogEntry(t.id, t.name, t.description, t.category, icon=t.icon,
                     showcased_concepts=t.showcased_concepts,
                     related_guides=guides.get(t.id, ()))
        for t in INTRO_EXAMPLES
    )
    how_to = tuple(
        CatalogEntry(t.id, t.name, t.description, t.category, related_guides=guides.get(t.id, ()))
        for t in list_how_to_examples()
    )
    scratch = (
        CatalogEntry(SCRATCH_ID, "Start from scratch",
                     "An empty model. We'll show you where to begin.", "scratch", icon="+"),
        CatalogEntry(UPLOAD_ID, "Load a json file",
                     "Open an existing model exported as .e-f.json.", "upload", icon="↥"),
    )
    return (
        CatalogGroup("examples", "Examples", introductory + how_to),
        CatalogGroup("scratch", "Or", scratch),
    )


def get_example_system_data(example_id: str) -> dict:
    """Resolve a picker ``example_id`` to its raw serialized ``System`` dict.

    Raises ``KeyError`` for an unknown id so the adapter can map it to a 404.
    """
    if example_id == SCRATCH_ID:
        json_path = DEFAULT_SYSTEM_DATA_PATH
    else:
        intro = next((t for t in INTRO_EXAMPLES if t.id == example_id), None)
        json_path = intro.json_path if intro is not None else get_how_to_example(example_id).json_path

    with open(json_path, "r") as file:
        return json.load(file)
