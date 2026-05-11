from django.http import Http404
from django.shortcuts import render

from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.efootprint_description_provider import EFOOTPRINT_DESCRIPTION_PROVIDER


def open_help_drawer(request, class_name):
    provider = EFOOTPRINT_DESCRIPTION_PROVIDER
    try:
        description = provider.class_description(class_name)
    except ValueError as exc:
        raise Http404(str(exc))

    context = {
        "header_name": f"About {ClassUIConfigProvider.get_label(class_name)}",
        "class_name": class_name,
        "class_label": ClassUIConfigProvider.get_label(class_name),
        "description": description,
        "disambiguation": provider.class_disambiguation(class_name),
        "pitfalls": provider.class_pitfalls(class_name),
        "interactions": provider.class_interactions(class_name),
        "docs_link": provider.resolve(f"{{doc:objects/{class_name}}}"),
    }
    return render(request, "model_builder/help_drawer/class_help.html", context=context)
