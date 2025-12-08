"""Snapshot testing utilities for web entity form structures.

These utilities allow comparing generated form structures against reference JSON files,
making it easy to detect regressions in form generation.
"""
import json
import os

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "class_structures")


def assert_json_equal(json1, json2, path=""):
    """
    Recursively asserts that two JSON-like Python structures are equal,
    ignoring dictionary key order and list element order.

    Raises an AssertionError if a mismatch is found.
    """
    if type(json1) != type(json2):
        raise AssertionError(f"Type mismatch at {path or 'root'}: {type(json1).__name__} != {type(json2).__name__}")

    if isinstance(json1, dict):
        keys1 = set(json1.keys())
        keys2 = set(json2.keys())
        if keys1 != keys2:
            raise AssertionError(f"Key mismatch at {path or 'root'}: {keys1} != {keys2}")
        for key in keys1:
            assert_json_equal(json1[key], json2[key], path + f".{key}")
    elif isinstance(json1, list):
        unmatched = list(json2)
        for i, item1 in enumerate(json1):
            for j, item2 in enumerate(unmatched):
                try:
                    assert_json_equal(item1, item2, path + f"[{i}]")
                    unmatched.pop(j)
                    break
                except AssertionError:
                    continue
            else:
                raise AssertionError(f"No match found for list element at {path}[{i}]: {item1}")
        if unmatched:
            raise AssertionError(f"Extra elements in second list at {path}: {unmatched}")
    else:
        if json1 != json2:
            raise AssertionError(f"Value mismatch at {path or 'root'}: {json1} != {json2}")


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

        assert_json_equal(tmp_structure, ref_structure)

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
        model_web: ModelWeb instance to pass to generate_object_creation_context
        object_type: Optional object_type parameter for generate_object_creation_context
    """
    web_class_name = web_class.__name__

    context = web_class.generate_object_creation_context(model_web=model_web, object_type=object_type)

    form_sections = context["form_sections"]
    assert_structure_matches_snapshot(form_sections, f"{web_class_name}_creation_structure")

    dynamic_data = context.get("dynamic_form_data")
    if dynamic_data is not None:
        assert_structure_matches_snapshot(dynamic_data, f"{web_class_name}_creation_dynamic_data")
