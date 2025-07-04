import re
import string
from typing import List, Tuple, Dict, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.core.all_classes_in_order import SERVICE_CLASSES
from efootprint.logger import logger

from utils import camel_to_snake

if TYPE_CHECKING:
    from model_builder.model_web import ModelWeb


def retrieve_attributes_by_type(modeling_obj, attribute_type):
    output_list = []
    for attr_name, attr_value in vars(modeling_obj).items():
        if (isinstance(attr_value, attribute_type)
            and attr_name not in modeling_obj.attributes_that_shouldnt_trigger_update_logic):
            output_list.append({'attr_name': attr_name, 'attr_value': attr_value})

    return output_list


class ObjectLinkedToModelingObjWeb:
    def __init__(self, object_linked_to_modeling_obj: ObjectLinkedToModelingObj, model_web: "ModelWeb"):
        self.efootprint_object = object_linked_to_modeling_obj
        self.model_web = model_web

    def __getattr__(self, name):
        attr = getattr(self.efootprint_object, name)

        return attr

    @property
    def modeling_obj_container(self):
        return wrap_efootprint_object(self.efootprint_object.modeling_obj_container, self.model_web)

    @property
    def attr_name_web(self):
        from model_builder.model_web import FORM_FIELD_REFERENCES
        if self.attr_name_in_mod_obj_container in FORM_FIELD_REFERENCES.keys():
            return FORM_FIELD_REFERENCES[self.attr_name_in_mod_obj_container]["label"]
        else:
            return self.attr_name_in_mod_obj_container.replace("_", " ")

    @property
    def class_as_snake_str(self):
        return camel_to_snake(type(self.efootprint_object).__name__)


class ExplainableObjectWeb(ObjectLinkedToModelingObjWeb):
    def compute_literal_formula_and_ancestors_mapped_to_symbols_list(self) \
        -> Tuple[List[str|ExplainableObject], List[Dict[str, ExplainableObject]]]:
        # Base symbols: Roman lowercase + Greek lowercase
        base_symbols = list(string.ascii_lowercase) + [
            'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ',
            'χ', 'ψ', 'ω']

        def get_symbol(i: int) -> str:
            n = len(base_symbols)
            index = i % n
            cycle = i // n
            base = base_symbols[index]
            return base if cycle == 0 else f"{base}{cycle}"

        ancestor_ids_to_symbols_mapping = {}
        ids_to_ancestors_mapping = {}
        flat_tuple_formula = self.compute_formula_as_flat_tuple(self.explain_nested_tuples)
        literal_formula = []
        current_symbol_index = 0
        for elt in flat_tuple_formula:
            if isinstance(elt, ExplainableObject):
                web_wrapper = ExplainableQuantityWeb if isinstance(elt, ExplainableQuantity) else ExplainableObjectWeb
                if elt.modeling_obj_container is None:
                    elt.attr_name_web = elt.label
                    literal_formula.append(
                        {"symbol": elt.label,
                         "explainable_object": web_wrapper(elt, elt.modeling_obj_container)})
                elif elt.id in ancestor_ids_to_symbols_mapping:
                    literal_formula.append(
                        {"symbol": ancestor_ids_to_symbols_mapping[elt.id],
                         "explainable_object": web_wrapper(elt, elt.modeling_obj_container)})
                else:
                    ancestor_ids_to_symbols_mapping[elt.id] = get_symbol(current_symbol_index)
                    literal_formula.append(
                        {"symbol": ancestor_ids_to_symbols_mapping[elt.id],
                         "explainable_object": web_wrapper(elt, elt.modeling_obj_container)})
                    current_symbol_index += 1
                    ids_to_ancestors_mapping[elt.id] = elt
            else:
                literal_formula.append(elt)

        ancestors_mapped_to_symbols_list = []

        for ancestor_id in ids_to_ancestors_mapping:
            ancestor = ids_to_ancestors_mapping[ancestor_id]
            web_wrapper = ExplainableQuantityWeb if isinstance(ancestor, ExplainableQuantity) else ExplainableObjectWeb
            ancestors_mapped_to_symbols_list.append(
                {"symbol": ancestor_ids_to_symbols_mapping[ancestor_id],
                 "explainable_object": web_wrapper(ancestor, ancestor.modeling_obj_container)})

        return literal_formula, ancestors_mapped_to_symbols_list


