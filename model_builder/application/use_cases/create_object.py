"""Use case for creating new modeling objects.

This module contains the business logic for object creation, separated from
HTTP/presentation concerns. The use case returns pure data that can be
presented by any adapter (HTMX, API, CLI, etc.).
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from model_builder.domain.interfaces import ISystemRepository


@dataclass
class CreateObjectInput:
    """Input data for object creation."""
    object_type: str
    form_data: Dict[str, Any]  # Dict-like object (QueryDict or plain dict)
    parent_id: Optional[str] = None


@dataclass
class CreateObjectOutput:
    """Output data from object creation."""
    created_object_id: str
    created_object_name: str
    created_object_type: str
    template_name: str
    web_id: str
    mirrored_web_ids: List[str] = field(default_factory=list)
    parent_was_linked: bool = False
    linked_parent_id: Optional[str] = None
    linked_parent_web_id: Optional[str] = None
    linked_parent_mirrored_web_ids: List[str] = field(default_factory=list)
    # HTML updates for parent card when parent was linked
    html_updates: str = ""
    # For cases where a different object should be returned (e.g., ExternalApi returns server)
    override_object: Optional[Any] = None


class CreateObjectUseCase:
    """Use case for creating a new modeling object.

    This class encapsulates the business logic for creating objects,
    including linking to parent objects when needed. It returns pure
    data without any HTTP/presentation concerns.
    """

    def __init__(self, repository: ISystemRepository):
        """Initialize with a system repository.

        Args:
            repository: Repository for loading and saving system data.
        """
        self.repository = repository

    def execute(self, input_data: CreateObjectInput) -> CreateObjectOutput:
        """Execute the object creation use case.

        Args:
            input_data: The input containing object type, form data, and optional parent ID.

        Returns:
            CreateObjectOutput with the created object details.

        Raises:
            Exception: Re-raises any exception after cleaning up the created object.
        """
        from model_builder.web_core.model_web import ModelWeb
        from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data
        from model_builder.efootprint_to_web_mapping import (wrap_efootprint_object,
                                                             EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING)

        # 1. Load system
        model_web = ModelWeb(self.repository)

        # 2. Get input web class (e.g., ExternalApiWeb) - hooks may be defined here
        input_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(input_data.object_type)
        form_data = input_data.form_data

        # 3. Apply hooks from input web class first (before type resolution)
        # 3a. Pre-create hook: create prerequisite objects (e.g., ExternalApi creates storage + server)
        if input_web_class and hasattr(input_web_class, 'pre_create'):
            form_data = input_web_class.pre_create(form_data, model_web)

        # 3b. Prepare input hook: modify form data before creation
        if input_web_class and hasattr(input_web_class, 'prepare_creation_input'):
            form_data = input_web_class.prepare_creation_input(form_data)

        # 4. Determine actual object type (may be different from input if using type_object_available)
        object_creation_type = form_data.get("type_object_available", input_data.object_type)

        # 5. Get creation web class (e.g., GenAIModelWeb) - may have additional hooks
        web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(object_creation_type)

        # 5a. Apply hooks from creation web class (if different from input class)
        if web_class and web_class != input_web_class:
            if hasattr(web_class, 'pre_create'):
                form_data = web_class.pre_create(form_data, model_web)
            if hasattr(web_class, 'prepare_creation_input'):
                form_data = web_class.prepare_creation_input(form_data)

        # 6. Create the efootprint object from form data
        try:
            new_efootprint_obj = create_efootprint_obj_from_post_data(form_data, model_web, object_creation_type)
        except Exception as e:
            # 6a. Handle creation error hook (e.g., ExternalApi handles InsufficientCapacityError)
            # Check input_web_class first, then web_class
            handler_class = None
            if input_web_class and hasattr(input_web_class, 'handle_creation_error'):
                handler_class = input_web_class
            elif web_class and hasattr(web_class, 'handle_creation_error'):
                handler_class = web_class

            if handler_class:
                new_efootprint_obj = handler_class.handle_creation_error(e, form_data, model_web)
            else:
                raise e

        try:
            # 7a. Pre-add hook: perform actions before adding to system (e.g., link to system lists)
            # Check both input_web_class and web_class
            if input_web_class and hasattr(input_web_class, 'pre_add_to_system'):
                input_web_class.pre_add_to_system(new_efootprint_obj, model_web)
            elif web_class and hasattr(web_class, 'pre_add_to_system'):
                web_class.pre_add_to_system(new_efootprint_obj, model_web)

            # 7b. Add to system
            added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

            # 8. Handle parent linking if needed
            parent_was_linked = False
            linked_parent_id = None
            linked_parent_web_id = None
            linked_parent_mirrored_web_ids = []
            html_updates = ""

            # Check if this class should skip parent linking (e.g., services link via 'server' field)
            skip_linking = (getattr(input_web_class, 'skip_parent_linking', False)
                            or getattr(web_class, 'skip_parent_linking', False))

            if input_data.parent_id and not skip_linking:
                parent_was_linked, linked_parent_web_id, linked_parent_mirrored_web_ids, html_updates = self._link_to_parent(
                    model_web, added_obj, input_data.parent_id)
                linked_parent_id = input_data.parent_id

            # 9. Post-create hook (e.g., ExternalApi returns server instead of service)
            # Check input_web_class first, then web_class
            override_object = None
            post_create_class = None
            if input_web_class and hasattr(input_web_class, 'post_create'):
                post_create_class = input_web_class
            elif web_class and hasattr(web_class, 'post_create'):
                post_create_class = web_class

            if post_create_class:
                post_create_result = post_create_class.post_create(added_obj, form_data, model_web)
                if post_create_result and post_create_result.get("return_server_instead"):
                    override_object = post_create_result.get("server_web")

            # 8. Build output
            return CreateObjectOutput(
                created_object_id=added_obj.efootprint_id,
                created_object_name=added_obj.name,
                created_object_type=object_creation_type,
                template_name=added_obj.template_name,
                web_id=added_obj.web_id,
                mirrored_web_ids=[card.web_id for card in added_obj.mirrored_cards],
                parent_was_linked=parent_was_linked,
                linked_parent_id=linked_parent_id,
                linked_parent_web_id=linked_parent_web_id,
                linked_parent_mirrored_web_ids=linked_parent_mirrored_web_ids,
                html_updates=html_updates,
                override_object=override_object,
            )
        except Exception as e:
            # Clean up on failure
            from efootprint.logger import logger
            logger.error("An error occurred during new object creation, deleting the created object.")
            added_obj_wrapper = wrap_efootprint_object(new_efootprint_obj, model_web)
            added_obj_wrapper.self_delete()
            model_web.update_system_data_with_up_to_date_calculated_attributes()
            raise e

    def _link_to_parent(self, model_web, added_obj, parent_id: str):
        """Link the created object to its parent.

        Returns:
            Tuple of (parent_was_linked, parent_web_id, parent_mirrored_web_ids, html_updates)
        """
        from typing import List, get_origin, get_args
        from django.template.loader import render_to_string
        from efootprint.utils.tools import get_init_signature_params
        from model_builder.object_creation_and_edition_utils import edit_object_in_system

        web_object_to_link_to = model_web.get_web_object_from_efootprint_id(parent_id)
        efootprint_object_to_link_to = web_object_to_link_to.modeling_obj

        # Find the attr name for the list of objects to append the added object to
        init_sig_params = get_init_signature_params(type(efootprint_object_to_link_to))
        attr_name_in_list_container = None
        for attr_name in init_sig_params:
            annotation = init_sig_params[attr_name].annotation
            if (get_origin(annotation) and get_origin(annotation) in (list, List)
                and isinstance(added_obj.modeling_obj, get_args(annotation)[0])):
                attr_name_in_list_container = attr_name
                break

        assert attr_name_in_list_container is not None, "A list attr name should always be found"

        # Build the edit data for the parent (plain dict works with edit_object_in_system)
        existing_element_ids = [elt.id for elt in getattr(efootprint_object_to_link_to, attr_name_in_list_container)]
        existing_element_ids.append(added_obj.efootprint_id)
        edit_data = {attr_name_in_list_container: ";".join(existing_element_ids)}

        # Edit the parent to include the new object
        edit_object_in_system(edit_data, web_object_to_link_to)

        # Generate HTML updates for all mirrored parent cards
        html_updates = ""
        mirrored_cards = web_object_to_link_to.mirrored_cards
        for mirrored_card in mirrored_cards:
            html_updates += (
                f"<div hx-swap-oob='outerHTML:#{mirrored_card.web_id}'>"
                f"{render_to_string(f'model_builder/object_cards/{mirrored_card.template_name}_card.html', {'object': mirrored_card})}"
                f"</div>"
            )

        parent_mirrored_web_ids = [card.web_id for card in mirrored_cards]

        return True, web_object_to_link_to.web_id, parent_mirrored_web_ids, html_updates
