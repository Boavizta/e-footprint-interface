import json
import math
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
    page.evaluate("closeAndEmptySidePanel()")

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

    builder.goto()
    builder.dismiss_template_picker_if_present()
    expect(builder.workspace_storage_warning).to_be_visible()
    expect(builder.workspace_storage_warning).to_contain_text("of")
    expect(builder.workspace_storage_warning).to_contain_text("You can keep working")

    builder.open_data_privacy_from_storage_warning()
    expect(page.locator("#retention-seconds")).to_have_value("3600")
