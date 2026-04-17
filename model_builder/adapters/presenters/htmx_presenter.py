"""HTMX presenter for formatting use case outputs as HTTP responses.

This module handles all HTTP/HTMX-specific response formatting, keeping
the presentation concerns separate from business logic.
"""
import json
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from model_builder.adapters.presenters.oob_regions import oob_regions_cover_all_cards, render_oob_regions
from model_builder.adapters.ui_config.constraint_messages import CONSTRAINT_MESSAGES
from model_builder.application.use_cases import CreateObjectOutput, EditObjectOutput, DeleteObjectOutput
from model_builder.application.use_cases.delete_object import DeleteCheckResult

if TYPE_CHECKING:
    from django.http import HttpRequest
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class HtmxPresenter:
    """Presenter for formatting use case outputs as HTMX-compatible HTTP responses.

    This class is responsible for taking pure data from use cases and
    formatting it into HTTP responses suitable for HTMX partial updates.
    """

    def __init__(self, request: "HttpRequest", model_web: "ModelWeb" = None):
        """Initialize with the HTTP request.

        Args:
            request: The Django HTTP request object.
        """
        self.request = request
        self._model_web = model_web

    @property
    def model_web(self) -> "ModelWeb":
        """Lazy-load ModelWeb instance. Only created when needed (e.g., for recomputation)."""
        if self._model_web is None:
            from model_builder.adapters.repositories import SessionSystemRepository
            from model_builder.domain.entities.web_core.model_web import ModelWeb
            self._model_web = ModelWeb(SessionSystemRepository(self.request.session))
        return self._model_web

    def _constraint_toast_messages(self) -> list[str]:
        """Return toast messages for any constraint changes on the current model_web."""
        changes = getattr(self._model_web, "constraint_changes", [])
        return [
            CONSTRAINT_MESSAGES[key][direction]
            for key, direction in changes
            if key in CONSTRAINT_MESSAGES
        ]

    def _oob_response_setup(self, oob_regions) -> tuple[bool, dict, list[str]]:
        """Compute (canvas_oob, extra_settle, constraint_messages) shared by every mutation response."""
        canvas_oob = oob_regions_cover_all_cards(oob_regions)
        extra_settle = {"initModelBuilderMain": ""} if canvas_oob else {}
        return canvas_oob, extra_settle, self._constraint_toast_messages()

    def _recomputation_html(self) -> str:
        """HTML for re-rendering the result panel as an OOB innerHTML swap."""
        refresh_content = render_to_string(
            "model_builder/result/result_panel.html", context={"model_web": self.model_web})
        return (f"<div id='result-block' hx-swap-oob='innerHTML:#result-block'>"
                f"{refresh_content}</div>")

    def present_created_object(self, output: CreateObjectOutput, recompute: bool = False) -> HttpResponse:
        """Format a created object as an HTTP response.

        Args:
            output: The output from CreateObjectUseCase.
            recompute: Whether to append result panel recomputation HTML.

        Returns:
            HttpResponse with the rendered object card and HTMX triggers.
        """
        canvas_oob, extra_settle, constraint_messages = self._oob_response_setup(output.oob_regions)

        if output.parent_was_linked:
            toast_and_highlight_data = {
                "ids": output.mirrored_web_ids,
                "name": output.created_object_name,
                "action_type": "add_new_object",
                "constraint_messages": constraint_messages,
            }

            if canvas_oob or (output.replaces_primary_render and output.oob_regions):
                # OOB regions handle the full re-render (parent inside edge device group, or canvas re-render)
                html_updates = render_oob_regions(self.model_web, output.oob_regions)
            else:
                parent_obj = self.model_web.get_web_object_from_efootprint_id(output.linked_parent_id)
                html_updates = self._generate_mirrored_cards_html(parent_obj.mirrored_cards)
                html_updates += self._sibling_cards_with_link_flip(
                    parent_obj.class_as_simple_str, {output.linked_parent_id}, target_count=1)
                html_updates += render_oob_regions(self.model_web, output.oob_regions)

            if recompute:
                html_updates += self._recomputation_html()
            return self._build_oob_response(html_updates, toast_and_highlight_data,
                                            extra_settle_triggers=extra_settle)

        # Check if we should return a different object (e.g., server instead of service)
        if output.override_object:
            override_obj = output.override_object
            response = render(
                self.request,
                f"model_builder/object_cards/{override_obj.template_name}_card.html",
                {"object": override_obj}
            )
            after_settle = {
                "displayToastAndHighlightObjects": {
                    "ids": [override_obj.web_id],
                    "name": override_obj.name,
                    "action_type": "add_new_object",
                    "constraint_messages": constraint_messages,
                }
            }
            after_settle.update(extra_settle)
            response["HX-Trigger-After-Settle"] = json.dumps(after_settle)
            if recompute:
                response.content += self._recomputation_html().encode("utf-8")
            return response

        # Standalone object - render its card (unless side-effects own the layout instead)
        if output.replaces_primary_render:
            response = HttpResponse("")
        else:
            added_obj = self.model_web.get_web_object_from_efootprint_id(output.created_object_id)
            response = render(
                self.request,
                f"model_builder/object_cards/{output.template_name}_card.html",
                {"object": added_obj}
            )

        after_settle = {
            "resetLeaderLines": "",
            "setAccordionListeners": {"accordionIds": [output.web_id]},
            "displayToastAndHighlightObjects": {
                "ids": [output.web_id],
                "name": output.created_object_name,
                "action_type": "add_new_object",
                "constraint_messages": constraint_messages,
            }
        }
        after_settle.update(extra_settle)
        response["HX-Trigger-After-Settle"] = json.dumps(after_settle)

        response.content += render_oob_regions(self.model_web, output.oob_regions).encode("utf-8")

        if recompute:
            response.content += self._recomputation_html().encode("utf-8")
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
        return self._build_oob_response(parent_html_updates, toast_and_highlight_data)

    def present_edited_object(
        self, output: EditObjectOutput, recompute: bool = False, trigger_result_display: bool = False
    ) -> HttpResponse:
        """Format an edited object as an HTTP response.

        Args:
            output: The output from EditObjectUseCase.
            recompute: Whether to append result panel recomputation HTML.
            trigger_result_display: Whether to trigger result chart display.

        Returns:
            HttpResponse with the updated HTML and HTMX triggers.
        """
        canvas_oob, extra_settle, constraint_messages = self._oob_response_setup(output.oob_regions)

        toast_and_highlight_data = {
            "ids": output.mirrored_web_ids,
            "name": output.edited_object_name,
            "action_type": "edit_object",
            "constraint_messages": constraint_messages,
        }

        if canvas_oob or output.replaces_primary_render:
            # OOB regions cover all relevant cards; skip per-card mirrored-card swaps
            html_updates = render_oob_regions(self.model_web, output.oob_regions)
        elif output.name_only_change and not recompute:
            html_updates = (self._generate_name_only_updates_html(output.mirrored_cards)
                            + render_oob_regions(self.model_web, output.oob_regions))
            return self._build_oob_response(html_updates, toast_and_highlight_data,
                                            extra_settle_triggers=extra_settle, reset_leaderlines=False)
        else:
            html_updates = self._generate_mirrored_cards_html(output.mirrored_cards)
            # Re-render siblings whose "Link existing" button just disappeared
            # (cascade delete during edit reduced linkable_existing_count from 1 to 0)
            edited_ids = {card.efootprint_id for card in output.mirrored_cards}
            html_updates += self._sibling_cards_with_link_flip(
                output.edited_object_type, edited_ids, target_count=0)
            html_updates += render_oob_regions(self.model_web, output.oob_regions)

        if recompute:
            html_updates += self._recomputation_html()
            trigger_result_display = True

        return self._build_oob_response(html_updates, toast_and_highlight_data, trigger_result_display,
                                        extra_settle_triggers=extra_settle)

    def _generate_name_only_updates_html(self, mirrored_cards) -> str:
        """Generate OOB innerHTML swaps targeting only the name element of each mirrored card.

        Used for name-only edits to avoid full card re-renders, preserving accordion state.
        """
        return "".join(
            f"<div hx-swap-oob='innerHTML:#name-{card.web_id}'>{card.name}</div>"
            for card in mirrored_cards
        )

    def _sibling_cards_with_link_flip(
        self, parent_type: str, excluded_ids: set, target_count: int
    ) -> str:
        """HTML for mirrored cards of siblings whose "Link existing" button just flipped.

        A sibling is re-rendered when any of its child_sections has `linkable_existing_count`
        equal to `target_count` — 1 after a link crosses 0→1 (button appears), 0 after an
        edit/delete crosses 1→0 (button disappears).
        """
        html = ""
        for sibling in self.model_web.get_web_objects_from_efootprint_type(parent_type):
            if sibling.efootprint_id in excluded_ids:
                continue
            if any(s["linkable_existing_count"] == target_count for s in sibling.child_sections):
                html += self._generate_mirrored_cards_html(sibling.mirrored_cards)
        return html

    def _generate_mirrored_cards_html(self, mirrored_cards) -> str:
        """Generate OOB swap HTML for a list of mirrored cards.

        Args:
            mirrored_cards: List of web objects representing mirrored cards.

        Returns:
            HTML string with hx-swap-oob divs for each card.
        """
        html = ""
        for card in mirrored_cards:
            html += (
                f"<div hx-swap-oob='outerHTML:#{card.web_id}'>"
                f"{render_to_string(f'model_builder/object_cards/{card.template_name}_card.html', {'object': card})}"
                f"</div>"
            )
        return html

    def _build_oob_response(
        self, html: str, toast_data: dict, trigger_result_display: bool = False,
        extra_settle_triggers: dict = None, reset_leaderlines: bool = True,
    ) -> HttpResponse:
        """Build an HTTP response with OOB swap HTML and HTMX triggers.

        Args:
            html: The HTML content with hx-swap-oob divs.
            toast_data: Data for the toast notification (ids, name, action_type).
            trigger_result_display: Whether to trigger result chart display.
            extra_settle_triggers: Optional extra keys for HX-Trigger-After-Settle.
            reset_leaderlines: Whether to fire the immediate `resetLeaderLines` HX-Trigger.
                Disable for updates that don't change layout (e.g. name-only edits).

        Returns:
            HttpResponse with appropriate HTMX headers.
        """
        response = HttpResponse(html)
        if reset_leaderlines:
            response["HX-Trigger"] = json.dumps({"resetLeaderLines": ""})
        after_settle_trigger = {"displayToastAndHighlightObjects": toast_data}
        if trigger_result_display:
            after_settle_trigger["triggerResultRendering"] = ""
        if extra_settle_triggers:
            after_settle_trigger.update(extra_settle_triggers)
        response["HX-Trigger-After-Settle"] = json.dumps(after_settle_trigger)
        return response

    def present_deleted_object(self, output: DeleteObjectOutput) -> HttpResponse:
        """Format a deleted object as an HTTP response.

        Args:
            output: The output from DeleteObjectUseCase.

        Returns:
            HttpResponse with HTMX triggers for UI updates.
        """
        canvas_oob, extra_settle, constraint_messages = self._oob_response_setup(output.oob_regions)

        toast_and_highlight_data = {
            "ids": output.deleted_web_ids,
            "name": output.deleted_object_name,
            "action_type": "delete_object",
            "constraint_messages": constraint_messages,
        }

        if output.was_list_deletion and not canvas_oob:
            # Per-card outerHTML swaps for each edited container + siblings whose "Link existing"
            # button just disappeared (linkable_existing_count crossed 1→0)
            html_updates = "".join(
                self._generate_mirrored_cards_html(c.mirrored_cards) for c in output.edited_containers)
            if output.edited_containers:
                edited_ids = {c.efootprint_id for c in output.edited_containers}
                html_updates += self._sibling_cards_with_link_flip(
                    output.edited_containers[0].class_as_simple_str, edited_ids, target_count=0)
            html_updates += render_oob_regions(self.model_web, output.oob_regions)
            return self._build_oob_response(html_updates, toast_and_highlight_data,
                                            extra_settle_triggers=extra_settle)

        if output.oob_regions:
            # Either canvas_oob (covers all cards) or targeted regions (e.g. edge device lists)
            return self._build_oob_response(
                render_oob_regions(self.model_web, output.oob_regions), toast_and_highlight_data,
                extra_settle_triggers=extra_settle)

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
        from model_builder.adapters.label_resolver import LabelResolver

        if not check_result.can_delete:
            # Can't delete - show blocking message
            blocking_names = ", ".join(check_result.blocking_containers)
            container_class = web_obj.modeling_obj_containers[0].class_as_simple_str
            container_label = LabelResolver.get_class_label(container_class).lower()

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
            class_label = LabelResolver.get_class_label(web_obj.class_as_simple_str).lower()
            child_label = LabelResolver.get_class_label(check_result.accordion_children_class_type).lower()
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
