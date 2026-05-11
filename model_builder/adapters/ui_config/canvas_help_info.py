"""Builds the ``class_help_info`` context dict consumed by the canvas Add buttons.

Each entry pairs a class label with its resolved class description so the
``add_object_button.html`` include can render an info icon next to the Add
button. The keys mirror the class names the canvas template uses in its
``hx_url`` segments.
"""
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.efootprint_description_provider import EFOOTPRINT_DESCRIPTION_PROVIDER

CANVAS_ADD_BUTTON_CLASSES = (
    "UsagePattern",
    "EdgeUsagePattern",
    "UsageJourney",
    "EdgeUsageJourney",
    "ServerBase",
    "ExternalAPI",
    "EdgeDeviceBase",
    "EdgeDeviceGroup",
)


def build_canvas_class_help_info() -> dict[str, dict]:
    info = {}
    for class_name in CANVAS_ADD_BUTTON_CLASSES:
        # Some Add buttons use a select-type key (e.g. ``EdgeDeviceBase``) that is
        # not registered in ``ALL_EFOOTPRINT_CLASSES_DICT``. Treat it as "no help"
        # so the icon simply doesn't render.
        try:
            description = EFOOTPRINT_DESCRIPTION_PROVIDER.class_description(class_name)
        except ValueError:
            description = None
        info[class_name] = {
            "label": ClassUIConfigProvider.get_label(class_name),
            "description": description,
        }
    return info
