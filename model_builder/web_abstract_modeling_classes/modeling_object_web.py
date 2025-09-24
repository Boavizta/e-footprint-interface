import json
import re
from typing import TYPE_CHECKING, get_origin, List, get_args

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

ATTRIBUTES_TO_SKIP_IN_FORMS = [
    "gpu_latency_alpha", "gpu_latency_beta", "fixed_nb_of_instances", "storage", "service", "server"]


class ModelingObjectWeb:
    add_template = "add_panel__generic.html"
    edit_template = "edit_panel__generic.html"
    attributes_to_skip_in_forms = ATTRIBUTES_TO_SKIP_IN_FORMS

    def __init__(self, modeling_obj: ModelingObject, model_web: "ModelWeb"):
        self._modeling_obj = modeling_obj
        self.model_web = model_web
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = True

    @property
    def settable_attributes(self):
        return ["_modeling_obj", "model_web", "gets_deleted_if_unique_mod_obj_container_gets_deleted"]

    def __getattr__(self, name):
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object

        attr = getattr(self._modeling_obj, name)

        if name == "id":
            raise AttributeError("The id attribute shouldn’t be retrieved by ModelingObjectWrapper objects. "
                             "Use efootprint_id and web_id for clear disambiguation.")

        if isinstance(attr, list) and len(attr) > 0 and isinstance(attr[0], ModelingObject):
            return [wrap_efootprint_object(item, self.model_web) for item in attr]

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
        return f"{self.class_as_simple_str}-{self._modeling_obj.id}"

    @property
    def mirrored_cards(self):
        return [self]

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
    def accordion_parent(self):
        return None

    @property
    def class_title_style(self):
        return None

    @property
    def accordion_children(self):
        return []

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
            corresponding_efootprint_class_str, [corresponding_efootprint_class],
            ATTRIBUTES_TO_SKIP_IN_FORMS, model_web)

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
            list_attr_name = None
            for attr_name in init_sig_params:
                annotation = init_sig_params[attr_name].annotation
                if (get_origin(annotation) and get_origin(annotation) in (list, List)
                    and isinstance(new_efootprint_obj, get_args(annotation)[0])):
                    list_attr_name = attr_name
                    break
            assert list_attr_name is not None, f"A list attr name should always be found"

            mutable_post = QueryDict(mutable=True)
            existing_element_ids = [elt.id for elt in getattr(efootprint_object_to_link_to, list_attr_name)]
            existing_element_ids.append(added_obj.efootprint_id)
            mutable_post[list_attr_name] = ";".join(existing_element_ids)

            response_html = compute_edit_object_html_and_event_response(mutable_post, web_object_to_link_to)

            toast_and_highlight_data = {
                "ids": [mirrored_card.web_id for mirrored_card in added_obj.mirrored_cards], "name": added_obj.name,
                "action_type": "add_new_object"
            }

            response = generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)

        return response

    def generate_object_edition_context(self):
        form_fields, form_fields_advanced, dynamic_lists = generate_dynamic_form(
            self.class_as_simple_str, self.modeling_obj.__dict__, self.attributes_to_skip_in_forms, self.model_web)

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

        return {"obj": self, "message": message, "sub_message": sub_message, "remove_card_with_hyperscript": True}

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
        self.self_delete()
        self.model_web.update_system_data_with_up_to_date_calculated_attributes()

        http_response = HttpResponse(status=204)
        toast_and_highlight_data = {"ids": [], "name": self.name, "action_type": "delete_object"}
        http_response["HX-Trigger"] = json.dumps({
            "resetLeaderLines": "",
            "displayToastAndHighlightObjects": toast_and_highlight_data
        })

        return http_response
