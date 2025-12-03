"""Use case for deleting modeling objects.

This module contains the business logic for object deletion, separated from
HTTP/presentation concerns.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from model_builder.domain.interfaces import ISystemRepository


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
    accordion_children_class_label: str = ""
    is_mirrored: bool = False
    mirrored_count: int = 0


@dataclass
class DeleteObjectOutput:
    """Output data from object deletion."""
    deleted_object_name: str
    deleted_object_type: str
    was_list_deletion: bool = False
    html_updates: str = ""  # Pre-rendered HTML for card updates (for list deletions)
    deleted_web_ids: List[str] = field(default_factory=list)


class DeleteObjectUseCase:
    """Use case for deleting a modeling object.

    This class encapsulates the business logic for deleting objects,
    including handling list container removals.
    """

    def __init__(self, repository: ISystemRepository):
        """Initialize with a system repository.

        Args:
            repository: Repository for loading and saving system data.
        """
        self.repository = repository

    def check_can_delete(self, object_id: str) -> DeleteCheckResult:
        """Check if an object can be deleted and gather context for confirmation.

        Args:
            object_id: The ID of the object to check.

        Returns:
            DeleteCheckResult with deletion context information.
        """
        from model_builder.web_core.model_web import ModelWeb
        from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

        model_web = ModelWeb(self.repository)
        web_obj = model_web.get_web_object_from_efootprint_id(object_id)

        list_containers, _ = web_obj.list_containers_and_attr_name_in_list_container

        # Check for blocking containers (non-list references)
        if web_obj.modeling_obj_containers and not list_containers:
            # Check if class has custom blocking logic via can_delete hook
            web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(web_obj.class_as_simple_str)
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
        children_label = accordion_children[0].class_label.lower() if has_children else ""

        # Check for mirroring
        mirrored_cards = web_obj.mirrored_cards
        is_mirrored = len(mirrored_cards) > 1

        return DeleteCheckResult(
            can_delete=True,
            is_list_deletion=bool(list_containers),
            has_accordion_children=has_children,
            accordion_children_count=len(accordion_children),
            accordion_children_class_label=children_label,
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
        from model_builder.web_core.model_web import ModelWeb
        from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response
        from efootprint.logger import logger

        model_web = ModelWeb(self.repository)
        web_obj = model_web.get_web_object_from_efootprint_id(input_data.object_id)

        object_name = web_obj.name
        object_type = web_obj.class_as_simple_str

        list_containers, attr_name_in_list_container = web_obj.list_containers_and_attr_name_in_list_container

        if list_containers:
            # List deletion: remove from all list containers
            html_updates = ""
            for list_container in list_containers:
                logger.info(f"Removing {web_obj.name} from {list_container.name}")

                # Build edit data to remove this object from the list (plain dict works)
                new_list_attribute_ids = [
                    list_attribute.efootprint_id
                    for list_attribute in getattr(list_container, attr_name_in_list_container)
                    if list_attribute.efootprint_id != web_obj.efootprint_id
                ]
                edit_data = {
                    'name': list_container.name,
                    attr_name_in_list_container: ";".join(new_list_attribute_ids)
                }

                partial_html = compute_edit_object_html_and_event_response(edit_data, list_container)
                html_updates += partial_html

            return DeleteObjectOutput(
                deleted_object_name=object_name,
                deleted_object_type=object_type,
                was_list_deletion=True,
                html_updates=html_updates,
            )
        else:
            # Normal deletion
            # Call pre_delete hook if defined (e.g., UsagePattern needs to unlink from system)
            from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
            web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(object_type)
            if web_class and hasattr(web_class, 'pre_delete'):
                web_class.pre_delete(web_obj, model_web)

            web_obj.self_delete()
            model_web.update_system_data_with_up_to_date_calculated_attributes()

            return DeleteObjectOutput(
                deleted_object_name=object_name,
                deleted_object_type=object_type,
                was_list_deletion=False,
            )
