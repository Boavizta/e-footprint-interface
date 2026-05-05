from types import SimpleNamespace, UnionType
from typing import Union, get_args, get_origin

from django.http import Http404
from django.urls import reverse
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.source_objects import Sources
from efootprint.abstract_modeling_classes.utils import css_escape
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.type_annotation_utils import resolve_optional_annotation


def _source_namespace(source_id: str, source_payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id=source_id,
        name=source_payload.get("name", ""),
        link=source_payload.get("link"),
    )


def _source_from_json(source_id: str, sources_block: dict):
    sentinel_sources = {Sources.USER_DATA.id: Sources.USER_DATA, Sources.HYPOTHESIS.id: Sources.HYPOTHESIS}
    if source_id in sentinel_sources:
        return sentinel_sources[source_id]
    return _source_namespace(source_id, sources_block[source_id])


def _available_sources_from_json(sources_block: dict) -> list:
    sources_by_id = {
        source_id: _source_namespace(source_id, source_payload)
        for source_id, source_payload in sources_block.items()
    }
    for sentinel in (Sources.USER_DATA, Sources.HYPOTHESIS):
        sources_by_id.setdefault(sentinel.id, sentinel)
    return sorted(sources_by_id.values(), key=lambda source: source.name)


def _calculated_attribute_names(efootprint_class) -> list[str]:
    calculated_attributes = getattr(efootprint_class, "calculated_attributes", [])
    if isinstance(calculated_attributes, property):
        return calculated_attributes.fget(efootprint_class.__new__(efootprint_class))
    return calculated_attributes


def _is_explainable_object_annotation(annotation) -> bool:
    annotation = resolve_optional_annotation(annotation)
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return any(
            isinstance(arg, type) and issubclass(arg, ExplainableObject)
            for arg in get_args(annotation)
            if arg is not type(None)
        )
    return isinstance(annotation, type) and issubclass(annotation, ExplainableObject)


def _find_modeling_object_payload(system_data: dict, object_id: str) -> tuple[str, dict]:
    for object_type, object_payloads in system_data.items():
        if object_type in MODELING_OBJECT_CLASSES_DICT and object_id in object_payloads:
            return object_type, object_payloads[object_id]
    raise Http404("Unknown source-table row.")


def _raise_if_not_editable_input_attr(efootprint_class, attr_name: str) -> None:
    init_params = get_init_signature_params(efootprint_class)
    if (
        attr_name not in init_params
        or not _is_explainable_object_annotation(init_params[attr_name].annotation)
        or attr_name in _calculated_attribute_names(efootprint_class)
    ):
        raise Http404("Only editable source-table rows have row editors.")


def build_source_table_row_editor_context(repository, object_id: str, attr_name: str) -> dict:
    try:
        system_data = repository.get_system_data()
        object_type, object_payload = _find_modeling_object_payload(system_data, object_id)
        efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
        _raise_if_not_editable_input_attr(efootprint_class, attr_name)

        attr_payload = object_payload[attr_name]
        sources_block = system_data.get("Sources", {}) or {}
        source = _source_from_json(attr_payload["source"], sources_block)
    except (AttributeError, KeyError, TypeError) as exc:
        raise Http404("Unknown source-table row.") from exc

    eq = SimpleNamespace(
        web_id=css_escape(f"{attr_name}-in-{object_id}"),
        source=source,
        comment=attr_payload.get("comment"),
    )

    return {
        "eq": eq,
        "available_sources": _available_sources_from_json(sources_block),
        "field_name_prefix": f"{object_type}_{attr_name}",
        "edit_object_url": reverse("edit-object", kwargs={"object_id": object_id}),
    }
