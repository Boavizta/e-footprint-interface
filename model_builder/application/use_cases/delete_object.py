"""Use case for deleting modeling objects.

This module contains the business logic for object deletion, separated from
HTTP/presentation concerns.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.oob_region import OobRegion


@dataclass
class DeleteObjectInput:
    """Input data for object deletion."""
    object_id: str
    form_data: Optional[Dict[str, Any]] = None  # For list removal operations


@dataclass
class DeleteCheckResult:
    """Result of checking if an object can be deleted."""
    can_delete: bool
    is_list_deletion: bool = False
    blocking_containers: List[str] = field(default_factory=list)
    has_accordion_children: bool = False
    accordion_children_count: int = 0
    accordion_children_class_type: str = ""  # Raw class type for presenter to resolve label
    is_mirrored: bool = False
    mirrored_count: int = 0


@dataclass
class DeleteObjectOutput:
    """Output data from object deletion."""
    deleted_object_name: str
    deleted_object_type: str
    was_list_deletion: bool = False
    # For list deletions, we need the edited containers to generate HTML in presenter
    edited_containers: List[Any] = field(default_factory=list)
    oob_regions: List[OobRegion] = field(default_factory=list)


class DeleteObjectUseCase:
    """Use case for deleting a modeling object.

    This class encapsulates the business logic for deleting objects,
    including handling list container removals.
    """

    def __init__(self, model_web: ModelWeb):
        """Initialize with a loaded web model.

        Args:
            model_web: web model loaded with system data.
        """
        self.model_web = model_web

    def check_can_delete(self, object_id: str) -> DeleteCheckResult:
        """Check if an object can be deleted and gather context for confirmation.

        Args:
            object_id: The ID of the object to check.

        Returns:
            DeleteCheckResult with deletion context information.
        """
        from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

        web_obj = self.model_web.get_web_object_from_efootprint_id(object_id)
        web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(web_obj.class_as_simple_str)

        list_containers, _ = web_obj.list_containers_and_attr_name_in_list_container
        dict_containers, _ = web_obj.dict_containers_and_attr_name_in_dict_container
        # Classes with a pre_delete hook (e.g. edge group members) handle their dict memberships
        # themselves on the normal deletion path, so their dict containers don't count here.
        if web_class and hasattr(web_class, 'pre_delete'):
            dict_containers = []
        child_containers = list_containers + dict_containers

        # Check for blocking containers (non-child references)
        if web_obj.modeling_obj_containers and not child_containers:
            # Check if class has custom blocking logic via can_delete hook
            if web_class and hasattr(web_class, 'can_delete'):
                can_delete, blocking_names = web_class.can_delete(web_obj)
                if not can_delete:
                    return DeleteCheckResult(can_delete=False, blocking_containers=blocking_names)
            else:
                # Default: block if has non-list containers
                blocking_names = [obj.name for obj in web_obj.modeling_obj_containers]
                return DeleteCheckResult(
                    can_delete=False,
                    blocking_containers=blocking_names,
                )

        # Check for accordion children
        accordion_children = web_obj.accordion_children
        has_children = len(accordion_children) > 0
        children_class_type = accordion_children[0].class_as_simple_str if has_children else ""

        # Check for mirroring
        mirrored_cards = web_obj.mirrored_cards
        is_mirrored = len(mirrored_cards) > 1

        return DeleteCheckResult(
            can_delete=True,
            is_list_deletion=bool(child_containers),
            has_accordion_children=has_children,
            accordion_children_count=len(accordion_children),
            accordion_children_class_type=children_class_type,
            is_mirrored=is_mirrored,
            mirrored_count=len(mirrored_cards),
        )

    def execute(self, input_data: DeleteObjectInput) -> DeleteObjectOutput:
        """Execute the object deletion use case.

        Args:
            input_data: The input containing object ID and optional form data.

        Returns:
            DeleteObjectOutput with deletion results.
        """
        from model_builder.domain.services import EditService
        from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
        from efootprint.logger import logger

        web_obj = self.model_web.get_web_object_from_efootprint_id(input_data.object_id)

        object_name = web_obj.name
        object_type = web_obj.class_as_simple_str
        web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(object_type)

        list_containers, attr_name_in_list_container = web_obj.list_containers_and_attr_name_in_list_container
        dict_containers, attr_name_in_dict_container = web_obj.dict_containers_and_attr_name_in_dict_container
        # Classes with a pre_delete hook (e.g. edge group members) handle their dict memberships
        # themselves on the normal deletion path below.
        if web_class and hasattr(web_class, 'pre_delete'):
            dict_containers = []

        if list_containers or dict_containers:
            # Child deletion: remove from all list and dict containers using domain service
            from model_builder.domain.services.object_linking_service import serialize_weighted_dict_entry
            edit_service = EditService()
            edited_containers = []

            containers_with_attrs = (
                [(container, attr_name_in_list_container, False) for container in list_containers]
                + [(container, attr_name_in_dict_container, True) for container in dict_containers])
            for container, attr_name, is_dict_container in containers_with_attrs:
                logger.info(f"Removing {web_obj.name} from {container.name}")

                # Build edit data to remove this object from the container attribute
                if is_dict_container:
                    new_attr_value = {
                        key.id: serialize_weighted_dict_entry(value)
                        for key, value in container.get_efootprint_value(attr_name).items()
                        if key.id != web_obj.efootprint_id
                    }
                else:
                    new_attr_value = [
                        list_attribute.efootprint_id
                        for list_attribute in getattr(container, attr_name)
                        if list_attribute.efootprint_id != web_obj.efootprint_id
                    ]
                edit_data = {"name": container.name, attr_name: new_attr_value}

                # Use domain service (no HTML generation)
                edit_result = edit_service.edit_with_cascade_cleanup(container, edit_data)
                edited_containers.append(edit_result.edited_object)

            self.model_web.persist_to_cache()
            # Call delete_side_effects after deletion so constraint diff reflects post-deletion state
            oob_regions = web_obj.delete_side_effects()
            return DeleteObjectOutput(
                deleted_object_name=object_name,
                deleted_object_type=object_type,
                was_list_deletion=True,
                edited_containers=edited_containers,
                oob_regions=oob_regions,
            )
        else:
            # Normal deletion
            # Call pre_delete hook if defined (e.g., UsagePattern needs to unlink from system)
            if web_class and hasattr(web_class, 'pre_delete'):
                web_class.pre_delete(web_obj, self.model_web)

            web_obj.self_delete()

            self.model_web.persist_to_cache()
            # Call delete_side_effects after deletion so constraint diff reflects post-deletion state
            oob_regions = web_obj.delete_side_effects()
            return DeleteObjectOutput(
                deleted_object_name=object_name,
                deleted_object_type=object_type,
                was_list_deletion=False,
                oob_regions=oob_regions,
            )
