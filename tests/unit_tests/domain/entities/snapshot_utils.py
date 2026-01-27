"""Snapshot testing utilities for web entity form structures.

These utilities allow comparing generated form structures against reference JSON files,
making it easy to detect regressions in form generation.
"""
import json
import os

from tests.utils import assert_dicts_equal

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "class_structures")


def assert_structure_matches_snapshot(structure: dict, snapshot_name: str, update_snapshot: bool = False):
    """Assert a form structure matches its reference snapshot.

    Args:
        structure: The generated structure dict to test
        snapshot_name: Name of the snapshot file (without .json extension)
        update_snapshot: If True, update the reference file instead of comparing

    Example:
        context = ServerWeb.generate_object_creation_context(model_web)
        assert_structure_matches_snapshot(context["form_sections"], "ServerWeb_creation_structure")
    """
    ref_path = os.path.join(SNAPSHOT_DIR, f"{snapshot_name}.json")
    tmp_path = os.path.join(SNAPSHOT_DIR, f"{snapshot_name}_tmp.json")

    # Write current structure to temp file
    with open(tmp_path, "w") as f:
        json.dump(structure, f, indent=4)

    if update_snapshot:
        # Update reference file
        os.replace(tmp_path, ref_path)
        return

    try:
        with open(ref_path, "r") as ref_file:
            ref_structure = json.load(ref_file)

        with open(tmp_path, "r") as tmp_file:
            tmp_structure = json.load(tmp_file)

        assert_dicts_equal(tmp_structure, ref_structure)

        # Clean up temp file on success
        os.remove(tmp_path)
    except FileNotFoundError:
        raise AssertionError(
            f"Reference snapshot not found: {ref_path}\n"
            f"Run with update_snapshot=True to create it, or copy {tmp_path} to {ref_path}"
        )
    except AssertionError:
        # Keep temp file for debugging on failure
        raise


def assert_creation_context_matches_snapshot(web_class, model_web, object_type: str = None):
    """Assert a web class's creation context matches its snapshot.

    Args:
        web_class: The web class (e.g., ServerWeb)
        model_web: ModelWeb instance to pass to FormContextBuilder
        object_type: Optional object_type parameter for build_creation_context
    """
    from model_builder.adapters.forms.form_context_builder import FormContextBuilder

    web_class_name = web_class.__name__
    if object_type is None:
        # Infer object_type from web_class name if not provided
        object_type = web_class_name.replace("Web", "")

    form_builder = FormContextBuilder(model_web)
    context = form_builder.build_creation_context(web_class, object_type)

    form_sections = context["form_sections"]
    assert_structure_matches_snapshot(form_sections, f"{web_class_name}_creation_structure")

    dynamic_data = context.get("dynamic_form_data")
    if dynamic_data is not None:
        assert_structure_matches_snapshot(dynamic_data, f"{web_class_name}_creation_dynamic_data")
