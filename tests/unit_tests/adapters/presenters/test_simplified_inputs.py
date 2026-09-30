from django.template.loader import render_to_string

from model_builder.adapters.forms.form_field_generator import generate_dynamic_form
from model_builder.adapters.presenters.simplified_inputs import build_workspace_context


def test_configure_groups_current_inputs_by_true_owner_and_keeps_existing_labels(minimal_model_web):
    context = build_workspace_context(minimal_model_web, configure=True)
    objects = [obj for group in context["groups"] for obj in group["objects"]]
    owners = {obj["object_id"]: obj for obj in objects}
    server = minimal_model_web.servers[0].modeling_obj
    assert server.id in owners and server.storage.id in owners
    assert [obj["open"] for obj in objects].count(True) == 1
    count = next(field for field in owners[server.id]["fields"] if field["address"].attribute == "fixed_nb_of_instances")
    assert count["editor"]["input_type"] == "explainable_quantity"
    assert count["editor"]["default"] == ""
    assert count["preview"] == "No value"
    assert count["editor"]["allows_empty"]
    assert count["dom_id"] == f"si-{context['system_id']}-{server.id}-fixed_nb_of_instances"
    assert not any(field["address"].attribute == "storage_capacity" for field in owners[server.id]["fields"])
    html = render_to_string("model_builder/simplified_inputs/workspace.html", context)
    assert count["editor"]["label"].capitalize() in html
    assert "data-selected-object-filter" in html


def test_selected_view_contains_only_saved_fields_and_authored_help(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    minimal_model_web.repository.interface_config = {"simplified_inputs": {
        "title": "Keep My Title", "guidance": "My Guidance", "fields": {
            server.id: {"lifespan": {"included": True, "help": "Preserve This Help"},
                        "power": {"included": False, "help": "Retained"}}}}}
    context = build_workspace_context(minimal_model_web)
    fields = [field for group in context["groups"] for obj in group["objects"] for field in obj["fields"]]
    assert [field["address"].attribute for field in fields] == ["lifespan"]
    html = render_to_string("model_builder/simplified_inputs/workspace.html", context)
    assert "Preserve This Help" in html
    assert "data-selection-controls" not in html
    assert context["title"] == "Keep My Title"


def test_normal_forms_still_exclude_instance_count(minimal_model_web):
    server = minimal_model_web.servers[0]
    normal, advanced, _ = generate_dynamic_form(server.class_as_simple_str, server.modeling_obj.__dict__,
                                                minimal_model_web, obj_to_edit=server)
    assert "fixed_nb_of_instances" not in {field["attr_name"] for field in normal + advanced}
