from types import SimpleNamespace
from unittest.mock import patch

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
