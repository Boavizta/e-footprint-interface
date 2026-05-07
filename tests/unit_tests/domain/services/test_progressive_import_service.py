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


def test_import_system_serializes_orphan_fragment_sources_with_system_to_json(minimal_system_data):
    system_data = deepcopy(minimal_system_data)
    external_api = EcoLogitsGenAIExternalAPI(
        "Test EcoLogits API",
        provider=SourceObject("mistralai"),
        model_name=SourceObject("open-mistral-7b"),
    )
    external_api_data = system_to_json(external_api, save_calculated_attributes=False)
    external_api_id = next(iter(external_api_data["EcoLogitsGenAIExternalAPI"]))

    # Simulate an older/input payload where calculated EcoLogits sources are not in
    # the top-level Sources block. The import service must not duplicate
    # system_to_json's source-hoisting logic to repair this.
    external_api_data["Sources"] = {
        source_id: source_payload
        for source_id, source_payload in external_api_data.get("Sources", {}).items()
        if source_id == "hypothesis"
    }
    _merge_input_fragment(system_data, external_api_data)

    imported = ProgressiveImportService(max_payload_size_mb=30).import_system(system_data)

    assert external_api_id in imported["EcoLogitsGenAIExternalAPI"]
    assert any(
        source_payload["name"] == "Ecologits llm_impacts function"
        for source_payload in imported.get("Sources", {}).values()
    )
    missing_source_refs = (
        set(_source_refs(imported))
        - set((imported.get("Sources") or {}).keys())
        - {"hypothesis", "user_data"}
    )
    assert missing_source_refs == set()

    _, flat_obj_dict, _ = json_to_system(imported, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
    assert external_api_id in flat_obj_dict
