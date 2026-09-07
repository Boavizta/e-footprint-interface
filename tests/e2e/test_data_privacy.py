import json
import math
import re
import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_retention_choice_and_shared_budget_warning_work_together(minimal_complete_model_builder):
    builder = minimal_complete_model_builder
    page = builder.page

    expect(builder.workspace_storage_status).to_have_count(1)
    expect(builder.workspace_storage_warning).to_have_count(0)

    builder.open_data_privacy_from_help_menu()
    progress = page.locator(".workspace-size-progress")
    current_bytes = int(progress.get_attribute("value"))
    limit_bytes = int(progress.get_attribute("max"))
    builder.set_recovery_retention(3600)
    expect(page.locator("#retention-update-result")).to_contain_text("Recovery retention is now 1 hour")
    builder.close_side_panel()

    model_document = page.evaluate(
        """async () => {
            const response = await fetch('/model_builder/download-json/');
            if (!response.ok) throw new Error(`Download failed: ${response.status}`);
            return response.json();
        }"""
    )
    padding_bytes = max(1, math.ceil(limit_bytes * 0.82) - current_bytes)
    model_document.setdefault("interface_config", {})["card_order"] = {
        "up-list": ["x" * padding_bytes],
        "uj-list": [],
        "external-api-list": [],
        "server-list": [],
        "edge-device-groups-list": [],
        "edge-devices-list": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as model_file:
        json.dump(model_document, model_file)
        model_path = model_file.name
    try:
        builder.import_json_file(model_path)
    finally:
        Path(model_path).unlink(missing_ok=True)

    expect(builder.workspace_storage_warning).to_be_visible()
    expect(builder.workspace_storage_warning).to_contain_text("of")
    expect(builder.workspace_storage_warning).to_contain_text("You can keep working")

    builder.open_data_privacy_from_storage_warning()
    expect(page.locator("#retention-seconds")).to_have_value("3600")

    operation_card = page.locator(
        ".data-privacy-card",
        has=page.get_by_role("heading", name="Operation, hosting & security"),
    )
    operation_text = operation_card.inner_text()
    if "Deployment-specific operator" in operation_text:
        expect(operation_card).to_contain_text(
            "Deployment-specific operator, processor, hosting, and region details are not configured"
        )
        expect(operation_card.locator("a[href^='mailto:']")).to_have_count(0)
    else:
        expect(operation_card).to_contain_text("Operated by")
        expect(operation_card).to_contain_text("hosted in")
        expect(operation_card.locator("a[href^='mailto:']")).to_have_count(1)

    builder.close_side_panel()
    builder.open_feedback_from_desktop_navbar()
    download = page.locator("[data-feedback-download]")
    expect(download).to_be_visible()
    expect(download).to_have_attribute("href", "/model_builder/download-json/")
    expect(download).to_have_attribute("target", "_blank")
    expect(download).to_have_attribute("rel", "noopener noreferrer")

    github = page.locator("[data-feedback-destination='github']")
    email = page.locator("[data-feedback-destination='email']")
    expect(github).to_have_attribute(
        "href",
        re.compile(r"^https://github\.com/Boavizta/e-footprint-interface/issues/new\?"),
    )
    expect(github).to_have_attribute("target", "_blank")
    expect(github).to_have_attribute("rel", "noopener noreferrer")
    expect(email).to_have_attribute("href", re.compile(r"^mailto:"))
