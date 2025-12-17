"""Tests for GenAI services - GPU servers, LLM models, external APIs."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestGenAIServices:
    """Tests for GenAI service creation and error handling."""

    def test_create_genai_service_on_gpu_server(self, empty_model_builder: ModelBuilderPage):
        """Create a GPU server with GenAI model service and edit it."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        server_name = "Test GPU Server"
        service_name = "Test GenAI Model"

        # Create GPU server with enough compute
        model_builder.click_add_server()
        side_panel.select_object_type("GPUServer")
        side_panel.fill_field("GPUServer_name", server_name)
        side_panel.fill_field("GPUServer_compute", "16")
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("GPUServer", server_name)

        # Add GenAI model service to server
        server_card = model_builder.get_object_card("GPUServer", server_name)
        server_card.click_add_service_button()

        side_panel.fill_field("GenAIModel_name", service_name)
        side_panel.select_option("GenAIModel_provider", "openai")
        side_panel.fill_field("GenAIModel_model_name", "gpt-4o")
        side_panel.submit_and_wait_for_close()

        # Edit the service - change provider and model
        service_card = model_builder.get_object_card("GenAIModel", service_name)
        service_card.click_edit_button()

        side_panel.select_option("GenAIModel_provider", "mistralai")
        side_panel.fill_field("GenAIModel_model_name", "mistral-small")
        side_panel.submit_and_wait_for_close()

    def test_error_modal_when_gpu_too_small_for_llm(self, empty_model_builder: ModelBuilderPage):
        """Error modal should appear when GPU server is too small for the LLM."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        server_name = "Small GPU Server"
        service_name = "Large LLM"

        # Create GPU server with default (small) compute
        model_builder.click_add_server()
        side_panel.select_object_type("GPUServer")
        side_panel.fill_field("GPUServer_name", server_name)
        # Don't set compute - use default which is too small
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("GPUServer", server_name)

        # Try to add large LLM model
        server_card = model_builder.get_object_card("GPUServer", server_name)
        server_card.click_add_service_button()

        side_panel.fill_field("GenAIModel_name", service_name)
        side_panel.select_option("GenAIModel_provider", "openai")
        side_panel.fill_field("GenAIModel_model_name", "gpt-4")
        page.locator("#btn-submit-form").click()

        # Error modal should appear
        expect(page.locator("#model-builder-modal")).to_be_visible()
        expect(page.locator("#model-builder-modal")).to_contain_text("but is asked")

    def test_external_api_button_creates_server_and_service(self, empty_model_builder: ModelBuilderPage):
        """External API button should create both GPU server and GenAI service."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Click external API button
        page.locator("#btn-add-external-api").click()
        page.locator("#sidePanelForm").wait_for(state="visible")

        # Configure GenAI model
        side_panel.select_option("GenAIModel_provider", "openai")
        side_panel.fill_field("GenAIModel_model_name", "gpt-4")
        side_panel.submit_and_wait_for_close()

        # Both server and service should be created
        model_builder.object_should_exist("GPUServer", "Generative AI model 1 API servers")
        model_builder.object_should_exist("GenAIModel", "Generative AI model 1")
