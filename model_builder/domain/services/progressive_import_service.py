"""Service for progressively importing system data with size validation.

This service handles the import of e-footprint system data from JSON,
computing calculated attributes progressively and checking size limits
to fail fast if a model exceeds the maximum allowed size.
"""
from time import perf_counter
from typing import Dict, Any

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
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
        """Import system data with progressive size validation.

        This method:
        1. Parses the JSON into efootprint objects without computing attributes
        2. Monkey-patches each object to track size after computation
        3. Triggers computations, failing fast if size limit exceeded
        4. Returns the fully computed system_data dict

        Args:
            system_data: The raw system data dictionary (already upgraded).

        Returns:
            Computed system data.

        Raises:
            PayloadSizeLimitExceeded: If cumulative JSON size exceeds max_payload_size_mb.
        """
        response_objs, flat_efootprint_objs_dict, upgraded_system_data = json_to_system(
            system_data, launch_system_computations=False,
            efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)

        upgraded_system_data["efootprint_version"] = efootprint_version
        size_tracker = {"json_size": 0}

        self._patch_objects_for_progressive_computation(flat_efootprint_objs_dict, size_tracker)

        system = next(iter(response_objs["System"].values()))
        system.after_init()

        self._remove_progressive_computation_patch(flat_efootprint_objs_dict)

        start = perf_counter()
        final_system_data = self._serialize_system_and_orphans(system, flat_efootprint_objs_dict)
        self._preserve_interface_metadata(upgraded_system_data, final_system_data)
        self._validate_payload_size(final_system_data)
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(f"Serialized final system data in {round(elapsed_ms, 1)} ms.")

        return final_system_data

    def _patch_objects_for_progressive_computation(
            self, flat_efootprint_objs_dict: Dict[str, Any], size_tracker: Dict[str, float]) -> None:
        """Patch all objects to track and validate size after computation.

        Args:
            flat_efootprint_objs_dict: Dictionary of efootprint objects by ID.
            size_tracker: Mutable dict tracking cumulative JSON size.
        """
        for efootprint_object in flat_efootprint_objs_dict.values():
            # Use object.__setattr__ to bypass ModelingObject's custom __setattr__ which triggers computations
            object.__setattr__(
                efootprint_object, "original_compute_calculated_attributes",
                efootprint_object.compute_calculated_attributes)

            def compute_and_store_calculated_attributes(obj=efootprint_object):
                obj.original_compute_calculated_attributes()
                self._compute_json_and_track_size(obj, size_tracker)

            object.__setattr__(
                efootprint_object, "compute_calculated_attributes", compute_and_store_calculated_attributes)

    def _compute_json_and_track_size(
            self, efootprint_object: Any, size_tracker: Dict[str, float]) -> None:
        """Serialize a computed object for progressive size checks.

        Args:
            efootprint_object: The efootprint object to serialize.
            size_tracker: Mutable dict tracking cumulative JSON size.

        Raises:
            PayloadSizeLimitExceeded: If cumulative size exceeds limit.
        """
        class_name = efootprint_object.class_as_simple_str
        # Remove patched method from instance __dict__ before to_json, so it falls back to class method
        del efootprint_object.__dict__["compute_calculated_attributes"]
        del efootprint_object.__dict__["original_compute_calculated_attributes"]

        json_data = efootprint_object.to_json(save_calculated_attributes=True)
        json_data_size = compute_json_size(json_data).size_mb
        size_tracker["json_size"] += json_data_size

        logger.debug(
            f"Computed and serialized calculated attributes for {class_name} (ID: {efootprint_object.id}), "
            f"increasing JSON size by {round(json_data_size, 2)}. "
            f"Total size is now {round(size_tracker['json_size'], 1)} MB")

        self._validate_payload_size(size_mb=size_tracker["json_size"])

        object.__setattr__(efootprint_object, "saved_to_json", True)

    def _remove_progressive_computation_patch(self, flat_efootprint_objs_dict: Dict[str, Any]) -> None:
        """Remove import-only instance attributes before canonical serialization."""
        for efootprint_object in flat_efootprint_objs_dict.values():
            efootprint_object.__dict__.pop("compute_calculated_attributes", None)
            efootprint_object.__dict__.pop("original_compute_calculated_attributes", None)
            efootprint_object.__dict__.pop("saved_to_json", None)

    def _serialize_system_and_orphans(self, system: Any, flat_efootprint_objs_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize the connected system, then preserve objects outside that graph.

        `system_to_json` owns both object serialization and top-level `Sources`
        construction. Keeping final output assembled from `system_to_json`
        fragments avoids duplicating source-hoisting rules here.
        """
        final_system_data = system_to_json(system, save_calculated_attributes=True)
        serialized_object_ids = self._object_ids_in_system_data(final_system_data)

        for efootprint_object in flat_efootprint_objs_dict.values():
            if efootprint_object.id in serialized_object_ids:
                continue
            orphan_data = system_to_json(efootprint_object, save_calculated_attributes=True)
            self._merge_system_json_fragment(final_system_data, orphan_data)
            serialized_object_ids.update(self._object_ids_in_system_data(orphan_data))

        return final_system_data

    @staticmethod
    def _object_ids_in_system_data(system_data: Dict[str, Any]) -> set[str]:
        metadata_keys = {"efootprint_version", "efootprint_interface_version", "Sources", "interface_config"}
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
