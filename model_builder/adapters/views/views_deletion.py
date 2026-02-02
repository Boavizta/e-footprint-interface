import json

from efootprint.utils.tools import time_it

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.application.use_cases import DeleteObjectUseCase, DeleteObjectInput
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error


@time_it
def ask_delete_object(request, object_id):
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    web_obj = model_web.get_web_object_from_efootprint_id(object_id)

    # Check if deletion is allowed and get context
    use_case = DeleteObjectUseCase(model_web)
    check_result = use_case.check_can_delete(object_id)

    # Present the confirmation modal
    presenter = HtmxPresenter(request, model_web)
    http_response = presenter.present_delete_confirmation(check_result, web_obj, object_id)
    http_response["HX-Trigger-After-Settle"] = json.dumps({"openModalDialog": {"modal_id": "model-builder-modal"}})

    return http_response


@render_exception_modal_if_error
@time_it
def delete_object(request, object_id):
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)

    # 1. Map request to use case input
    input_data = DeleteObjectInput(
        object_id=object_id,
        form_data=request.POST if request.POST else None
    )

    # 2. Execute use case
    use_case = DeleteObjectUseCase(model_web)
    output = use_case.execute(input_data)

    # 3. Present result
    presenter = HtmxPresenter(request, model_web)
    return presenter.present_deleted_object(output)
