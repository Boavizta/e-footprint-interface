from copy import deepcopy

from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.external_apis.ecologits.ecologits_external_api import EcoLogitsGenAIExternalAPI

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.services.progressive_import_service import ProgressiveImportService


def _merge_input_fragment(target: dict, fragment: dict) -> None:
    for key, value in fragment.items():
        if key == "efootprint_version":
            continue
        if isinstance(value, dict):
            target.setdefault(key, {}).update(value)


def _source_refs(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "Sources":
                continue
            if key == "source" and isinstance(value, str):
                yield value
            yield from _source_refs(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _source_refs(value)


def _modeling_object_ids(payload):
    metadata_keys = {"efootprint_version", "efootprint_interface_version", "Sources", "interface_config",
                     "calculation_graph"}
    return {
        object_id
        for class_key, class_dict in payload.items()
        if class_key not in metadata_keys and isinstance(class_dict, dict)
        for object_id in class_dict
    }


def test_import_system_delegates_source_integrity_to_system_to_json(minimal_system_data):
    system_data = deepcopy(minimal_system_data)
    external_api = EcoLogitsGenAIExternalAPI(
        "Test EcoLogits API",
        provider=SourceObject("mistralai"),
        model_name=SourceObject("open-mistral-7b"),
    )
    external_api_data = system_to_json(external_api, save_computed_state=False)
    external_api_id = next(iter(external_api_data["EcoLogitsGenAIExternalAPI"]))

    # Simulate an older/input payload whose top-level Sources block is stripped. The import service
    # must delegate source handling to system_to_json rather than reimplementing it, so the imported
    # payload keeps every referenced source (no dangling refs) and re-adds no orphan.
    external_api_data["Sources"] = {
        source_id: source_payload
        for source_id, source_payload in external_api_data.get("Sources", {}).items()
        if source_id == "hypothesis"
    }
    _merge_input_fragment(system_data, external_api_data)

    imported = ProgressiveImportService(max_payload_size_mb=30).import_system(system_data)

    assert external_api_id in imported["EcoLogitsGenAIExternalAPI"]
    missing_source_refs = (
        set(_source_refs(imported))
        - set((imported.get("Sources") or {}).keys())
        - _modeling_object_ids(imported)
        - {"hypothesis", "user_data"}
    )
    assert missing_source_refs == set()
    # Pure computed-attribute provenance (re-attached deterministically on recompute) is not
    # referenced by any serialized value, so system_to_json must not persist it as an orphan.
    assert all(
        source_payload["name"] != "Ecologits llm_impacts function"
        for source_payload in imported.get("Sources", {}).values()
    )

    _, flat_obj_dict, _ = json_to_system(imported, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
    assert external_api_id in flat_obj_dict
