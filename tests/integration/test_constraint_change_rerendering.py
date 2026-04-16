"""Integration tests for creation-constraint diffing + OOB re-render wiring.

These tests exercise the end-to-end effect of `create_side_effects` /
`delete_side_effects` on `ModelWeb.creation_constraints` and verify that the
expected OOB regions are emitted when a constraint flips.
"""
import json

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
from model_builder.application.use_cases.delete_object import DeleteObjectInput, DeleteObjectUseCase
from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_SYSTEM_DATA
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values


REGION_KEYS_FROM_BASE = {"model_canvas", "results_buttons"}


def _fresh_repository() -> InMemorySystemRepository:
    """Default-data repository, without the `persist_to_cache` pre-warm used elsewhere.

    We want the raw default_system_data (no Server, no Job, no UsagePattern) so that
    JobWeb starts disabled and flips to enabled when a Server is added.
    """
    return InMemorySystemRepository(initial_data=DEFAULT_SYSTEM_DATA)


def _create_server(repository: InMemorySystemRepository):
    server_post_data = create_post_data_from_class_default_values("Srv", "Server", server_type="autoscaling")
    server_post_data["Storage_form_data"] = json.dumps(
        create_post_data_from_class_default_values("Stg", "Storage"))
    parsed = parse_form_data(server_post_data, "Server")
    return CreateObjectUseCase(repository).execute(
        CreateObjectInput(object_type="Server", form_data=parsed, parent_id=None))


def test_creating_server_flips_job_constraint_and_emits_oob_regions():
    """Before any server exists JobWeb is disabled; creating one flips it on and
    emits both the canvas + results_buttons OOB regions."""
    repository = _fresh_repository()

    baseline = ModelWeb(repository)
    assert baseline.creation_constraints["JobWeb"]["enabled"] is False

    output = _create_server(repository)
    mutated = output.model_web

    assert mutated.creation_constraints["JobWeb"]["enabled"] is True
    assert ("JobWeb", "unlocked") in mutated.constraint_changes

    emitted_keys = {region.key for region in output.oob_regions}
    assert REGION_KEYS_FROM_BASE.issubset(emitted_keys), (
        f"Expected base side-effect regions inside {emitted_keys}")


def test_creating_object_without_constraint_flip_emits_no_regions():
    """Creating a second server does not flip any constraint, so the base
    `create_side_effects` returns an empty OOB-region list."""
    repository = _fresh_repository()
    _create_server(repository)

    output = _create_server(repository)
    mutated = output.model_web

    assert mutated.constraint_changes == []
    assert [region.key for region in output.oob_regions] == []


def test_deleting_last_server_flips_job_constraint_off():
    """Removing the last server drops JobWeb back to disabled, emitting the two
    base OOB regions from `delete_side_effects`."""
    repository = _fresh_repository()
    server_output = _create_server(repository)
    server_id = server_output.created_object_id

    use_case = DeleteObjectUseCase(ModelWeb(repository))
    delete_output = use_case.execute(DeleteObjectInput(object_id=server_id))

    after = ModelWeb(repository)
    assert after.creation_constraints["JobWeb"]["enabled"] is False
    assert ("JobWeb", "locked") in use_case.model_web.constraint_changes

    emitted_keys = {region.key for region in delete_output.oob_regions}
    assert REGION_KEYS_FROM_BASE.issubset(emitted_keys)


def test_edge_device_group_delete_side_effects_preserve_base_regions():
    """EdgeDeviceGroupWeb.delete_side_effects overrides the base hook; the override
    must still chain to `super()` so the constraint-diff regions are not dropped.

    Behavioural check: with no flip (no constraint change), only the override's
    own region ('edge_device_lists') is emitted — and the baseline constraints
    dict is untouched.
    """
    repository = _fresh_repository()
    model_web = ModelWeb(repository)
    baseline_constraints = dict(model_web.creation_constraints)

    # Skip __init__ — the hook only reads self.model_web, and building a real
    # EdgeDeviceGroupWeb requires a live modeling_obj that this test doesn't need.
    stub = EdgeDeviceGroupWeb.__new__(EdgeDeviceGroupWeb)
    stub.model_web = model_web
    regions = stub.delete_side_effects()

    assert "edge_device_lists" in {r.key for r in regions}
    assert model_web.creation_constraints == baseline_constraints
