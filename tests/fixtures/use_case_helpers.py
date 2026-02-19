from __future__ import annotations

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
from model_builder.application.use_cases.delete_object import DeleteObjectInput, DeleteObjectUseCase
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb


def create_object(repository, post_data: dict, parent_id: str | None = None) -> str:
    """Parse post_data, run CreateObjectUseCase, return the created object id."""
    object_type = post_data["type_object_available"]
    parsed_form = parse_form_data(post_data, object_type)
    output = CreateObjectUseCase(repository).execute(
        CreateObjectInput(object_type=object_type, form_data=parsed_form, parent_id=parent_id))
    return output.created_object_id


def edit_object(repository, object_id: str, object_type: str, raw_form_data: dict) -> None:
    """Parse raw_form_data, run EditObjectUseCase for object_id."""
    parsed_form = parse_form_data(raw_form_data, object_type)
    EditObjectUseCase(ModelWeb(repository)).execute(EditObjectInput(object_id=object_id, form_data=parsed_form))


def delete_object(repository, object_id: str) -> None:
    """Run DeleteObjectUseCase for object_id."""
    DeleteObjectUseCase(ModelWeb(repository)).execute(DeleteObjectInput(object_id=object_id))
