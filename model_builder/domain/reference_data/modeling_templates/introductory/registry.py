"""Registry of introductory modeling templates owned by the interface.

These are ready-to-mutate example {class:System}s shown in the first-run template
picker. Interface-owned serialized snapshots live next to this file as
``<id>.json`` and are (re)generated from the Python scenario constructors in
``scripts/intro_template_scenarios/`` via ``scripts/build_intro_templates.py``.
The e-commerce snapshot is library-owned and referenced from
``efootprint.modeling_templates`` so docs and interface cannot drift.

``IntroTemplate`` mirrors the library's ``HowToTemplate`` so the catalog service
can merge both into a single picker. ``showcased_concepts`` are display-only
metadata tokens: each is either a ``{class:X}`` token (resolved against the
efootprint class set, just like the SSOT placeholder handlers) or a key of the
closed ``CONCEPTS`` mapping below, for concepts that map to no single class.
"""
from dataclasses import dataclass
from pathlib import Path

from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.modeling_templates import get_introductory_template

HERE = Path(__file__).parent
CATEGORY = "introductory"


@dataclass(frozen=True)
class Concept:
    """A picker concept chip that maps to no single efootprint class."""
    label: str
    help_class: str | None = None  # optional {class:X} to open in the help drawer


# Closed set of concept tokens. Tokens that *do* map to a class are written as
# ``{class:X}`` in ``showcased_concepts`` instead of being listed here.
CONCEPTS: dict[str, Concept] = {
    "web_service": Concept("Web service"),
    "database": Concept("Database", help_class="Storage"),
    "llm_inference": Concept("LLM inference"),
    "edge_computing": Concept("Edge computing"),
    "device_fleet": Concept("Device fleet"),
}

_CLASS_TOKEN_PREFIX = "{class:"
_CLASS_TOKEN_SUFFIX = "}"


@dataclass(frozen=True)
class IntroTemplate:
    id: str
    name: str
    description: str
    icon: str
    showcased_concepts: tuple[str, ...]
    json_path: Path
    category: str = CATEGORY


def resolve_concept_token(token: str) -> str:
    """Validate a ``showcased_concepts`` token and return its resolved value.

    Returns the bare class name for a ``{class:X}`` token and the concept label
    for a ``CONCEPTS`` key. This is domain-level validation, not display: the
    human-facing chip label (the class UI label, mirroring the help-drawer links)
    is resolved in the presentation layer, which alone owns ``CLASS_UI_CONFIG``.
    Raises ``ValueError`` for an unknown class or concept key, so the registry
    consistency test fails loudly on drift.
    """
    if token.startswith(_CLASS_TOKEN_PREFIX) and token.endswith(_CLASS_TOKEN_SUFFIX):
        class_name = token[len(_CLASS_TOKEN_PREFIX):-len(_CLASS_TOKEN_SUFFIX)]
        if class_name not in ALL_EFOOTPRINT_CLASSES_DICT:
            raise ValueError(f"Unknown class in showcased_concepts token: {token!r}")
        return class_name
    concept = CONCEPTS.get(token)
    if concept is None:
        raise ValueError(f"Unknown showcased_concepts token: {token!r}")
    return concept.label


INTRO_TEMPLATES: tuple[IntroTemplate, ...] = (
    IntroTemplate(
        id="ecommerce",
        name="Classical e-commerce",
        description="A shopping journey served by a web application server calling a database server.",
        icon="🛒",
        showcased_concepts=("web_service", "{class:Server}", "database"),
        json_path=get_introductory_template("ecommerce").json_path,
    ),
    IntroTemplate(
        id="ai_chatbot",
        name="AI chatbot",
        description="A chatbot served by a web app that routes simple and complex prompts to small and large LLM APIs.",
        icon="🤖",
        showcased_concepts=("web_service", "llm_inference", "{class:ExternalAPI}", "{class:Server}"),
        json_path=HERE / "ai_chatbot.json",
    ),
    IntroTemplate(
        id="iot_industrial",
        name="Industrial IoT",
        description="A fleet of connected edge devices running recurrent on-device workloads — "
                    "lands with edge modeling already active.",
        icon="📟",
        showcased_concepts=("edge_computing", "{class:EdgeComputer}", "device_fleet"),
        json_path=HERE / "iot_industrial.json",
    ),
)
