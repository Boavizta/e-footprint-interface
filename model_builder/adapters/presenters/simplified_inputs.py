"""Current modeling inputs grouped by their actual type and owner for both focused views."""
from collections import defaultdict

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.adapters.forms.timeseries_builder_registry import can_edit_timeseries
from model_builder.adapters.label_resolver import LabelResolver
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.domain.services.simplified_inputs import FieldAddress, build_catalog, normalize_definition


def input_catalog(model_web):
    return build_catalog(model_web, can_edit_timeseries=can_edit_timeseries)


def _preview(value):
    if isinstance(value, EmptyExplainableObject):
        return "No value"
    if isinstance(value, ModelingObject):
        return value.name
    if isinstance(value, list):
        return ", ".join(item.name for item in value)
    return str(value)


def build_workspace_context(model_web, *, configure=False, catalog=None):
    catalog = catalog or input_catalog(model_web)
    definition = normalize_definition(model_web.repository.interface_config.get("simplified_inputs"))
    attributes_by_owner = defaultdict(set)
    for address, descriptor in catalog.fields.items():
        setting = definition["fields"].get(address.object_id, {}).get(address.attribute, {})
        if descriptor.eligible and (configure or setting.get("included")):
            attributes_by_owner[address.object_id].add(address.attribute)
    unavailable_inputs = []
    if configure:
        for address, descriptor in catalog.fields.items():
            if descriptor.eligible or address not in catalog.dependents:
                continue
            owner = model_web.flat_efootprint_objs_dict[address.object_id]
            label = FieldUIConfigProvider.get_config(address.attribute, owner.efootprint_class.__name__)["label"]
            unavailable_inputs.append(f"{owner.name}: {label} cannot be included because a required input has no supported editor.")
    groups = {}
    form_builder = FormContextBuilder(model_web)
    system_id = model_web.system.efootprint_id
    first = True
    for owner_id, attributes in attributes_by_owner.items():
        web_obj = model_web.get_web_object_from_efootprint_id(owner_id)
        type_name = web_obj.class_as_simple_str
        group = groups.setdefault(type_name, {"object_type": LabelResolver.get_class_label(type_name),
                                             "dom_id": f"si-{system_id}-type-{type_name}", "objects": []})
        fields = []
        for editor in form_builder.build_input_fields(web_obj, attributes):
            attribute = editor["attr_name"]
            address = FieldAddress(owner_id, attribute)
            descriptor = catalog.fields[address]
            fields.append({"address": address, "dom_id": f"si-{system_id}-{owner_id}-{attribute}",
                           "setting": definition["fields"].get(owner_id, {}).get(
                               attribute, {"included": False, "help": ""}),
                           "editor": editor, "preview": _preview(getattr(web_obj.modeling_obj, attribute)),
                           "controller": descriptor.controller,
                           "dependents": [f"si-{system_id}-{dep.object_id}-{dep.attribute}"
                                          for dep in catalog.dependents.get(address, ())]})
        group["objects"].append({"object_id": owner_id, "dom_id": f"si-{system_id}-object-{owner_id}",
                                 "name": web_obj.name, "fields": fields, "open": first,
                                 "selected_count": sum(field["setting"]["included"] for field in fields)})
        first = False
    return {"system_id": system_id, "slot": getattr(model_web.repository, "slot", 0),
            "configure": configure, "title": definition["title"], "guidance": definition["guidance"],
            "groups": list(groups.values()), "unavailable_inputs": unavailable_inputs}


def definition_from_form(data):
    """Read the complete settings form; missing checkboxes are excluded, help remains authored."""
    fields = {}
    for key in data:
        if key.startswith("help:"):
            _, owner_id, attribute = key.split(":", 2)
            included = f"include:{owner_id}:{attribute}" in data
            help_text = data[key]
            if included or help_text:
                fields.setdefault(owner_id, {})[attribute] = {"included": included, "help": help_text}
    return {"title": data.get("title", ""), "guidance": data.get("guidance", ""), "fields": fields}
