"""Catalog-backed settings for compact bookmarks and provisional constructor fields."""
from model_builder.adapters.forms.timeseries_builder_registry import can_edit_timeseries
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.domain.services.simplified_inputs import FieldAddress, build_catalog, normalize_definition


def included_requirement(model_web, address, *, definition=None):
    definition = definition if definition is not None else normalize_definition(model_web.repository.interface_config.get("simplified_inputs"))
    if not definition["fields"].get(address.object_id, {}).get(address.attribute, {}).get("included"):
        return None
    owner = model_web.flat_efootprint_objs_dict[address.object_id]
    return {"object_id": address.object_id, "attribute": address.attribute,
            "label": f"{owner.name} · {FieldUIConfigProvider.get_config(address.attribute, owner.efootprint_class.__name__)["label"]}"}


def bookmark_context(model_web, address, *, catalog=None, definition=None, suffix="panel"):
    catalog = catalog if catalog is not None else build_catalog(model_web, can_edit_timeseries=can_edit_timeseries)
    descriptor = catalog.fields.get(address)
    if descriptor is None or not descriptor.eligible:
        return None
    definition = definition if definition is not None else normalize_definition(
        model_web.repository.interface_config.get("simplified_inputs"))
    return {"address": address, "attribute": address.attribute, "dom_id": f"bookmark-{address.object_id}-{address.attribute}-{suffix}",
            "setting": definition["fields"].get(address.object_id, {}).get(address.attribute,
                                                                        {"included": False, "help": ""}),
            "required_by": included_requirement(model_web, descriptor.controller, definition=definition) if descriptor.controller else None}
