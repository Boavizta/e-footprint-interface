"""Use case for editing modeling objects.

This module contains the business logic for object editing, separated from
HTTP/presentation concerns.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List

from model_builder.domain.interfaces import ISystemRepository


@dataclass
class EditObjectInput:
    """Input data for object editing."""
    object_id: str
    form_data: Dict[str, Any]


@dataclass
class EditObjectOutput:
    """Output data from object editing."""
    edited_object_id: str
    edited_object_name: str
    edited_object_type: str
    template_name: str
    web_id: str
    mirrored_web_ids: List[str] = field(default_factory=list)
    html_updates: str = ""  # Pre-rendered HTML for card updates (temporary for migration)


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
        from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response
        from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

        # 1. Load system
        model_web = ModelWeb(self.repository)

        # 2. Get object to edit
        obj_to_edit = model_web.get_web_object_from_efootprint_id(input_data.object_id)

        # 3. Apply pre_edit hook if defined (e.g., ServerWeb edits storage first)
        web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(obj_to_edit.class_as_simple_str)
        if web_class and hasattr(web_class, 'pre_edit'):
            web_class.pre_edit(input_data.form_data, obj_to_edit, model_web)

        # 4. Compute edit HTML (this also performs the edit via edit_object_in_system)
        # Note: During migration, we still use the existing function which handles HTML generation
        html_updates = compute_edit_object_html_and_event_response(input_data.form_data, obj_to_edit)

        # 4. Build output
        return EditObjectOutput(
            edited_object_id=obj_to_edit.efootprint_id,
            edited_object_name=obj_to_edit.name,
            edited_object_type=obj_to_edit.class_as_simple_str,
            template_name=obj_to_edit.template_name,
            web_id=obj_to_edit.web_id,
            mirrored_web_ids=[card.web_id for card in obj_to_edit.mirrored_cards],
            html_updates=html_updates,
        )
