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
    path("display-calculus-graph/<efootprint_id>/<attr_name>/", model_builder.views.display_calculus_graph,
         name="display-calculus-graph"),
    path("display-calculus-graph/<efootprint_id>/<attr_name>/<id_of_key_in_dict>", model_builder.views.display_calculus_graph,
             name="display-calculus-graph-from-dict"),
    path("graph/<cache_key>", model_builder.views.get_calculus_graph, name="get-graph"),
    path("download-sources/", views.download_sources, name="download-sources"),
    path("open-panel-system-name/", model_builder.edition.views_edition.open_panel_system_name,
         name="open-panel-system-name"),
    path("save-system-name/", model_builder.edition.views_edition.save_system_name, name="save-system-name"),
    path("get_explainable_hourly_quantity_chart_and_explanation/<efootprint_id>/<attr_name>/",
         model_builder.views.get_explainable_hourly_quantity_chart_and_explanation,
         name="get_explainable_hourly_quantity_chart_and_explanation"),
    path("get_explainable_hourly_quantity_chart_and_explanation/<efootprint_id>/<attr_name>/<id_of_key_in_dict>",
         model_builder.views.get_explainable_hourly_quantity_chart_and_explanation,
         name="get_explainable_hourly_quantity_chart_and_explanation_from_dict"),
    path("get_explainable_recurrent_quantity_chart_and_explanation/<efootprint_id>/<attr_name>/",
         model_builder.views.get_explainable_recurrent_quantity_chart_and_explanation,
         name="get_explainable_recurrent_quantity_chart_and_explanation"),
    path("get_calculated_attribute_explanation/<efootprint_id>/<attr_name>/",
         model_builder.views.get_calculated_attribute_explanation,
         name="get_calculated_attribute_explanation"),
]
