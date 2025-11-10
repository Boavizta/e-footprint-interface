import json
import re
from typing import TYPE_CHECKING, get_origin, List, get_args, Tuple, Optional

from django.http import QueryDict, HttpResponse
from django.shortcuts import render
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.class_structure import generate_dynamic_form, generate_object_creation_context
from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data
from model_builder.web_abstract_modeling_classes.explainable_objects_web import ExplainableQuantityWeb, \
    ExplainableObjectWeb, ExplainableObjectDictWeb
from model_builder.web_abstract_modeling_classes.object_linked_to_modeling_obj_web import ObjectLinkedToModelingObjWeb
from model_builder.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ModelingObjectWeb:
    default_values = {}
    add_template = "add_panel__generic.html"
    edit_template = "edit_panel__generic.html"
    attributes_to_skip_in_forms = []

    def __init__(self, modeling_obj: ModelingObject, model_web: "ModelWeb", list_container=None):
        self._modeling_obj = modeling_obj
        self.model_web = model_web
        self.list_container = list_container
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = True

    @property
    def settable_attributes(self):
        return ["_modeling_obj", "model_web", "list_container", "gets_deleted_if_unique_mod_obj_container_gets_deleted"]

    def __getattr__(self, name):
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object

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
    def value(self):
        return self.efootprint_id

    @property
    def label(self):
        return self.name

    @property
    def class_label(self):
        return FORM_TYPE_OBJECT[self.class_as_simple_str]["label"]

    @property
    def web_id(self):
        if self.list_container is not None:
            return f"{self.class_as_simple_str}-{self._modeling_obj.id}_in_{self.list_container.web_id}"
        return f"{self.class_as_simple_str}-{self._modeling_obj.id}"

    @property
    def efootprint_contextual_modeling_obj_containers(self):
        return self._modeling_obj.contextual_modeling_obj_containers

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
    def template_name(self):
        snake_case_class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', self.class_as_simple_str).lower()
        return f"{snake_case_class_name}"

    @property
    def links_to(self):
        return ""

    @property
    def data_line_opt(self):
        return "object-to-object"

    @property
    def data_attributes_as_list_of_dict(self):
        return [{'id': f'{self.web_id}', 'data-link-to': self.links_to, 'data-line-opt': self.data_line_opt}]

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
            elif len(list_containers) > 0:
                raise NotImplementedError(
                    f"Modeling object {self} appears in both list and non-list attributes of its containers. "
                    f"This is not supported behavior.")

        return list_containers, attr_name_in_list_container

    @property
    def accordion_parent(self):
        return self.list_container

    @property
    def class_title_style(self):
        return None

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

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        corresponding_efootprint_class_str = cls.__name__.replace("Web", "")
        corresponding_efootprint_class = MODELING_OBJECT_CLASSES_DICT[corresponding_efootprint_class_str]
        return generate_object_creation_context(
            corresponding_efootprint_class_str, [corresponding_efootprint_class], model_web)

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

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        object_creation_type = request.POST.get("type_object_available", object_type)
        new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, object_creation_type)
        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

        object_to_link_to_id = request.POST.get("efootprint_id_of_parent_to_link_to", None)

        if object_to_link_to_id is None:
            response = render(
                request, f"model_builder/object_cards/{added_obj.template_name}_card.html",
                {added_obj.template_name: added_obj})

            response["HX-Trigger-After-Swap"] = json.dumps({
                "resetLeaderLines": "",
                "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
                "displayToastAndHighlightObjects": {
                    "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
            })
        else:
            web_object_to_link_to = model_web.get_web_object_from_efootprint_id(object_to_link_to_id)
            efootprint_object_to_link_to = web_object_to_link_to.modeling_obj
            # Find the attr name for the list of objects to append the added object to in the efootprint_object_to_link_to
            init_sig_params = get_init_signature_params(type(efootprint_object_to_link_to))
            attr_name_in_list_container = None
            for attr_name in init_sig_params:
                annotation = init_sig_params[attr_name].annotation
                if (get_origin(annotation) and get_origin(annotation) in (list, List)
                    and isinstance(new_efootprint_obj, get_args(annotation)[0])):
                    attr_name_in_list_container = attr_name
                    break
            assert attr_name_in_list_container is not None, f"A list attr name should always be found"

            mutable_post = QueryDict(mutable=True)
            existing_element_ids = [elt.id for elt in getattr(efootprint_object_to_link_to, attr_name_in_list_container)]
            existing_element_ids.append(added_obj.efootprint_id)
            mutable_post[attr_name_in_list_container] = ";".join(existing_element_ids)

            response_html = compute_edit_object_html_and_event_response(mutable_post, web_object_to_link_to)

            toast_and_highlight_data = {
                "ids": [mirrored_card.web_id for mirrored_card in added_obj.mirrored_cards], "name": added_obj.name,
                "action_type": "add_new_object"
            }

            response = generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)

        return response

    def generate_object_edition_context(self):
        form_fields, form_fields_advanced, dynamic_lists = generate_dynamic_form(
            self.class_as_simple_str, self.modeling_obj.__dict__, self.model_web)

        context_data = {
            "object_to_edit": self,
            "form_fields": form_fields,
            "form_fields_advanced": form_fields_advanced,
            "dynamic_form_data": {"dynamic_lists": dynamic_lists},
            "header_name": f"Edit {self.name}"
        }

        return context_data

    def edit_object_and_return_html_response(self, edit_form_data: QueryDict):
        return compute_edit_object_html_and_event_response(edit_form_data, self)

    def generate_cant_delete_modal_message(self):
        msg = (f"This {self.class_as_simple_str} is referenced by "
               f"{", ".join([obj.name for obj in self.modeling_obj_containers])}. "
               f"To delete it, first delete or reorient these "
               f"{FORM_TYPE_OBJECT[self.modeling_obj_containers[0].class_as_simple_str]["label"].lower()}s.")

        return msg

    def generate_ask_delete_modal_context(self):
        context_data = {}
        accordion_children = self.accordion_children

        if len(accordion_children) > 0:
            class_label = self.class_label.lower()
            child_class_label = accordion_children[0].class_label.lower()
            message = (f"This {class_label} is associated with {len(accordion_children)} {child_class_label}. "
                       f"This action will delete them all")
            sub_message = f"{child_class_label.capitalize()} used in other {class_label}s will remain in those."
        else:
            message = f"Are you sure you want to delete this {self.class_as_simple_str} ?"
            sub_message = ""

        context_data["obj"] = self
        context_data["message"] = message
        context_data["sub_message"] = sub_message
        context_data["remove_card_with_hyperscript"] = True

        # Override for mirrored objects (those with list_container or multiple mirrored_cards)
        mirrored_cards = self.mirrored_cards
        if len(mirrored_cards) > 1:
            context_data["remove_card_with_hyperscript"] = False
            context_data["message"] = (f"This {self.class_as_simple_str} is mirrored {len(mirrored_cards)} times, "
                                       f"this action will delete all mirrored {self.class_as_simple_str}s.")
            context_data["sub_message"] = (f"To delete only one {self.class_as_simple_str}, "
                                           f"break the mirroring link first.")

        return context_data

    def generate_ask_delete_http_response(self, request):
        if self.modeling_obj_containers:
            cant_delete_modal_message = self.generate_cant_delete_modal_message()
            cant_delete_modal_context = {
                "modal_id": "model-builder-modal", "message": cant_delete_modal_message}

            http_response = render(request, "model_builder/modals/cant_delete_modal.html",
                                   context=cant_delete_modal_context)
        else:
            delete_modal_context = self.generate_ask_delete_modal_context()
            delete_modal_context["modal_id"] = "model-builder-modal"

            http_response = render(
                request, "model_builder/modals/delete_card_modal.html",
                context=delete_modal_context)

        return http_response

    def generate_delete_http_response(self, request):
        list_containers, attr_name_in_list_container = self.list_containers_and_attr_name_in_list_container
        if list_containers:
            toast_and_highlight_data = {"ids": [], "name": self.name, "action_type": "delete_object"}
            response_html = ""
            for list_container in list_containers:
                mutable_post = request.POST.copy()
                logger.info(f"Removing {self.name} from {list_container.name}")
                mutable_post['name'] = list_container.name
                new_list_attribute_ids = [
                    list_attribute.efootprint_id
                    for list_attribute in getattr(list_container, attr_name_in_list_container)
                    if list_attribute.efootprint_id != self.efootprint_id]
                mutable_post[attr_name_in_list_container] = ";".join(new_list_attribute_ids)
                request.POST = mutable_post

                partial_response_html = compute_edit_object_html_and_event_response(request.POST, list_container)
                response_html += partial_response_html

            http_response = generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)
        else:
            # Non-list object: normal deletion
            self.self_delete()
            self.model_web.update_system_data_with_up_to_date_calculated_attributes()

            http_response = HttpResponse(status=204)
            toast_and_highlight_data = {"ids": [], "name": self.name, "action_type": "delete_object"}
            http_response["HX-Trigger"] = json.dumps({
                "resetLeaderLines": "",
                "displayToastAndHighlightObjects": toast_and_highlight_data
            })

        return http_response
