"""Domain service for editing modeling objects with cascade behavior.

This service handles object editing and cleanup of orphaned accordion children,
keeping this business logic separate from HTTP/presentation concerns.
"""
from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb


@dataclass
class EditResult:
    """Result of editing an object with cascade cleanup."""
    edited_object: "ModelingObjectWeb"


class EditService:
    """Service that handles object editing with cascade cleanup of orphaned children.

    When an object is edited, some of its accordion children may become orphaned
    (no longer referenced by any container). This service identifies and deletes
    those orphaned children as part of the edit operation.
    """

    def edit_with_cascade_cleanup(self, obj_to_edit: "ModelingObjectWeb", form_data: Dict[str, Any]) -> EditResult:
        """Edit an object and clean up any orphaned accordion children.

        Args:
            obj_to_edit: The web object to edit.
            form_data: Pre-parsed form data with clean attribute names (no prefixes).
                      Should be parsed by adapter layer before calling this service.

        Returns:
            EditResult containing the edited object.
        """
        from model_builder.domain.object_factory import edit_object_from_parsed_data

        # Capture accordion children before edit (for each mirrored card)
        accordion_children_before = {}
        for mirrored_card in obj_to_edit.mirrored_cards:
            accordion_children_before[mirrored_card] = copy(mirrored_card.accordion_children)

        # Perform the edit (form_data is already parsed by adapter)
        edited_obj = edit_object_from_parsed_data(form_data, obj_to_edit)

        # Capture accordion children after edit
        accordion_children_after = {}
        for mirrored_card in edited_obj.mirrored_cards:
            accordion_children_after[mirrored_card] = copy(mirrored_card.accordion_children)

        # Find children that were removed (only need to check first mirrored card)
        first_mirrored_card = next(iter(accordion_children_after.keys()))
        removed_children = [
            child for child in accordion_children_before[first_mirrored_card]
            if child not in accordion_children_after[first_mirrored_card]
        ]

        # Delete orphaned children (those with no remaining containers)
        had_deletions = False
        for child in removed_children:
            if len(child.modeling_obj_containers) == 0:
                child.self_delete()
                had_deletions = True

        # Update system data if deletions occurred
        if had_deletions:
            obj_to_edit.model_web.update_system_data_with_up_to_date_calculated_attributes()

        return EditResult(edited_object=edited_obj)
