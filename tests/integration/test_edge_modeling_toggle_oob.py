"""Integration tests for the edge_modeling_toggle OOB region.

Follows the Step 1 constraint-change OOB pattern: no browser, real
InMemorySystemRepository + ModelWeb + use cases.
"""
import json

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
from model_builder.application.use_cases.delete_object import DeleteObjectInput, DeleteObjectUseCase
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.hardware.edge.edge_component_base_web import EdgeComponentWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_SYSTEM_DATA
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values


TOGGLE_REGION = "edge_modeling_toggle"


def _fresh_repository() -> InMemorySystemRepository:
    return InMemorySystemRepository(initial_data=DEFAULT_SYSTEM_DATA)


def _create(repository, object_type: str, name: str, parent_id=None, **overrides):
    post_data = create_post_data_from_class_default_values(name, object_type, **overrides)
    parsed = parse_form_data(post_data, object_type)
    return CreateObjectUseCase(repository).execute(
        CreateObjectInput(object_type=object_type, form_data=parsed, parent_id=parent_id))


def test_creating_first_edge_object_emits_toggle_region():
    repository = _fresh_repository()
    baseline = ModelWeb(repository)
    assert baseline.has_edge_objects is False

    output = _create(repository, "EdgeDevice", "Sensor", components="")

    assert output.model_web.has_edge_objects is True
    assert TOGGLE_REGION in {r.key for r in output.oob_regions}


def test_deleting_last_edge_object_emits_toggle_region():
    repository = _fresh_repository()
    create_output = _create(repository, "EdgeDevice", "Sensor", components="")
    edge_device_id = create_output.created_object_id

    assert ModelWeb(repository).has_edge_objects is True

    delete_output = DeleteObjectUseCase(ModelWeb(repository)).execute(
        DeleteObjectInput(object_id=edge_device_id))

    assert ModelWeb(repository).has_edge_objects is False
    assert TOGGLE_REGION in {r.key for r in delete_output.oob_regions}


def test_edit_without_edge_flip_does_not_emit_toggle_region():
    repository = _fresh_repository()
    create_output = _create(repository, "EdgeDevice", "Sensor", components="")
    edge_device_id = create_output.created_object_id

    edit_post_data = create_post_data_from_class_default_values("Renamed Sensor", "EdgeDevice", components="")
    parsed = parse_form_data(edit_post_data, "EdgeDevice")
    edit_output = EditObjectUseCase(ModelWeb(repository)).execute(
        EditObjectInput(object_id=edge_device_id, form_data=parsed))

    assert TOGGLE_REGION not in {r.key for r in edit_output.oob_regions}


def test_creating_second_edge_object_does_not_re_emit_toggle_region():
    repository = _fresh_repository()
    _create(repository, "EdgeDevice", "Sensor 1", components="")

    output = _create(repository, "EdgeDevice", "Sensor 2", components="")

    assert TOGGLE_REGION not in {r.key for r in output.oob_regions}


def test_edge_device_subclass_overrides_preserve_toggle_region():
    """EdgeDeviceGroupWeb / EdgeDeviceBaseWeb / EdgeComponentWeb override *_side_effects.

    Their super() chain must propagate the edge_modeling_toggle region. Use a stub
    instance pointed at a model where has_edge_objects_cached lags the real state
    (mimics what happens during a mutation), and assert the region is emitted.
    """
    for web_class in (EdgeDeviceGroupWeb, EdgeDeviceBaseWeb, EdgeComponentWeb):
        repository = _fresh_repository()
        _create(repository, "EdgeDevice", "Sensor", components="")
        model_web = ModelWeb(repository)
        # Force the cache to lag the real state so the diff detects a flip.
        model_web.has_edge_objects_cached = False

        stub = web_class.__new__(web_class)
        stub.model_web = model_web
        regions = stub.delete_side_effects()

        assert TOGGLE_REGION in {r.key for r in regions}, (
            f"{web_class.__name__}.delete_side_effects dropped the edge_modeling_toggle region")
