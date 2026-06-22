import json
import os
from urllib.parse import urlencode

from django.shortcuts import render
from efootprint import __version__ as efootprint_version

from e_footprint_interface import __version__ as interface_version

GITHUB_NEW_ISSUE_URL = "https://github.com/Boavizta/e-footprint-interface/issues/new"


def build_report_bug_url(error=None):
    """Build a GitHub "new issue" URL with a prefilled bug-report template.

    The body never includes a traceback or model data (it would leak into the URL and the
    public issue); it only carries the versions and the exception type, and asks the user to
    attach the model they downloaded from the recovery page.
    """
    body_lines = [
        "## What happened",
        "<!-- What were you doing when the error occurred? -->",
        "",
        "## Model file",
        "<!-- Please drag-and-drop the model you downloaded from the recovery page here. -->",
        "",
        "## Environment",
        f"- e-footprint version: {efootprint_version}",
        f"- interface version: {interface_version}",
    ]
    if error is not None:
        body_lines.append(f"- Error: {type(error).__name__}: {error}")
    query = urlencode({"title": "[Bug] e-footprint interface error", "body": "\n".join(body_lines)})
    return f"{GITHUB_NEW_ISSUE_URL}?{query}"


def _slot_label(slot: int) -> str:
    """Human label for a workspace slot on the recovery page: 0 → "A", 1 → "B"."""
    return chr(ord("A") + slot)


def render_recovery_page(request, error=None, status=200):
    """Render the self-contained recovery page (reset / download / report a bug).

    Used as the escape hatch from a dead state: the entry view falls back to it when the
    session model fails to deserialize, and the project-wide handler500 renders it in
    production. It must never depend on the (possibly corrupt) model — it only reads the
    workspace *index* (occupied slot ids + active pointer) and whether each slot's raw payload
    exists, defensively, so a per-slot download link can be offered without ever deserializing.
    """
    recovery_slots = []
    try:
        from model_builder.adapters.repositories import SessionWorkspaceRepository
        workspace = SessionWorkspaceRepository(request.session)
        active_slot = workspace.active_slot()
        for slot in workspace.list_slots():
            # has_system_data is a cache existence check, not a deserialize — dead-state-safe.
            if workspace.repository_for(slot).has_system_data():
                recovery_slots.append(
                    {"slot": slot, "label": _slot_label(slot), "is_active": slot == active_slot})
        if not recovery_slots and workspace.active_repository().has_system_data():
            # Index empty/out of sync but the active slot still has raw data: offer the single link.
            recovery_slots = [{"slot": active_slot, "label": _slot_label(active_slot), "is_active": True}]
    except Exception:
        recovery_slots = []

    # A single-slot session shows one unlabelled "Download your current model"; two slots get one
    # labelled link each ("Download model A / B"), so neither model is lost from a dead state.
    show_slot_labels = len(recovery_slots) > 1

    context = {
        "report_bug_url": build_report_bug_url(error),
        "recovery_slots": recovery_slots,
        "show_slot_labels": show_slot_labels,
        "has_saved_model": bool(recovery_slots),
        "error_type": type(error).__name__ if error is not None else None,
    }

    return render(request, "model_builder/recovery.html", context, status=status)


def render_exception_modal(request, exception):
    if os.environ.get("RAISE_EXCEPTIONS"):
        raise exception
    http_response = render(request, "model_builder/modals/exception_modal.html", {
        "modal_id": "model-builder-modal", "message": exception})

    # The modal is delivered entirely out-of-band into #modal-container, so the main response body is
    # empty. Without this, that empty body would be swapped into the triggering element's target —
    # harmless for transient side panels, but it would wipe #main-content-block for views that target
    # the whole builder (add-model / remove-model). HX-Reswap: none suppresses the main swap; OOB
    # swaps are still processed, so the modal appears and the canvas is left untouched.
    http_response["HX-Reswap"] = "none"
    http_response["HX-Trigger-After-Settle"] = json.dumps({"openModalDialog": {"modal_id": "model-builder-modal"}})

    return http_response


def render_exception_modal_if_error(func):
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return render_exception_modal(request, e)
    return wrapper
