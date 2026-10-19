from types import SimpleNamespace
from unittest.mock import patch

import pytest

from model_builder.adapters.presenters.htmx_presenter import HtmxPresenter
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex
from model_builder.application.use_cases import CreateObjectOutput, DeleteObjectOutput, EditObjectOutput


class DictSession(dict):
    session_key = "session-key"
    modified = False


def _assert_one_storage_status_oob(response):
    content = response.content.decode()
    assert content.count('id="workspace-storage-status"') == 1
    assert 'hx-swap-oob="innerHTML:#workspace-storage-status"' in content
    assert "4 MB of 5 MB" in content


def test_successful_crud_presentations_append_one_metadata_status_oob(settings):
    session = DictSession()
    WorkspaceIndex(session).set_slot_size(0, 4 * 1024 * 1024)
    request = SimpleNamespace(session=session)
    model_web = SimpleNamespace(constraint_changes=[])
    presenter = HtmxPresenter(request, model_web)

    created = CreateObjectOutput(
        created_object_id="created",
        created_object_name="Created",
        created_object_type="Server",
        template_name="server",
        web_id="Server-created",
        replaces_primary_render=True,
    )
    edited = EditObjectOutput(
        edited_object_id="edited",
        edited_object_name="Edited",
        edited_object_type="Server",
        template_name="server",
        web_id="Server-edited",
        replaces_primary_render=True,
    )
    deleted = DeleteObjectOutput(deleted_object_name="Deleted", deleted_object_type="Server")

    with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 5):
        responses = [
            presenter.present_created_object(created),
            presenter.present_edited_object(edited),
            presenter.present_deleted_object(deleted),
        ]

    for response in responses:
        assert response.status_code == 200
        _assert_one_storage_status_oob(response)
    assert responses[-1]["HX-Reswap"] == "none"


def test_creation_companion_notice_keeps_authored_name_as_text(minimal_model_web):
    import json
    from model_builder.domain.services.simplified_inputs import FieldAddress

    owner = minimal_model_web.servers[0].modeling_obj
    owner.name = "<Study & code>"
    model = SimpleNamespace(constraint_changes=[], flat_efootprint_objs_dict={owner.id: owner})
    output = CreateObjectOutput(owner.id, owner.name, "Server", "server", f"Server-{owner.id}",
                                replaces_primary_render=True, simplified_added={FieldAddress(owner.id, "compute")})
    response = HtmxPresenter(SimpleNamespace(session=DictSession()), model).present_created_object(output)
    messages = json.loads(response["HX-Trigger-After-Settle"])["displayToastAndHighlightObjects"]["constraint_messages"]
    assert messages == ["<Study & code> · compute was included in Simplified inputs."]


@pytest.mark.parametrize("refresh_cards,replaces_primary_render", [(True, False), (False, False), (True, True)])
def test_normal_edit_refreshes_every_affected_owner_and_mirror_once_without_canvas_overlap(
    refresh_cards, replaces_primary_render
):
    import json
    from unittest.mock import MagicMock
    from django.template.loader import render_to_string
    from efootprint.abstract_modeling_classes.source_objects import SourceObject
    from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
        EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
    from model_builder.domain.object_factory import AutomaticInputChange, InputEditResult
    from model_builder.domain.oob_region import OobRegion

    api = EcoLogitsVideoGenExternalAPI.from_defaults("Video API")
    jobs = [EcoLogitsVideoGenExternalAPIJob.from_defaults(name, external_api=api) for name in ["Job A", "Job B"]]
    top_a = SimpleNamespace(web_id="Journey-a", template_name="journey")
    top_b = SimpleNamespace(web_id="Journey-b", template_name="journey")
    cards = [SimpleNamespace(top_parent=top_a), SimpleNamespace(top_parent=top_b)]
    web_objects = {job.id: SimpleNamespace(mirrored_cards=cards) for job in jobs}
    model = MagicMock(constraint_changes=[])
    model.get_web_object_from_efootprint_id.side_effect = web_objects.__getitem__
    model.get_web_objects_from_efootprint_type.return_value = []
    presenter = HtmxPresenter(SimpleNamespace(session=DictSession()), model)
    output = EditObjectOutput(api.id, api.name, "EcoLogitsVideoGenExternalAPI", "api", "API-id",
        refresh_cards=refresh_cards, replaces_primary_render=replaces_primary_render,
        input_edit_result=InputEditResult(
            automatic_changes=[AutomaticInputChange((job, "resolution"), job.resolution,
                                                     SourceObject("480p", label="Authored resolution")) for job in jobs],
            affected_inputs={(api, "model_name"), *((job, "resolution") for job in jobs)}))
    def render(template, context):
        return render_to_string(template, context) if template.endswith("input_repair_notices.html") else "card"

    with patch("model_builder.adapters.presenters.htmx_presenter.render_to_string", side_effect=render) as render_card:
        response = presenter.present_edited_object(output)
        assert sum(call.args[0].endswith("_card.html") for call in render_card.call_args_list) == 2
    content = response.content.decode()
    assert content.count("outerHTML:#Journey-a") == content.count("outerHTML:#Journey-b") == 1
    toast = json.loads(response["HX-Trigger-After-Settle"])["displayToastAndHighlightObjects"]
    assert toast["notice_target"] == "input-repair-notices"
    assert "notices" not in toast
    notices = "Job A: Authored resolution changed to 480p. — Job B: Authored resolution changed to 480p."
    assert notices in content
    assert json.loads(response["HX-Trigger"]) == {"resetLeaderLines": ""}

    output.oob_regions = [OobRegion.make("canvas")]
    with patch("model_builder.adapters.presenters.htmx_presenter.oob_regions_cover_all_cards", return_value=True), \
         patch("model_builder.adapters.presenters.htmx_presenter.render_oob_regions", return_value="canvas") as render_canvas, \
         patch.object(presenter, "_render_top_parent_cards") as render_cards:
        response = presenter.present_edited_object(output)
        render_cards.assert_not_called()
        render_canvas.assert_called_once_with(model, output.oob_regions)
    assert "canvas" in response.content.decode()
    assert notices in response.content.decode()
    assert json.loads(response["HX-Trigger-After-Settle"])["displayToastAndHighlightObjects"] == toast


