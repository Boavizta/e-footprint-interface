"""(Re)generate the introductory template JSONs from their Python scenario constructors.

The committed source of truth is the ``build_system()`` constructors under
``scripts/intro_template_scenarios/``; the JSONs next to the introductory
registry are derived artifacts. Re-run this whenever a constructor or the
library serialization schema changes:

    python -m scripts.build_intro_templates

Object ids are pinned to readable, name-based slugs (rather than per-process
uuids) so the committed JSON is reviewable and stable across regenerations —
hence the ``_use_name_as_id`` flips, which must happen before any other
efootprint import (mirrors the library's how-to ``_authoring`` package).
"""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

ModelingObject._use_name_as_id = True
Source._use_name_as_id = True

from efootprint.api_utils.system_to_json import system_to_json  # noqa: E402

from model_builder.domain.reference_data.modeling_templates.introductory.registry import (  # noqa: E402
    INTRO_TEMPLATES,
)
from scripts.intro_template_scenarios import ai_chatbot, ecommerce, iot_industrial  # noqa: E402

BUILDERS = {
    "ecommerce": ecommerce.build_system,
    "ai_chatbot": ai_chatbot.build_system,
    "iot_industrial": iot_industrial.build_system,
}


def main() -> None:
    templates_by_id = {tpl.id: tpl for tpl in INTRO_TEMPLATES}
    missing = set(templates_by_id) ^ set(BUILDERS)
    if missing:
        raise SystemExit(
            f"Mismatch between registry ids and scenario builders: {sorted(missing)}. "
            f"Every introductory template must have exactly one build_system().")

    assert ModelingObject._use_name_as_id and Source._use_name_as_id, (
        "Build must run with name-based ids; the _use_name_as_id flips must precede efootprint imports.")

    for template_id, build_system in BUILDERS.items():
        target = templates_by_id[template_id].json_path
        system_to_json(build_system(), save_calculated_attributes=False, output_filepath=str(target))
        print(f"Wrote {target}")


if __name__ == "__main__":
    main()
