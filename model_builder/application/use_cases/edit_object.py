"""Use case for editing modeling objects.

This module contains the business logic for object editing, separated from
HTTP/presentation concerns.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List

from model_builder.domain.entities.web_core.model_web import ModelWeb


@dataclass
class EditObjectInput:
    """Input data for object editing.

    Note: form_data should be pre-parsed by the adapter layer using
    parse_form_data(). It should contain clean attribute names
    (no prefixes), nested form data under _parsed_* keys, and units under _units key.
    """
    object_id: str
    form_data: Dict[str, Any]  # Pre-parsed form data (clean attribute names)


@dataclass
class EditObjectOutput:
    """Output data from object editing."""
    edited_object_id: str
    edited_object_name: str
    edited_object_type: str
    template_name: str
    web_id: str
    mirrored_web_ids: List[str] = field(default_factory=list)
    mirrored_cards: List[Any] = field(default_factory=list)  # Web objects for HTML rendering


class EditObjectUseCase:
    """Use case for editing an existing modeling object.

    This class encapsulates the business logic for editing objects.
    It returns pure data without any HTTP/presentation concerns.
    """

    def __init__(self, model_web: ModelWeb):
        """Initialize with a web model.

        Args:
            model web with a loaded system data.
        """
        self.model_web = model_web

    def execute(self, input_data: EditObjectInput) -> EditObjectOutput:
        """Execute the object editing use case.

        Args:
            input_data: The input containing object ID and form data.

        Returns:
            EditObjectOutput with the edited object details.
        """
        from model_builder.domain.entities.web_core.model_web import ModelWeb
        from model_builder.domain.services import EditService

        # Get object to edit
        obj_to_edit = self.model_web.get_web_object_from_efootprint_id(input_data.object_id)

        # Apply pre_edit hook if defined (e.g., ServerWeb edits storage first)
        if hasattr(obj_to_edit, 'pre_edit'):
            obj_to_edit.pre_edit(input_data.form_data)

        # Perform the edit with cascade cleanup (domain service, no HTML)
        edit_service = EditService()
        edit_result = edit_service.edit_with_cascade_cleanup(obj_to_edit, input_data.form_data)

        # Build output with pure data (presenter will generate HTML)
        edited_obj = edit_result.edited_object

        self.model_web.update_system_data_with_up_to_date_calculated_attributes()
        return EditObjectOutput(
            edited_object_id=edited_obj.efootprint_id,
            edited_object_name=edited_obj.name,
            edited_object_type=edited_obj.class_as_simple_str,
            template_name=edited_obj.template_name,
            web_id=edited_obj.web_id,
            mirrored_web_ids=[card.web_id for card in edited_obj.mirrored_cards],
            mirrored_cards=list(edited_obj.mirrored_cards),
        )
