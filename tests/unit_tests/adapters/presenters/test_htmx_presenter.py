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


@pytest.mark.parametrize("refresh_cards,replaces_primary_render", [(True, False), (False, False), (True, True)])
def test_normal_edit_refreshes_every_affected_owner_and_mirror_once_without_canvas_overlap(
    refresh_cards, replaces_primary_render
):
    import json
    from unittest.mock import MagicMock
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
    with patch("model_builder.adapters.presenters.htmx_presenter.render_to_string", return_value="card") as render_card:
        response = presenter.present_edited_object(output)
        assert render_card.call_count == 2
    content = response.content.decode()
    assert content.count("outerHTML:#Journey-a") == content.count("outerHTML:#Journey-b") == 1
    notices = json.loads(response["HX-Trigger-After-Settle"])["displayToastAndHighlightObjects"]["notices"]
    assert notices == ["Job A: Authored resolution changed to 480p.", "Job B: Authored resolution changed to 480p."]
    assert json.loads(response["HX-Trigger"]) == {"resetLeaderLines": ""}

    output.oob_regions = [OobRegion.make("canvas")]
    with patch("model_builder.adapters.presenters.htmx_presenter.oob_regions_cover_all_cards", return_value=True), \
         patch("model_builder.adapters.presenters.htmx_presenter.render_oob_regions", return_value="canvas") as render_canvas, \
         patch.object(presenter, "_render_top_parent_cards") as render_cards:
        response = presenter.present_edited_object(output)
        render_cards.assert_not_called()
        render_canvas.assert_called_once_with(model, output.oob_regions)
    assert "canvas" in response.content.decode()
    assert json.loads(response["HX-Trigger-After-Settle"])["displayToastAndHighlightObjects"]["notices"] == notices
