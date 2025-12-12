"""Use case for editing modeling objects.

This module contains the business logic for object editing, separated from
HTTP/presentation concerns.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List

from model_builder.domain.interfaces import ISystemRepository


@dataclass
class EditObjectInput:
    """Input data for object editing.

    Note: form_data should be pre-parsed by the adapter layer using
    parse_form_data_with_nested(). It should contain clean attribute names
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

    def __init__(self, repository: ISystemRepository):
        """Initialize with a system repository.

        Args:
            repository: Repository for loading and saving system data.
        """
        self.repository = repository

    def execute(self, input_data: EditObjectInput) -> EditObjectOutput:
        """Execute the object editing use case.

        Args:
            input_data: The input containing object ID and form data.

        Returns:
            EditObjectOutput with the edited object details.
        """
        from model_builder.domain.entities.web_core.model_web import ModelWeb
        from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
        from model_builder.domain.services import EditService

        # 1. Load system
        model_web = ModelWeb(self.repository)

        # 2. Get object to edit
        obj_to_edit = model_web.get_web_object_from_efootprint_id(input_data.object_id)

        # 3. Apply pre_edit hook if defined (e.g., ServerWeb edits storage first)
        web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(obj_to_edit.class_as_simple_str)
        if web_class and hasattr(web_class, 'pre_edit'):
            web_class.pre_edit(input_data.form_data, obj_to_edit, model_web)

        # 4. Perform the edit with cascade cleanup (domain service, no HTML)
        edit_service = EditService()
        edit_result = edit_service.edit_with_cascade_cleanup(obj_to_edit, input_data.form_data)

        # 5. Build output with pure data (presenter will generate HTML)
        edited_obj = edit_result.edited_object
        return EditObjectOutput(
            edited_object_id=edited_obj.efootprint_id,
            edited_object_name=edited_obj.name,
            edited_object_type=edited_obj.class_as_simple_str,
            template_name=edited_obj.template_name,
            web_id=edited_obj.web_id,
            mirrored_web_ids=[card.web_id for card in edited_obj.mirrored_cards],
            mirrored_cards=list(edited_obj.mirrored_cards),
        )
