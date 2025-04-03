from django.urls import path

import model_builder.addition.views_addition
import model_builder.views_deletion
import model_builder.edition.views_edition
from . import views

urlpatterns = [
    path("", views.model_builder_main, name="model-builder"),
    path("<reboot>", views.model_builder_main, name="model-builder"),
    path("open-create-object-panel/<object_type>/",
         model_builder.addition.views_addition.open_create_object_panel, name="open-add-new-object-panel"),
    path("add-object/<object_type>/",
         model_builder.addition.views_addition.add_object, name="add-new-object"),
    path("open-edit-object-panel/<object_id>/", model_builder.edition.views_edition.open_edit_object_panel,
         name="open-edit-object-panel"),
    path("edit-object/<object_id>/", model_builder.edition.views_edition.edit_object, name="edit-object"),
    path("delete-object/<object_id>/", model_builder.views_deletion.delete_object, name="delete-object"),
    path("ask-delete-object/<object_id>/", model_builder.views_deletion.ask_delete_object, name="ask-delete-object"),
    path("download-json/", views.download_json, name="download-json"),
    path("result-chart/", views.result_chart, name="result-chart"),
    path("open-import-json-panel/", views.open_import_json_panel, name="open-import-json-panel"),
    path("upload-json/", views.upload_json, name="upload-json"),
    path('display-calculus-graph/<efootprint_id>/<attr_name>/', model_builder.views.display_calculus_graph,
         name='display-calculus-graph'),
    path('graph/<cache_key>/<efootprint_id>/<attr_name>/<graph_key>', model_builder.views.get_calculus_graph,
         name='get-graph'),
    path('save-model-name/', model_builder.edition.views_edition.save_model_name, name='save-model-name'),
]
