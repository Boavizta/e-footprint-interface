from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj

from utils import camel_to_snake

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class ObjectLinkedToModelingObjWeb:
    def __init__(self, object_linked_to_modeling_obj: ObjectLinkedToModelingObj, model_web: "ModelWeb"):
        self.efootprint_object = object_linked_to_modeling_obj
        self.model_web = model_web

    def __getattr__(self, name):
        # Check if the attribute is defined in the class hierarchy (as a property, method, etc.)
        for cls in type(self).__mro__:
            if name in cls.__dict__:
                attr_descriptor = cls.__dict__[name]
                if isinstance(attr_descriptor, property):
                    return attr_descriptor.fget(self)
                elif hasattr(attr_descriptor, '__get__'):
                    return attr_descriptor.__get__(self, type(self))
                else:
                    return attr_descriptor

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
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object
        return wrap_efootprint_object(self.efootprint_object.modeling_obj_container, self.model_web)

    @property
    def key_in_dict(self):
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object
        return wrap_efootprint_object(self.efootprint_object.key_in_dict, self.model_web)

    @property
    def attr_name_web(self):
        """Return raw attribute name for display. Use |field_label filter in templates for formatting."""
        attr_name = self.attr_name_in_mod_obj_container
        # When modeling_obj_container is None, use the efootprint object's label
        if attr_name is None:
            return self.efootprint_object.label
        return attr_name

    @property
    def class_as_snake_str(self):
        return camel_to_snake(type(self.efootprint_object).__name__)
