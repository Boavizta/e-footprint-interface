"""Tests for server and service creation/editing."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestServers:
    """Tests for server CRUD operations."""

    def test_create_cloud_server(self, empty_model_builder: ModelBuilderPage):
        """Test creating a BoaviztaCloudServer."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel

        server_name = "Test Cloud Server"

        model_builder.click_add_server()
        side_panel.should_contain_text("Add new server")
        side_panel.select_object_type("BoaviztaCloudServer")
        side_panel.fill_field("BoaviztaCloudServer_name", server_name)
        side_panel.fill_field("BoaviztaCloudServer_instance_type", "ent1-l")
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("BoaviztaCloudServer", server_name)

    def test_create_second_cloud_server(self, empty_model_builder: ModelBuilderPage):
        """Test creating a second BoaviztaCloudServer with different instance type."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel

        server_name = "Second Cloud Server"

        model_builder.click_add_server()
        side_panel.should_contain_text("Add new server")
        side_panel.select_object_type("BoaviztaCloudServer")
        side_panel.fill_field("BoaviztaCloudServer_name", server_name)
        side_panel.fill_field("BoaviztaCloudServer_instance_type", "dev1-s")
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("BoaviztaCloudServer", server_name)


@pytest.mark.e2e
class TestServices:
    """Tests for service operations."""

    def test_add_service_to_server(self, empty_model_builder: ModelBuilderPage):
        """Test adding a WebApplication service to a server."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        server_name = "Server For Service"
        service_name = "Test Web App"

        # First create a server
        model_builder.click_add_server()
        side_panel.select_object_type("BoaviztaCloudServer")
        side_panel.fill_field("BoaviztaCloudServer_name", server_name)
        side_panel.fill_field("BoaviztaCloudServer_instance_type", "ent1-l")
        side_panel.submit_and_wait_for_close()

        # Add service to server
        server_card = model_builder.get_object_card("BoaviztaCloudServer", server_name)
        server_card.click_add_service_button()

        side_panel.fill_field("WebApplication_name", service_name)
        side_panel.select_option("WebApplication_technology", "php-symfony")
        side_panel.submit_and_wait_for_close()

        # Verify service was added
        expect(page.locator("div").filter(has_text=service_name).locator("button[id^='button']").first).to_be_visible()
