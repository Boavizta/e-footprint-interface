"""UI configuration for form rendering.

This module loads and exports UI configuration for classes and fields,
used by form generation and label resolution in the presentation layer.
"""
import os
import json

_root = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_root, "class_ui_config.json"), "r") as f:
    CLASS_UI_CONFIG = json.load(f)

with open(os.path.join(_root, "field_ui_config.json"), "r") as f:
    FIELD_UI_CONFIG = json.load(f)
