import re
from typing import TYPE_CHECKING, get_origin, List, Tuple, Optional

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, get_instance_attributes
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import (
    ExplainableQuantityWeb, ExplainableObjectWeb, ExplainableObjectDictWeb)
from model_builder.domain.entities.web_abstract_modeling_classes.object_linked_to_modeling_obj_web import ObjectLinkedToModelingObjWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class ModelingObjectWeb:
    default_values = {}
    add_template = "add_panel__generic.html"
    edit_template = "edit_panel__generic.html"
    attributes_to_skip_in_forms = []
    gets_deleted_if_unique_mod_obj_container_gets_deleted = True

    def __init__(self, modeling_obj: ModelingObject, model_web: "ModelWeb", list_container=None):
        self._modeling_obj = modeling_obj
        self.model_web = model_web
        self.list_container = list_container

    @property
    def settable_attributes(self):
        return ["_modeling_obj", "model_web", "list_container"]

    def __getattr__(self, name):
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object

        # Check if the attribute is defined in the class hierarchy (as a property, method, etc.)
        # If it is, we need to manually call it and let any error propagate
        for cls in type(self).__mro__:
            if name in cls.__dict__:
                attr_descriptor = cls.__dict__[name]
                # If it's a property, call its getter
                if isinstance(attr_descriptor, property):
                    return attr_descriptor.fget(self)
                # If it's another descriptor (like a method), get it normally
                elif hasattr(attr_descriptor, '__get__'):
                    return attr_descriptor.__get__(self, type(self))
                # Otherwise just return it
                else:
                    return attr_descriptor

        attr = getattr(self._modeling_obj, name)

        if name == "id":
            raise AttributeError("The id attribute shouldn’t be retrieved by ModelingObjectWrapper objects. "
                             "Use efootprint_id and web_id for clear disambiguation.")

        if isinstance(attr, list) and len(attr) > 0 and isinstance(attr[0], ModelingObject):
            return [wrap_efootprint_object(item, self.model_web, self) for item in attr]

        if isinstance(attr, ModelingObject):
            return wrap_efootprint_object(attr, self.model_web)

        if isinstance(attr, ExplainableQuantity):
            return ExplainableQuantityWeb(attr, self.model_web)

        if isinstance(attr, ExplainableObject):
            return ExplainableObjectWeb(attr, self.model_web)

        if isinstance(attr, ExplainableObjectDict):
            return ExplainableObjectDictWeb(attr, self.model_web)

        return attr

    def __setattr__(self, key, value):
        if key in self.settable_attributes:
            super.__setattr__(self, key, value)
        else:
            raise PermissionError(f"{self} is trying to set the {key} attribute with value {value}.")

    def __hash__(self):
        return hash(self.web_id)

    def __eq__(self, other):
        return self.web_id == other.web_id

    def set_efootprint_value(self, key, value, check_input_validity=True):
        error_message = (f"{self} tried to set a ModelingObjectWrapper attribute to its underlying e-footprint "
                         f"object, which is forbidden. Only set e-footprint objects as attributes of e-footprint "
                         f"objects.")
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], ModelingObjectWeb):
            raise PermissionError(error_message)

        if isinstance(value, ModelingObjectWeb):
            raise PermissionError(error_message)

        if isinstance(value, ObjectLinkedToModelingObjWeb):
            raise PermissionError(error_message)

        self._modeling_obj.__setattr__(key, value, check_input_validity)

    def get_efootprint_value(self, key):
        return getattr(self._modeling_obj, key, None)

    @property
    def calculated_attributes_values(self):
        return [self.__getattr__(attr_name) for attr_name in self.calculated_attributes]

    @property
    def modeling_obj(self):
        return self._modeling_obj

    @property
    def efootprint_id(self):
        return self._modeling_obj.id

    @property
    def web_id(self):
        if self.list_container is not None:
            return f"{self.class_as_simple_str}-{self._modeling_obj.id}_in_{self.list_container.web_id}"
        return f"{self.class_as_simple_str}-{self._modeling_obj.id}"

    @property
    def value(self):
        return self.efootprint_id

    @property
    def label(self):
        return self.name

    @property
    def template_name(self):
        snake_case_class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', self.class_as_simple_str).lower()
        return f"{snake_case_class_name}"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """
        Returns HTMX configuration for the object creation form.
        Override in subclasses to customize behavior for specific object types.

        Args:
            context_data: The context data dictionary passed to the template

        Returns:
            Dictionary with optional keys:
            - hx_vals: dict of additional values to pass via hx-vals
            - hx_target: CSS selector for target element
            - hx_swap: HTMX swap strategy
        """
        return {}  # Default: no special HTMX configuration

    @property
    def links_to(self):
        output = ""
        direct_modeling_object_attributes = get_instance_attributes(self.modeling_obj, ModelingObject)
        if len(direct_modeling_object_attributes) == 0:
            list_modeling_object_attributes = get_instance_attributes(self.modeling_obj, ListLinkedToModelingObj)
            for list_modeling_objects in list_modeling_object_attributes.values():
                for list_modeling_object in list_modeling_objects:
                    web_object = self.model_web.get_web_object_from_efootprint_id(list_modeling_object.id)
                    output += f"|{web_object.links_to}"
        else:
            for modeling_object_attr in direct_modeling_object_attributes.values():
                web_object = self.model_web.get_web_object_from_efootprint_id(modeling_object_attr.id)
                output += f"|{web_object.web_id}"
        return output

    @property
    def data_line_opt(self):
        return "object-to-object"

    @property
    def data_attributes_as_list_of_dict(self):
        return [{'id': f'{self.web_id}', 'data-link-to': self.links_to, 'data-line-opt': self.data_line_opt}]

    @property
    def efootprint_contextual_modeling_obj_containers(self):
        return self._modeling_obj.contextual_modeling_obj_containers

    @property
    def list_containers_and_attr_name_in_list_container(self) -> Tuple[List["ModelingObjectWeb"], Optional[str]]:
        list_containers = []
        attr_name_in_list_container = None
        for contextual_container in self.efootprint_contextual_modeling_obj_containers:
            attr_name = contextual_container.attr_name_in_mod_obj_container
            container = contextual_container.modeling_obj_container
            container_signature = get_init_signature_params(container.efootprint_class)
            annotation = container_signature[attr_name].annotation
            if get_origin(annotation) and get_origin(annotation) in (list, List):
                list_containers.append(self.model_web.get_web_object_from_efootprint_id(container.id))
                attr_name_in_list_container = attr_name

        return list_containers, attr_name_in_list_container

    @property
    def mirrored_cards(self):
        """Recursively compute all mirrored instances of this object based on list containers."""
        result = []

        # Check if this object appears in any list attributes of container objects
        list_containers, attr_name_in_list_container = self.list_containers_and_attr_name_in_list_container
        for list_container in list_containers:
            for container_mirror in list_container.mirrored_cards:
                result.append(type(self)(self._modeling_obj, self.model_web, container_mirror))

        # If no list containers found, return self (base case for recursion)
        if not list_containers:
            return [self]

        return result

    @property
    def accordion_parent(self):
        return self.list_container

    @property
    def all_accordion_parents(self):
        list_parents = []
        parent = self.accordion_parent
        while parent:
            list_parents.append(parent)
            parent = parent.accordion_parent

        return list_parents

    @property
    def top_parent(self):
        if len(self.all_accordion_parents) == 0:
            return self
        else:
            return self.all_accordion_parents[-1]

    @property
    def list_attr_names(self):
        init_signature = get_init_signature_params(self.efootprint_class)
        list_attr_names = []
        for attr_name, param_info in init_signature.items():
            annotation = param_info.annotation
            if get_origin(annotation) and get_origin(annotation) in (list, List):
                list_attr_names.append(attr_name)
        return list_attr_names

    @property
    def accordion_children(self):
        """Automatically compute accordion children from list attributes."""
        children = []
        for attr_name in self.list_attr_names:
            attr_value = getattr(self, attr_name, None)
            if attr_value and isinstance(attr_value, list):
                children.extend(attr_value)

        return children

    @property
    def children_property_name(self) -> str:
        """Property name for accessing children (e.g., 'jobs'). Assumes a single list attr."""
        list_attr_names = self.list_attr_names
        assert len(list_attr_names) == 1, (
            f"{self} should have exactly one list attribute, found: {list_attr_names}.")

        return list_attr_names[0]

    @property
    def child_object_types_str(self) -> List[str]:
        """Type strings of child objects (supports multiple list attributes)."""
        init_signature = get_init_signature_params(self.efootprint_class)
        child_types = []
        for attr_name in self.list_attr_names:
            annotation = init_signature[attr_name].annotation
            child_types.append(annotation.__args__[0].__name__)

        return child_types

    @property
    def child_object_type_str(self) -> str:
        """Retained for backward compatibility when there is a single child type."""
        child_types = self.child_object_types_str
        assert len(child_types) == 1, (
            f"{self} exposes multiple child types: {child_types}. Use child_object_types_str instead.")
        return child_types[0]

    @property
    def child_sections(self):
        """Structured view of children grouped by their list attribute/type."""
        init_signature = get_init_signature_params(self.efootprint_class)
        sections = []
        for attr_name in self.list_attr_names:
            children = getattr(self, attr_name, []) or []
            annotation = init_signature[attr_name].annotation
            child_type = annotation.__args__[0].__name__
            sections.append({
                "type_str": child_type,
                "children": children,
                "attr_name": attr_name,
            })

        return sections

    def self_delete(self):
        obj_type = self.class_as_simple_str
        object_id = self.efootprint_id
        objects_to_delete_afterwards = []
        for modeling_obj in self.mod_obj_attributes:
            if (
                modeling_obj.gets_deleted_if_unique_mod_obj_container_gets_deleted
                and len(modeling_obj.modeling_obj_containers) == 1
            ):
                objects_to_delete_afterwards.append(modeling_obj)
        logger.info(f"Deleting {self.name}")
        self.modeling_obj.self_delete()
        self.model_web.response_objs[obj_type].pop(object_id, None)
        self.model_web.flat_efootprint_objs_dict.pop(object_id, None)
        for mod_obj in objects_to_delete_afterwards:
            mod_obj.self_delete()
