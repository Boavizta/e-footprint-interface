"""Service for importing system data with size validation.

This service handles the import of e-footprint system data from JSON: it loads the model, computes it
(the connected graph plus any orphan objects), serializes it under the minimal contract, and checks
the resulting payload against the size limit.
"""
from time import perf_counter
from typing import Dict, Any

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import (
    CALCULATION_GRAPH_KEY, calculation_graph_section, system_to_json)
from efootprint.logger import logger
from efootprint import __version__ as efootprint_version

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.exceptions import PayloadSizeLimitExceeded


class ProgressiveImportService:
    """Service for importing system data with progressive size validation.

    This service imports e-footprint system data from JSON, computing calculated
    attributes one object at a time and checking the cumulative size after each.
    This allows failing fast if a model exceeds the maximum allowed size, rather
    than computing everything first and failing at session save time.
    """

    def __init__(self, max_payload_size_mb: float):
        """Initialize the service with size constraints.

        Args:
            max_payload_size_mb: Maximum allowed payload size in megabytes.
        """
        self.max_payload_size_mb = max_payload_size_mb

    def import_system(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import system data, compute it, and return the canonical (with-computed-state) payload.

        Loads without computing (the pull engine defers all computation), then pulls the whole model —
        the connected graph via the system, plus any orphan objects being imported so their computed
        sources are attached and hoisted — serializes with the computed state, and checks the final
        payload against the size budget. The minimal serialization contract keeps that payload small,
        so one size check on the final payload replaces the former per-object progressive tracking.

        Args:
            system_data: The raw system data dictionary (already upgraded).

        Returns:
            Computed system data.

        Raises:
            PayloadSizeLimitExceeded: If the final payload exceeds max_payload_size_mb.
        """
        response_objs, flat_efootprint_objs_dict, upgraded_system_data = json_to_system(
            system_data, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        upgraded_system_data["efootprint_version"] = efootprint_version

        system = next(iter(response_objs["System"].values()))
        system.after_init()

        start = perf_counter()
        final_system_data = self._serialize_system_and_orphans(system, flat_efootprint_objs_dict)
        self._preserve_interface_metadata(upgraded_system_data, final_system_data)
        self._validate_payload_size(final_system_data)
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(f"Serialized final system data in {round(elapsed_ms, 1)} ms.")

        return final_system_data

    def _serialize_system_and_orphans(self, system: Any, flat_efootprint_objs_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize the connected system, then preserve objects outside that graph.

        `system_to_json` owns both object serialization and top-level `Sources` construction. Keeping
        final output assembled from `system_to_json` fragments avoids duplicating source-hoisting rules
        here. The per-fragment calculation-graph sections are dropped (they are addressed relative to
        their own fragment) and one graph over every serialized object is rebuilt at the end, so an
        exact-version reload trusts the stored values.
        """
        final_system_data = system_to_json(system, save_computed_state=True)
        final_system_data.pop(CALCULATION_GRAPH_KEY, None)
        serialized_object_ids = self._object_ids_in_system_data(final_system_data)

        for efootprint_object in flat_efootprint_objs_dict.values():
            if efootprint_object.id in serialized_object_ids:
                continue
            # Orphans are not reached by the system-wide pull, so compute them individually here to
            # attach their computed sources before serialization hoists them into the Sources block.
            efootprint_object.after_init()
            orphan_data = system_to_json(efootprint_object, save_computed_state=True)
            orphan_data.pop(CALCULATION_GRAPH_KEY, None)
            self._merge_system_json_fragment(final_system_data, orphan_data)
            serialized_object_ids.update(self._object_ids_in_system_data(orphan_data))

        final_system_data[CALCULATION_GRAPH_KEY] = calculation_graph_section(
            list(flat_efootprint_objs_dict.values()))
        return final_system_data

    @staticmethod
    def _object_ids_in_system_data(system_data: Dict[str, Any]) -> set[str]:
        metadata_keys = {"efootprint_version", "efootprint_interface_version", "Sources", "interface_config",
                         CALCULATION_GRAPH_KEY}
        return {
            object_id
            for class_key, class_dict in system_data.items()
            if class_key not in metadata_keys and isinstance(class_dict, dict)
            for object_id in class_dict
        }

    @staticmethod
    def _merge_system_json_fragment(target: Dict[str, Any], fragment: Dict[str, Any]) -> None:
        for top_level_key, fragment_value in fragment.items():
            if not isinstance(fragment_value, dict):
                existing_value = target.get(top_level_key)
                if existing_value is not None and existing_value != fragment_value:
                    raise ValueError(
                        f"Conflicting top-level payload for `{top_level_key}`.")
                target[top_level_key] = fragment_value
                continue

            target_value = target.setdefault(top_level_key, {})
            if not isinstance(target_value, dict):
                raise ValueError(
                    f"Cannot merge dict payload into non-dict top-level key `{top_level_key}`.")

            for nested_key, nested_payload in fragment_value.items():
                existing_payload = target_value.get(nested_key)
                if existing_payload is not None and existing_payload != nested_payload:
                    raise ValueError(
                        f"Conflicting nested payload for `{top_level_key}.{nested_key}`.")
                target_value[nested_key] = nested_payload

    @staticmethod
    def _preserve_interface_metadata(source: Dict[str, Any], target: Dict[str, Any]) -> None:
        for metadata_key in ("interface_config", "efootprint_interface_version"):
            if metadata_key in source:
                target[metadata_key] = source[metadata_key]

    def _validate_payload_size(self, system_data: Dict[str, Any] | None = None, size_mb: float | None = None) -> None:
        if size_mb is None:
            if system_data is None:
                raise ValueError("Either system_data or size_mb must be provided for payload-size validation.")
            size_mb = compute_json_size(system_data).size_mb
        if size_mb > self.max_payload_size_mb:
            raise PayloadSizeLimitExceeded(size_mb, self.max_payload_size_mb)