class ExplainableQuantityWeb(ExplainableObjectWeb):
    @property
    def rounded_value(self):
        return round(self.value, 2)

    @property
    def unit(self):
        return self.value.units


class ExplainableObjectDictWeb(ObjectLinkedToModelingObjWeb):
    @property
    def get_values_as_list(self) -> List[ExplainableObjectWeb]:
        return [ExplainableObjectWeb(explainable_object, self.model_web)
                for explainable_object in self.efootprint_object.values()]


class ModelingObjectWeb:
    def __init__(self, modeling_obj: ModelingObject, model_web: "ModelWeb"):
        self._modeling_obj = modeling_obj
        self.model_web = model_web

    @property
    def settable_attributes(self):
        return ["_modeling_obj", "model_web"]

    def __getattr__(self, name):
        attr = getattr(self._modeling_obj, name)

        if name == "id":
            raise ValueError("The id attribute shouldn’t be retrieved by ModelingObjectWrapper objects. "
                             "Use efootprint_id and web_id for clear disambiguation.")

        if isinstance(attr, list) and len(attr) > 0 and isinstance(attr[0], ModelingObject):
            return [wrap_efootprint_object(item, self.model_web) for item in attr]

        if isinstance(attr, ModelingObject):
            return wrap_efootprint_object(attr, self.model_web)

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
        from model_builder.model_web import FORM_TYPE_OBJECT
        return FORM_TYPE_OBJECT[self.class_as_simple_str]["label"]

    @property
    def web_id(self):
        return self._modeling_obj.id

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
                not (
                    (modeling_obj.class_as_simple_str in [service_class.__name__ for service_class in SERVICE_CLASSES])
                    or isinstance(modeling_obj, ServerWeb)
                    or isinstance(modeling_obj, UsageJourneyWeb)
                )
                and len(modeling_obj.modeling_obj_containers) == 1
            ):
                objects_to_delete_afterwards.append(modeling_obj)
        logger.info(f"Deleting {self.name}")
        self.modeling_obj.self_delete()
        self.model_web.response_objs[obj_type].pop(object_id, None)
        self.model_web.flat_efootprint_objs_dict.pop(object_id, None)
        for mod_obj in objects_to_delete_afterwards:
            mod_obj.self_delete()

class ServiceWeb(ModelingObjectWeb):
    @property
    def class_title_style(self):
        return "h8"

    @property
    def template_name(self):
        return "service"

class ServerWeb(ModelingObjectWeb):
    @property
    def template_name(self):
        return "server"

    @property
    def accordion_parent(self):
        return None

    @property
    def accordion_children(self):
        return [self.storage]

    @property
    def class_title_style(self):
        return "h6"


class JobWeb(ModelingObjectWeb):
    @property
    def web_id(self):
        raise PermissionError(f"JobWeb objects don’t have a web_id attribute because their html "
                             f"representation should be managed by the MirroredJobWeb object")

    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for usage_journey_step in self.usage_journey_steps:
            for mirrored_usage_journey_card in usage_journey_step.mirrored_cards:
                mirrored_cards.append(MirroredJobWeb(self._modeling_obj, mirrored_usage_journey_card))

        return mirrored_cards


class MirroredJobWeb(ModelingObjectWeb):
    def __init__(self, modeling_obj: ModelingObject, uj_step):
        super().__init__(modeling_obj, uj_step.model_web)
        self.usage_journey_step = uj_step

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["usage_journey_step"]

    @property
    def template_name(self):
        return "job"

    @property
    def web_id(self):
        return f"{self.usage_journey_step.web_id}_{self.efootprint_id}"

    @property
    def links_to(self):
        return self.server.web_id

    @property
    def accordion_parent(self):
        return self.usage_journey_step

    @property
    def accordion_children(self):
        return []

    @property
    def class_title_style(self):
        return "h8"


class UsageJourneyStepWeb(ModelingObjectWeb):
    @property
    def web_id(self):
        raise PermissionError(f"UsageJourneyStepWeb objects don’t have a web_id attribute because their html "
                             f"representation should be managed by the MirroredUsageJourneyStepWeb object")

    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for usage_journey in self.usage_journeys:
            mirrored_cards.append(MirroredUsageJourneyStepWeb(self._modeling_obj, usage_journey))

        return mirrored_cards


