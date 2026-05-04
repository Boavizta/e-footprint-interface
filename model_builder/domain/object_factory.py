"""Domain object factory for creating and editing efootprint objects.

This module contains the core domain logic for constructing efootprint objects
from parsed attribute data. It handles type conversion, source tracking,
and object reference resolution.

Note: This module expects pre-parsed data (clean attribute names without prefixes).
Use adapters/forms/form_data_parser.py to parse HTTP form data before calling these functions.
"""
from copy import copy, deepcopy
from typing import Any, Dict, List, get_origin, get_args, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import Sources
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.type_annotation_utils import resolve_optional_annotation

if TYPE_CHECKING:
    from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb
    from model_builder.domain.entities.web_core.model_web import ModelWeb


def _build_explainable_object_dict_entries(value: Dict[str, Any], model_web: "ModelWeb", attr_name: str) -> dict:
    entries = {}
    for key_id, explainable_value_dict in value.items():
        if key_id not in model_web.flat_efootprint_objs_dict:
            raise ValueError(f"Unknown modeling object id '{key_id}' in {attr_name}.")
        explainable_obj = ExplainableObject.from_json_dict(explainable_value_dict)
        explainable_obj.source = Sources.USER_DATA
        entries[model_web.flat_efootprint_objs_dict[key_id]] = explainable_obj
    return entries


def _apply_metadata(
    explainable_object: ExplainableObject,
    parsed_value: Dict[str, Any],
    available_sources: list,
    pending_sources: Dict[str, Any],
) -> None:
    """Set source, confidence, and comment on an ExplainableObject from parsed form data.

    parsed_value must be a dict (the structured output of parse_form_data for this attribute).
    pending_sources is a per-submission dict shared across all _apply_metadata calls in the
    same create/edit invocation. It is keyed by the client-submitted source id and lets two
    fields submitting the same new (unknown) id resolve to the *same* Source instance.
    Source resolution order:
      1. available_sources (model's existing sources, matched by id)
      2. pending_sources (new sources created earlier in the same submission, matched by id)
      3. Mint a new Source, using the submitted id so the same id resolves to the same instance
         within one submission (enables same-form cross-field source sharing).
    When no id is submitted (legacy / no-JS fallback): mint from name+link without dedup.
    Confidence: carry submitted value; None if absent or invalid (client clears it on value change).
    Comment: always carry submitted value (None if empty/absent).
    """
    source_dict = parsed_value.get("source")
    if source_dict:
        source_id = source_dict.get("id") or None
        source_name = source_dict.get("name") or ""
        source_link = source_dict.get("link") or None
        if source_id:
            matched = next((s for s in available_sources if s.id == source_id), None)
            if matched is not None:
                explainable_object.source = matched
            else:
                if source_id not in pending_sources:
                    pending_sources[source_id] = Source(source_name, source_link, id=source_id)
                explainable_object.source = pending_sources[source_id]
        elif source_name:
            explainable_object.source = Source(source_name, source_link)
        else:
            explainable_object.source = Sources.USER_DATA
    else:
        explainable_object.source = Sources.USER_DATA

    raw_confidence = parsed_value.get("confidence")
    explainable_object.confidence = (
        raw_confidence if raw_confidence in ("low", "medium", "high") else None
    )

    explainable_object.comment = parsed_value.get("comment") or None


def create_efootprint_obj_from_parsed_data(
    parsed_data: Dict[str, Any], model_web: "ModelWeb", object_type: str
) -> ModelingObject:
    """Create an efootprint object from parsed attribute data.

    Args:
        parsed_data: Dict with clean attribute names (no prefixes), nested fields as dicts,
                    and optional "_units" key for unit mappings
        model_web: ModelWeb instance for resolving object references
        object_type: The efootprint class name (e.g., "Server", "Job")

    Returns:
        New efootprint ModelingObject instance
    """
    from model_builder.domain.efootprint_to_web_mapping import get_corresponding_web_class

    new_efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[object_type]
    init_sig_params = get_init_signature_params(new_efootprint_obj_class)
    corresponding_web_class = get_corresponding_web_class(new_efootprint_obj_class)

    default_values = deepcopy(new_efootprint_obj_class.default_values)
    for default_web_attr in corresponding_web_class.default_values:
        default_values[default_web_attr] = copy(corresponding_web_class.default_values[default_web_attr])

    obj_creation_kwargs = {}
    available_sources = model_web.available_sources
    pending_sources: Dict[str, Source] = {}

    for attr_name, value in parsed_data.items():
        if attr_name == "name":
            obj_creation_kwargs[attr_name] = value
            continue
        if attr_name not in init_sig_params:
            continue
        annotation = init_sig_params[attr_name].annotation
        annotation = resolve_optional_annotation(annotation)
        annotation_origin = get_origin(annotation)
        if annotation_origin and annotation_origin in (list, List):
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            obj_creation_kwargs[attr_name] = [
                model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                for obj_id in value
            ]
        elif (annotation_origin is not None and isinstance(annotation_origin, type)
              and issubclass(annotation_origin, ExplainableObjectDict)) or (
                isinstance(annotation, type) and issubclass(annotation, ExplainableObjectDict)):
            obj_creation_kwargs[attr_name] = ExplainableObjectDict(
                _build_explainable_object_dict_entries(value, model_web, attr_name))
        elif issubclass(annotation, ModelingObject):
            mod_obj_attribute_object_type_str = annotation.__name__
            obj_to_add = model_web.get_efootprint_object_from_efootprint_id(value, mod_obj_attribute_object_type_str)
            obj_creation_kwargs[attr_name] = obj_to_add
        elif issubclass(annotation, ExplainableObject):
            explainable_object = ExplainableObject.from_json_dict(value)
            _apply_metadata(explainable_object, value, available_sources, pending_sources)
            obj_creation_kwargs[attr_name] = explainable_object

    return new_efootprint_obj_class.from_defaults(**obj_creation_kwargs)


