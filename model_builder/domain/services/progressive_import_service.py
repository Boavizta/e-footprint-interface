"""Service for progressively importing system data with size validation.

This service handles the import of e-footprint system data from JSON,
computing calculated attributes progressively and checking size limits
to fail fast if a model exceeds the maximum allowed size.
"""
from copy import deepcopy
from typing import Dict, Any

from efootprint.api_utils.json_to_system import json_to_system
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
        copied_system_data = deepcopy(system_data)
        response_objs, flat_efootprint_objs_dict = json_to_system(
            copied_system_data, launch_system_computations=False,
            efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)

        copied_system_data["efootprint_version"] = efootprint_version
        size_tracker = {"json_size": 0}

        self._patch_objects_for_progressive_computation(
            flat_efootprint_objs_dict, copied_system_data, size_tracker)

        system = next(iter(response_objs["System"].values()))
        system.after_init()

        self._compute_remaining_objects(flat_efootprint_objs_dict, copied_system_data, size_tracker)

        # Reserialize all objects to ensure final calculation graph is captured
        logger.info("Reserializing all objects to finalize system data.")
        for efootprint_object in flat_efootprint_objs_dict.values():
            del efootprint_object.__dict__["saved_to_json"]
            copied_system_data[efootprint_object.class_as_simple_str][efootprint_object.id] = \
                efootprint_object.to_json(save_calculated_attributes=True)
        logger.info("Reserialized all objects to finalize system data.")

        return copied_system_data

    def _patch_objects_for_progressive_computation(
            self, flat_efootprint_objs_dict: Dict[str, Any], system_data: Dict[str, Any],
            size_tracker: Dict[str, float]) -> None:
        """Patch all objects to track and validate size after computation.

        Args:
            flat_efootprint_objs_dict: Dictionary of efootprint objects by ID.
            system_data: The system data dict to populate.
            size_tracker: Mutable dict tracking cumulative JSON size.
        """
        for efootprint_object in flat_efootprint_objs_dict.values():
            # Use object.__setattr__ to bypass ModelingObject's custom __setattr__ which triggers computations
            object.__setattr__(
                efootprint_object, "original_compute_calculated_attributes",
                efootprint_object.compute_calculated_attributes)

            def compute_and_store_calculated_attributes(obj=efootprint_object):
                obj.original_compute_calculated_attributes()
                self._compute_json_and_save_to_dict(obj, system_data, size_tracker)

            object.__setattr__(
                efootprint_object, "compute_calculated_attributes", compute_and_store_calculated_attributes)

    def _compute_json_and_save_to_dict(
            self, efootprint_object: Any, system_data: Dict[str, Any],
            size_tracker: Dict[str, float]) -> None:
        """Compute JSON for an object and save it, checking size limits.

        Args:
            efootprint_object: The efootprint object to serialize.
            system_data: The system data dict to populate.
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
            f"Computed and stored calculated attributes for {class_name} (ID: {efootprint_object.id}), "
            f"increasing JSON size by {round(json_data_size, 2)}. "
            f"Total size is now {round(size_tracker['json_size'], 1)} MB")

        if size_tracker["json_size"] > self.max_payload_size_mb:
            raise PayloadSizeLimitExceeded(size_tracker["json_size"], self.max_payload_size_mb)

        system_data[class_name][efootprint_object.id] = json_data
        object.__setattr__(efootprint_object, "saved_to_json", True)

    def _compute_remaining_objects(
            self, flat_efootprint_objs_dict: Dict[str, Any], system_data: Dict[str, Any],
            size_tracker: Dict[str, float]) -> None:
        """Compute and save any objects not yet processed.

        Some objects may not have their compute_calculated_attributes called
        during system.after_init() (e.g., orphaned objects). This ensures
        all objects are processed.

        Args:
            flat_efootprint_objs_dict: Dictionary of efootprint objects by ID.
            system_data: The system data dict to populate.
            size_tracker: Mutable dict tracking cumulative JSON size.
        """
        for efootprint_object in flat_efootprint_objs_dict.values():
            if not getattr(efootprint_object, "saved_to_json", False):
                self._compute_json_and_save_to_dict(efootprint_object, system_data, size_tracker)
