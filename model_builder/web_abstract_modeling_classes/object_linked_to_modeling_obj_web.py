from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj

from utils import camel_to_snake


class ObjectLinkedToModelingObjWeb:
    def __init__(self, object_linked_to_modeling_obj: ObjectLinkedToModelingObj, model_web: "ModelWeb"):
        self.efootprint_object = object_linked_to_modeling_obj
        self.model_web = model_web

    def __getattr__(self, name):
        attr = getattr(self.efootprint_object, name)

        return attr

    @property
    def id(self):
        raise AttributeError("The id attribute shouldn’t be retrieved by ObjectLinkedToModelingObjWeb objects. "
                         "Use efootprint_id and web_id for clear disambiguation.")

    @property
    def web_id(self):
        return css_escape(self.efootprint_object.id)

    @property
    def efootprint_id(self):
        return self.efootprint_object.id

    @property
    def modeling_obj_container(self):
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return wrap_efootprint_object(self.efootprint_object.modeling_obj_container, self.model_web)

    @property
    def key_in_dict(self):
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return wrap_efootprint_object(self.efootprint_object.key_in_dict, self.model_web)

    @property
    def attr_name_web(self):
        from model_builder.web_core.model_web import FORM_FIELD_REFERENCES
        if self.attr_name_in_mod_obj_container in FORM_FIELD_REFERENCES.keys():
            return FORM_FIELD_REFERENCES[self.attr_name_in_mod_obj_container]["label"]
        else:
            return self.attr_name_in_mod_obj_container.replace("_", " ")

    @property
    def class_as_snake_str(self):
        return camel_to_snake(type(self.efootprint_object).__name__)
