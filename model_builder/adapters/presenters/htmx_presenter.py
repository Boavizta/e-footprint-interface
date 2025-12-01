"""HTMX presenter for formatting use case outputs as HTTP responses.

This module handles all HTTP/HTMX-specific response formatting, keeping
the presentation concerns separate from business logic.
"""
import json
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.shortcuts import render

from model_builder.application.use_cases import CreateObjectOutput, EditObjectOutput, DeleteObjectOutput
from model_builder.application.use_cases.delete_object import DeleteCheckResult
from model_builder.edition.edit_object_http_response_generator import generate_http_response_from_edit_html_and_events

if TYPE_CHECKING:
    from django.http import HttpRequest


class HtmxPresenter:
    """Presenter for formatting use case outputs as HTMX-compatible HTTP responses.

    This class is responsible for taking pure data from use cases and
    formatting it into HTTP responses suitable for HTMX partial updates.
    """

    def __init__(self, request: "HttpRequest"):
        """Initialize with the HTTP request.

        Args:
            request: The Django HTTP request object.
        """
        self.request = request

    def present_created_object(self, output: CreateObjectOutput) -> HttpResponse:
        """Format a created object as an HTTP response.

        Args:
            output: The output from CreateObjectUseCase.

        Returns:
            HttpResponse with the rendered object card and HTMX triggers.
        """
        from model_builder.adapters.repositories import SessionSystemRepository
        from model_builder.web_core.model_web import ModelWeb

        if output.parent_was_linked:
            # Parent was linked - return the parent's updated HTML
            toast_and_highlight_data = {
                "ids": output.mirrored_web_ids,
                "name": output.created_object_name,
                "action_type": "add_new_object"
            }
            return generate_http_response_from_edit_html_and_events(
                output.html_updates if hasattr(output, 'html_updates') else "",
                toast_and_highlight_data
            )

        # Check if we should return a different object (e.g., ExternalApi returns server)
        if output.override_object:
            override_obj = output.override_object
            response = render(
                self.request,
                f"model_builder/object_cards/{override_obj.template_name}_card.html",
                {"object": override_obj}
            )
            response["HX-Trigger-After-Swap"] = json.dumps({
                "displayToastAndHighlightObjects": {
                    "ids": [override_obj.web_id],
                    "name": override_obj.name,
                    "action_type": "add_new_object"
                }
            })
            return response

        # Standalone object - render its card
        repository = SessionSystemRepository(self.request.session)
        model_web = ModelWeb(repository)
        added_obj = model_web.get_web_object_from_efootprint_id(output.created_object_id)

        response = render(
            self.request,
            f"model_builder/object_cards/{output.template_name}_card.html",
            {"object": added_obj}
        )

        response["HX-Trigger-After-Swap"] = json.dumps({
            "resetLeaderLines": "",
            "setAccordionListeners": {"accordionIds": [output.web_id]},
            "displayToastAndHighlightObjects": {
                "ids": [output.web_id],
                "name": output.created_object_name,
                "action_type": "add_new_object"
            }
        })

        return response

    def present_created_object_with_parent_link(
        self, output: CreateObjectOutput, parent_html_updates: str
    ) -> HttpResponse:
        """Format a created object that was linked to a parent.

        Args:
            output: The output from CreateObjectUseCase.
            parent_html_updates: The HTML updates for the parent object.

        Returns:
            HttpResponse with the parent's updated HTML and HTMX triggers.
        """
        toast_and_highlight_data = {
            "ids": output.mirrored_web_ids,
            "name": output.created_object_name,
            "action_type": "add_new_object"
        }
        return generate_http_response_from_edit_html_and_events(parent_html_updates, toast_and_highlight_data)

    def present_edited_object(self, output: EditObjectOutput, trigger_result_display: bool = False) -> HttpResponse:
        """Format an edited object as an HTTP response.

        Args:
            output: The output from EditObjectUseCase.
            trigger_result_display: Whether to trigger result chart display.

        Returns:
            HttpResponse with the updated HTML and HTMX triggers.
        """
        toast_and_highlight_data = {
            "ids": output.mirrored_web_ids,
            "name": output.edited_object_name,
            "action_type": "edit_object"
        }
        return generate_http_response_from_edit_html_and_events(
            output.html_updates, toast_and_highlight_data, trigger_result_display
        )

    def present_deleted_object(self, output: DeleteObjectOutput) -> HttpResponse:
        """Format a deleted object as an HTTP response.

        Args:
            output: The output from DeleteObjectUseCase.

        Returns:
            HttpResponse with HTMX triggers for UI updates.
        """
        toast_and_highlight_data = {
            "ids": output.deleted_web_ids,
            "name": output.deleted_object_name,
            "action_type": "delete_object"
        }

        if output.was_list_deletion:
            return generate_http_response_from_edit_html_and_events(
                output.html_updates, toast_and_highlight_data
            )
        else:
            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps({
                "resetLeaderLines": "",
                "displayToastAndHighlightObjects": toast_and_highlight_data
            })
            return response

    def present_delete_confirmation(
        self, check_result: DeleteCheckResult, web_obj, object_id: str
    ) -> HttpResponse:
        """Present a delete confirmation modal.

        Args:
            check_result: The result from checking if deletion is allowed.
            web_obj: The web object to potentially delete.
            object_id: The ID of the object.

        Returns:
            HttpResponse with the appropriate modal.
        """
        from model_builder.form_references import FORM_TYPE_OBJECT

        if not check_result.can_delete:
            # Can't delete - show blocking message
            blocking_names = ", ".join(check_result.blocking_containers)
            container_class = web_obj.modeling_obj_containers[0].class_as_simple_str
            container_label = FORM_TYPE_OBJECT[container_class]["label"].lower()

            message = (
                f"This {web_obj.class_as_simple_str} is referenced by {blocking_names}. "
                f"To delete it, first delete or reorient these {container_label}s."
            )

            return render(
                self.request,
                "model_builder/modals/cant_delete_modal.html",
                {"modal_id": "model-builder-modal", "message": message}
            )

        # Build delete confirmation context
        context = {
            "obj": web_obj,
            "modal_id": "model-builder-modal",
            "remove_card_with_hyperscript": True,
        }

        if check_result.has_accordion_children:
            class_label = web_obj.class_label.lower()
            child_label = check_result.accordion_children_class_label
            context["message"] = (
                f"This {class_label} is associated with {check_result.accordion_children_count} {child_label}. "
                f"This action will delete them all"
            )
            context["sub_message"] = f"{child_label.capitalize()} used in other {class_label}s will remain in those."
        else:
            context["message"] = f"Are you sure you want to delete this {web_obj.class_as_simple_str} ?"
            context["sub_message"] = ""

        if check_result.is_mirrored:
            context["remove_card_with_hyperscript"] = False
            context["message"] = (
                f"This {web_obj.class_as_simple_str} is mirrored {check_result.mirrored_count} times, "
                f"this action will delete all mirrored {web_obj.class_as_simple_str}s."
            )
            context["sub_message"] = (
                f"To delete only one {web_obj.class_as_simple_str}, "
                f"break the mirroring link first."
            )

        return render(
            self.request,
            "model_builder/modals/delete_card_modal.html",
            context
        )
