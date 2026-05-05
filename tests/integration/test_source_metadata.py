"""Integration tests for source metadata through parser → factory chain."""
import pytest

from efootprint.abstract_modeling_classes.source_objects import Sources

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.application.use_cases import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.object_factory import edit_object_from_parsed_data


@pytest.fixture
def model_web_with_server(minimal_repository):
    return ModelWeb(minimal_repository)


def test_edit_with_metadata_sets_confidence_comment_and_source(model_web_with_server):
    """Full parser → factory edit path with all metadata fields carries them onto the ExplainableObject."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]
    existing_source = Sources.HYPOTHESIS

    current_compute = server_web.modeling_obj.compute
    raw_form_data = {
        "Server_compute": str(current_compute.magnitude),
        "Server_compute__unit": f"{current_compute.value.units:~P}",
        "Server_compute__confidence": "medium",
        "Server_compute__comment": "verified by audit",
        "Server_compute__source_id": existing_source.id,
        "Server_compute__source_name": existing_source.name,
        "Server_compute__source_link": existing_source.link or "",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)

    updated = server_web.modeling_obj.compute
    assert updated.confidence == "medium"
    assert updated.comment == "verified by audit"
    assert updated.source is existing_source


def test_edit_with_unknown_source_id_mints_new_source(model_web_with_server):
    """Unknown source id causes a new Source to be minted with the submitted name and link."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]

    current_compute = server_web.modeling_obj.compute
    raw_form_data = {
        "Server_compute": str(current_compute.magnitude),
        "Server_compute__unit": f"{current_compute.value.units:~P}",
        "Server_compute__source_id": "nonexistent-id",
        "Server_compute__source_name": "Custom Study",
        "Server_compute__source_link": "https://example.com/study",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)

    updated = server_web.modeling_obj.compute
    assert updated.source.name == "Custom Study"
    assert updated.source.link == "https://example.com/study"
    assert updated.source.id in [s.id for s in model_web.available_sources]


def test_edit_value_change_with_no_confidence_submitted_resets_confidence(model_web_with_server):
    """Changing the value without resubmitting confidence clears it (client clears __confidence on change)."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]

    current_compute = server_web.modeling_obj.compute
    current_units = f"{current_compute.value.units:~P}"

    raw_form_data = {
        "Server_compute": str(current_compute.magnitude),
        "Server_compute__unit": current_units,
        "Server_compute__confidence": "high",
        "Server_compute__comment": "initial note",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)
    assert server_web.modeling_obj.compute.confidence == "high"

    new_value = str(current_compute.magnitude + 1)
    raw_form_data_changed = {
        "Server_compute": new_value,
        "Server_compute__unit": current_units,
        "Server_compute__comment": "initial note",
    }
    parsed_changed = parse_form_data(raw_form_data_changed, "Server")
    edit_object_from_parsed_data(parsed_changed, server_web)

    updated = server_web.modeling_obj.compute
    assert updated.confidence is None
    assert updated.comment == "initial note"


def test_edit_value_change_with_confidence_resubmitted_honors_it(model_web_with_server):
    """User can set confidence alongside a new value in one save; server must honor the explicit submission."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]

    current_compute = server_web.modeling_obj.compute
    current_compute.confidence = None
    new_value = str(current_compute.magnitude + 1)
    current_units = f"{current_compute.value.units:~P}"

    raw_form_data = {
        "Server_compute": new_value,
        "Server_compute__unit": current_units,
        "Server_compute__confidence": "medium",
        "Server_compute__comment": "updated estimate",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)

    updated = server_web.modeling_obj.compute
    assert updated.confidence == "medium"
    assert updated.comment == "updated estimate"


def test_edit_with_custom_source_no_id_mints_new_source(model_web_with_server):
    """Custom source submitted with a name but empty id mints a new Source instead of falling back to USER_DATA."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]

    current_compute = server_web.modeling_obj.compute
    raw_form_data = {
        "Server_compute": str(current_compute.magnitude),
        "Server_compute__unit": f"{current_compute.value.units:~P}",
        "Server_compute__source_id": "",
        "Server_compute__source_name": "My Custom Source",
        "Server_compute__source_link": "https://custom.example.com",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)

    updated = server_web.modeling_obj.compute
    assert updated.source.name == "My Custom Source"
    assert updated.source.link == "https://custom.example.com"


def test_same_form_cross_field_new_source_resolves_to_one_instance(model_web_with_server):
    """Two fields submitted with the same client-generated unknown id must share one Source instance."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]

    current_compute = server_web.modeling_obj.compute
    current_ram = server_web.modeling_obj.ram
    shared_id = "client-generated-shared-id"

    raw_form_data = {
        "Server_compute": str(current_compute.magnitude),
        "Server_compute__unit": f"{current_compute.value.units:~P}",
        "Server_compute__source_id": shared_id,
        "Server_compute__source_name": "Shared Study",
        "Server_compute__source_link": "https://shared.example.com",
        "Server_ram": str(current_ram.magnitude),
        "Server_ram__unit": f"{current_ram.value.units:~P}",
        "Server_ram__source_id": shared_id,
        "Server_ram__source_name": "Shared Study",
        "Server_ram__source_link": "https://shared.example.com",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)

    assert server_web.modeling_obj.compute.source is server_web.modeling_obj.ram.source
    assert server_web.modeling_obj.compute.source.id == shared_id


def test_existing_source_identity_is_preserved_after_edit(model_web_with_server):
    """Picking an existing source by id resolves to the same Python instance already in the model."""
    model_web = model_web_with_server
    server_web = model_web.get_web_objects_from_efootprint_type("Server")[0]

    existing_source = Sources.HYPOTHESIS
    current_compute = server_web.modeling_obj.compute

    raw_form_data = {
        "Server_compute": str(current_compute.magnitude),
        "Server_compute__unit": f"{current_compute.value.units:~P}",
        "Server_compute__source_id": existing_source.id,
        "Server_compute__source_name": existing_source.name,
        "Server_compute__source_link": existing_source.link or "",
    }
    parsed = parse_form_data(raw_form_data, "Server")
    edit_object_from_parsed_data(parsed, server_web)

    assert server_web.modeling_obj.compute.source is existing_source


def test_country_metadata_only_confidence_edit_from_source_table_does_not_require_card_render(rf, minimal_repository):
    """Country source-table metadata autosave should not require a Country object-card template."""
    model_web = ModelWeb(minimal_repository)
    country_source_row = next(
        row for row in model_web.web_explainable_quantities_sources
        if (
            row.modeling_obj_container.class_as_simple_str == "Country"
            and row.attr_name_in_mod_obj_container == "average_carbon_intensity"
        )
    )
    country_web = country_source_row.modeling_obj_container
    raw_form_data = {
        "Country_average_carbon_intensity__confidence": "medium",
        "csrfmiddlewaretoken": "token",
        "recomputation": "",
    }
    parsed = parse_form_data(raw_form_data, "Country")

    output = EditObjectUseCase(model_web).execute(
        EditObjectInput(object_id=country_web.efootprint_id, form_data=parsed))

    response = HtmxPresenter(rf.post("/model_builder/edit-object/"), model_web).present_edited_object(output)

    assert output.refresh_cards is False
    assert response.status_code == 200
    assert response.content == b""
    assert country_web.modeling_obj.average_carbon_intensity.confidence == "medium"