class MirroredUsageJourneyStepWeb(UsageJourneyStepWeb):
    def __init__(self, modeling_obj: ModelingObject, usage_journey):
        super().__init__(modeling_obj, usage_journey.model_web)
        self.usage_journey = usage_journey

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["usage_journey"]

    @property
    def web_id(self):
        return f"{self.usage_journey.web_id}_{self.efootprint_id}"

    @property
    def links_to(self):
        linked_server_ids = set([job.server.web_id for job in self.jobs])
        return "|".join(linked_server_ids)

    @property
    def accordion_parent(self):
        return self.usage_journey

    @property
    def accordion_children(self):
        return self.jobs

    @property
    def jobs(self):
        web_jobs = []
        for job in self._modeling_obj.jobs:
            web_jobs.append(MirroredJobWeb(job, self))

        return web_jobs

    @property
    def icon_links_to(self):
        usage_journey_steps = self.usage_journey.uj_steps
        index = usage_journey_steps.index(self)
        if index < len(usage_journey_steps) - 1:
            link_to = f"icon-{usage_journey_steps[index+1].web_id}"
        else:
            link_to = f'add-usage-pattern-{self.usage_journey.web_id}'

        return link_to

    @property
    def icon_leaderline_style(self):
        usage_journey_steps = self.usage_journey.uj_steps
        index = usage_journey_steps.index(self)
        if index < len(usage_journey_steps) - 1:
            class_name = "vertical-step-swimlane"
        else:
            class_name = 'step-dot-line'

        return class_name

    @property
    def class_title_style(self):
        return "h7"

    @property
    def data_attributes_as_list_of_dict(self):
        data_attribute_updates = super().data_attributes_as_list_of_dict
        data_attribute_updates.append(
            {'id': f'icon-{self.web_id}', 'data-link-to': self.icon_links_to,
             'data-line-opt': self.icon_leaderline_style})

        return data_attribute_updates

class UsageJourneyWeb(ModelingObjectWeb):
    @property
    def links_to(self):
        linked_server_ids = set()
        for uj_step in self.uj_steps:
            for job in uj_step.jobs:
                linked_server_ids.add(job.server.web_id)

        return "|".join(sorted(linked_server_ids))

    @property
    def accordion_parent(self):
        return None

    @property
    def accordion_children(self):
        return self.uj_steps

    @property
    def uj_steps(self):
        web_uj_steps = []
        for uj_step in self._modeling_obj.uj_steps:
            web_uj_steps.append(MirroredUsageJourneyStepWeb(uj_step, self))

        return web_uj_steps

    @property
    def class_title_style(self):
        return "h6"


class UsagePatternWeb(ModelingObjectWeb):
    @property
    def links_to(self):
        return self.usage_journey.web_id

    @property
    def accordion_parent(self):
        return None

    @property
    def accordion_children(self):
        # TODO: Add Device mix Network mix and Country mix
        return []

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"

EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING = {
    "Server": ServerWeb,
    "GPUServer": ServerWeb,
    "BoaviztaCloudServer": ServerWeb,
    "UsageJourneyStep": UsageJourneyStepWeb,
    "UsageJourney": UsageJourneyWeb,
    "UsagePattern": UsagePatternWeb,
    "UsagePatternFromForm": UsagePatternWeb,
    "Job": JobWeb,
    "GPUJob": JobWeb,
    "GenAIJob": JobWeb,
    "VideoStreamingJob": JobWeb,
    "WebApplicationJob": JobWeb,
    "GenAIModel": ServiceWeb,
    "VideoStreaming": ServiceWeb,
    "WebApplication": ServiceWeb,
    "Storage": ModelingObjectWeb
}

def wrap_efootprint_object(modeling_obj: ModelingObject, model_web: "ModelWeb"):
    if modeling_obj.class_as_simple_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.keys():
        return EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[modeling_obj.class_as_simple_str](modeling_obj, model_web)

    return ModelingObjectWeb(modeling_obj, model_web)
