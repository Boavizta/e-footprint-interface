import os
import json


root = os.path.join(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(root, "reference_data", "form_fields_reference.json"), "r") as f:
    FORM_FIELD_REFERENCES = json.load(f)

with open(os.path.join(root, "reference_data", "form_type_object.json"), "r") as f:
    FORM_TYPE_OBJECT = json.load(f)
