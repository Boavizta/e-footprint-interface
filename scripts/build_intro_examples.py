"""(Re)generate the introductory example JSONs from their Python scenario constructors.

The committed source of truth for interface-owned examples is the
``build_system()`` constructors under ``scripts/intro_example_scenarios/``; the
local JSONs next to the introductory registry are derived artifacts. Re-run this
whenever a constructor or the library serialization schema changes:

    python -m scripts.build_intro_examples

Object ids are pinned to readable, name-based slugs (rather than per-process
uuids) so the committed JSON is reviewable and stable across regenerations —
hence the ``_use_name_as_id`` flips, which must happen before any other
efootprint import (mirrors the library's how-to ``_authoring`` package).
"""
from pathlib import Path

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

ModelingObject._use_name_as_id = True
Source._use_name_as_id = True

from efootprint.api_utils.system_to_json import system_to_json  # noqa: E402

from model_builder.domain.reference_data.modeling_examples.introductory.registry import (  # noqa: E402
    INTRO_EXAMPLES,
)
from scripts.intro_example_scenarios import ai_chatbot, genai_video, iot_industrial  # noqa: E402

BUILDERS = {
    "ai_chatbot": ai_chatbot.build_system,
    "genai_video": genai_video.build_system,
    "iot_industrial": iot_industrial.build_system,
}

LOCAL_EXAMPLE_DIR = (
    Path(__file__).resolve().parents[1] /
    "model_builder/domain/reference_data/modeling_examples/introductory"
)


def main() -> None:
    local_examples_by_id = {
        example.id: example for example in INTRO_EXAMPLES
        if example.json_path.parent == LOCAL_EXAMPLE_DIR
    }
    missing = set(local_examples_by_id) ^ set(BUILDERS)
    if missing:
        raise SystemExit(
            f"Mismatch between registry ids and scenario builders: {sorted(missing)}. "
            f"Every interface-owned introductory example must have exactly one build_system().")

    assert ModelingObject._use_name_as_id and Source._use_name_as_id, (
        "Build must run with name-based ids; the _use_name_as_id flips must precede efootprint imports.")

    for example_id, build_system in BUILDERS.items():
        target = local_examples_by_id[example_id].json_path
        system_to_json(build_system(), save_computed_state=False, output_filepath=str(target))
        print(f"Wrote {target}")


if __name__ == "__main__":
    main()