def edit_object_from_parsed_data(parsed_data: Dict[str, Any], obj_to_edit: "ModelingObjectWeb",
                                 update_system_data=False):
    """Edit an efootprint object from parsed attribute data.

    Args:
        parsed_data: Dict with clean attribute names (no prefixes), nested fields as dicts,
                    and optional "_units" key for unit mappings
        obj_to_edit: The web wrapper of the object to edit
        update_system_data: Whether to update system data after editing

    Returns:
        Tuple of (edited_object, had_non_name_changes: bool, name_changed: bool)
    """
    model_web = obj_to_edit.model_web
    available_sources = model_web.available_sources
    pending_sources: Dict[str, Source] = {}
    init_sig_params = get_init_signature_params(obj_to_edit.efootprint_class)

    changes_list = []
    old_name = obj_to_edit.name

    for attr_name, value in parsed_data.items():
        if attr_name not in init_sig_params or attr_name == "self":
            continue
        if attr_name == "name":
            obj_to_edit.set_efootprint_value(attr_name, value)
            continue

        annotation = init_sig_params[attr_name].annotation
        annotation = resolve_optional_annotation(annotation)
        annotation_origin = get_origin(annotation)
        current_value = getattr(obj_to_edit.modeling_obj, attr_name)

        if annotation_origin and annotation_origin in (list, List):
            current_mod_obj_ids = [mod_obj.efootprint_id for mod_obj in getattr(obj_to_edit, attr_name)]
            if value == current_mod_obj_ids:
                continue
            logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            changes_list.append([
                current_value,
                [model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                 for obj_id in value]])
            continue

        is_explainable_object_dict = (
            (annotation_origin is not None and isinstance(annotation_origin, type)
             and issubclass(annotation_origin, ExplainableObjectDict))
            or (isinstance(annotation, type) and issubclass(annotation, ExplainableObjectDict)))
        if is_explainable_object_dict:
            new_entries = _build_explainable_object_dict_entries(value, model_web, attr_name)
            if new_entries != current_value:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                changes_list.append([current_value, ExplainableObjectDict(new_entries)])
            continue

        if issubclass(annotation, ModelingObject):
            new_mod_obj_id = value
            current_mod_obj_id = getattr(obj_to_edit, attr_name).efootprint_id
            if new_mod_obj_id != current_mod_obj_id:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                mod_obj_attribute_object_type_str = annotation.__name__
                obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                    new_mod_obj_id, mod_obj_attribute_object_type_str)
                changes_list.append([current_value, obj_to_add])
            continue

        if issubclass(annotation, ExplainableObject):
            if value.get("_metadata_only"):
                _apply_metadata(current_value, value, available_sources, pending_sources)
                continue
            new_value = ExplainableObject.from_json_dict(value)
            new_value.set_label(current_value.label)
            value_changed = new_value != current_value
            _apply_metadata(new_value, value, available_sources, pending_sources)
            if value_changed:
                changes_list.append([current_value, new_value])
            else:
                # ModelingUpdate skips same-value changes; apply metadata directly since
                # confidence/comment/source don't affect calculations.
                metadata_changed = (
                    new_value.source is not current_value.source
                    or new_value.confidence != current_value.confidence
                    or new_value.comment != current_value.comment
                )
                if metadata_changed:
                    current_value.source = new_value.source
                    current_value.confidence = new_value.confidence
                    current_value.comment = new_value.comment

    if changes_list:
        ModelingUpdate(changes_list, compute_previous_system_footprints=False)

    if update_system_data:
        model_web.persist_to_cache()

    return obj_to_edit, bool(changes_list), obj_to_edit.name != old_name