@pytest.mark.parametrize("editor", ["normal", "simplified"])
def test_large_accepted_repair_batch_carries_every_notice_in_body_with_bounded_headers(minimal_system, rf, editor):
    import json
    import re
    from html import unescape
    from efootprint.abstract_modeling_classes.source_objects import SourceObject
    from efootprint.abstract_modeling_classes.explainable_object_dict import to_weighted_explainable_object_dict
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
        EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
    from model_builder.adapters.repositories import InMemorySystemRepository
    from model_builder.adapters.presenters.simplified_inputs import input_catalog, present_edited_input
    from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
    from model_builder.application.use_cases.simplified_inputs import (
        EditSimplifiedInput, EditSimplifiedInputUseCase, UpdateSimplifiedDefinitionUseCase)
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.domain.services.simplified_inputs import FieldAddress

    api = EcoLogitsVideoGenExternalAPI.from_defaults("Shared video API")
    jobs = [EcoLogitsVideoGenExternalAPIJob.from_defaults(
        f"Video job {index:03} <Study & code>", external_api=api, resolution=SourceObject("1080p (1920 x 1080)"))
        for index in range(200)]
    journey = next(iter(minimal_system.usage_patterns[0].usage_journeys))
    next(iter(journey.uj_steps)).jobs = to_weighted_explainable_object_dict(jobs)
    repository = InMemorySystemRepository(initial_data=system_to_json(minimal_system, save_computed_state=False),
                                          max_payload_size_mb=5)
    model = ModelWeb(repository)
    expected_notices = [f"{job.name}: {job.resolution.label} changed to 480p (854 x 480)." for job in jobs]
    request = rf.post("/model_builder/")
    request.session = DictSession()
    if editor == "normal":
        output = EditObjectUseCase(model, input_catalog).execute(EditObjectInput(api.id, {
            "provider": {"value": "bytedance"}, "model_name": {"value": "seedance-1.0"}}))
        assert len(output.input_edit_result.automatic_changes) == len(jobs)
        response = HtmxPresenter(request, model).present_edited_object(output)
    else:
        catalog = input_catalog(model)
        UpdateSimplifiedDefinitionUseCase(repository, catalog).execute({
            "fields": {api.id: {"provider": {"included": True}}}})
        output = EditSimplifiedInputUseCase(model, catalog).execute(
            EditSimplifiedInput(FieldAddress(api.id, "provider"), {"value": "bytedance"}))
        expected_notices.append(f"{api.name}: {api.model_name.label} changed to seedance-1.0.")
        assert sorted(output.notices) == sorted(expected_notices)
        response = present_edited_input(request, model, FieldAddress(api.id, "provider"), output, catalog)
    assert len(json.dumps(expected_notices).encode()) > 8 * 1024

    assert len(response.serialize_headers()) < 1024
    holder_pattern = (r'<div id="input-repair-notices"[^>]*>(.*?)</div>' if editor == "normal"
                      else r'<p id="si-[^"]+-notice"[^>]*hx-swap-oob="true">(.*?)</p>')
    holder = re.search(holder_pattern, response.content.decode(), re.DOTALL)
    assert holder is not None
    if editor == "normal":
        assert sorted(unescape(holder[1]).split(" — ")) == sorted(expected_notices)
    else:
        assert unescape(holder[1]) == " ".join(output.notices)
    assert "<Study" not in holder[1]
    assert "&lt;Study &amp; code&gt;" in holder[1]
