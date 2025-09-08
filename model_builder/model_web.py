import json
import math
import os
from datetime import timedelta
from time import time

from django.contrib.sessions.backends.base import SessionBase
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes, ModelingObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.core.all_classes_in_order import SERVICE_CLASSES, ALL_EFOOTPRINT_CLASSES
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.job import JobBase
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.logger import logger
from efootprint import __version__ as efootprint_version

from model_builder.efootprint_extensions.edge_usage_pattern_from_form import EdgeUsagePatternFromForm
from model_builder.efootprint_extensions.recurrent_edge_process_from_form import RecurrentEdgeProcessFromForm
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_builder_utils import determine_global_time_bounds, to_rounded_daily_values, get_reindexed_array_from_dict
from model_builder.modeling_objects_web import wrap_efootprint_object, ExplainableObjectWeb
from utils import EFOOTPRINT_COUNTRIES


_extension_classes = [UsagePatternFromForm, RecurrentEdgeProcessFromForm, EdgeUsagePatternFromForm]
MODELING_OBJECT_CLASSES_DICT = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_EFOOTPRINT_CLASSES + _extension_classes}

model_web_root = os.path.dirname(os.path.abspath(__file__))
ABSTRACT_EFOOTPRINT_MODELING_CLASSES = {"JobBase": JobBase, "ServerBase": ServerBase}

with open(os.path.join(model_web_root, "form_fields_reference.json"), "r") as f:
    FORM_FIELD_REFERENCES = json.load(f)

with open(os.path.join(model_web_root, "form_type_object.json"), "r") as f:
    FORM_TYPE_OBJECT = json.load(f)


def default_networks():
    with open(os.path.join(model_web_root, "default_networks.json"), "r") as f:
        return json.load(f)

def default_devices():
    with open(os.path.join(model_web_root, "default_devices.json"), "r") as f:
        return json.load(f)

def default_countries():
    with open(os.path.join(model_web_root, "default_countries.json"), "r") as f:
        return json.load(f)

DEFAULT_OBJECTS_CLASS_MAPPING = {
    "Network": default_networks, "Device": default_devices, "Country": default_countries}
ATTRIBUTES_TO_SKIP_IN_FORMS = [
    "gpu_latency_alpha", "gpu_latency_beta", "fixed_nb_of_instances", "storage", "service", "server"]


class ModelWeb:
    def __init__(self, session: SessionBase):
        start = time()
        self.session = session
        self.system_data = session["system_data"]
        logger.info(f"Session data loaded in {time() - start:.3f} seconds.")
        start = time()
        self.response_objs, self.flat_efootprint_objs_dict = json_to_system(
            self.system_data, launch_system_computations=True, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        self.system = wrap_efootprint_object(list(self.response_objs["System"].values())[0], self)
        if self.system.storages and getattr(self.system.storages[0]._modeling_obj, "storage_needed", None) is None:
            # TODO: Remove this conditional block for V1
            logger.info("Storage attributes need be recomputed because of e-footprint update from 10.1.13 to 10.1.14")
            for storage in self.system.storages:
                storage._modeling_obj.storage_needed = EmptyExplainableObject()
                storage._modeling_obj.storage_freed = EmptyExplainableObject()
                storage._modeling_obj.automatic_storage_dumps_after_storage_duration = EmptyExplainableObject()
                storage.compute_calculated_attributes()
        logger.info(f"ModelWeb object created in {time() - start:.3f} seconds.")

    def to_json(self, save_calculated_attributes=True):
        """
        Serializes the current system data to JSON format.
        :param save_calculated_attributes: If True, calculated attributes will be included in the serialization.
        :return: JSON representation of the system data.
        """
        output_json = {"efootprint_version": efootprint_version}
        for efootprint_obj in reversed(self.flat_efootprint_objs_dict.values()):
            if efootprint_obj.class_as_simple_str not in output_json:
                output_json[efootprint_obj.class_as_simple_str] = {}
            output_json[efootprint_obj.class_as_simple_str][efootprint_obj.id] = efootprint_obj.to_json(
                save_calculated_attributes=save_calculated_attributes)

        return output_json

    def update_system_data_with_up_to_date_calculated_attributes(self):
        """
        Updates the session's system data with the calculated attributes data.
        :param system_data: Dictionary containing the new system data.
        """
        self.session.modified = True
        self.session["system_data"] = self.to_json(save_calculated_attributes=True)

    def raise_incomplete_modeling_errors(self):
        if len(self.system.servers) == 0:
            raise ValueError(
                "No impact could be computed because the modeling is incomplete. Please make sure you have at least "
                "one usage pattern linked to a usage journey with at least one step making a request to a server.")
        else:
            usage_journeys_linked_to_usage_pattern_and_without_uj_steps = []
            for usage_journey in self.usage_journeys:
                if len(usage_journey.usage_patterns) > 0 and len(usage_journey.uj_steps) == 0:
                    usage_journeys_linked_to_usage_pattern_and_without_uj_steps.append(usage_journey)

            if len(usage_journeys_linked_to_usage_pattern_and_without_uj_steps) > 0:
                raise ValueError(
                    f"The following usage journey(s) have no usage journey step:  "
                    f"{[uj.name for uj in usage_journeys_linked_to_usage_pattern_and_without_uj_steps]}."
                    f" Please add at least one step in each of the above usage journey(s), so that the model can be "
                    f"computed.\n\n"
                    "(Alternatively, if they are work in progress, you can delete the usage patterns pointing to them: "
                    "in that way the usage journeys will be ignored in the computation.)"
                )

    @staticmethod
    def _efootprint_object_from_json(json_input: dict, object_type: str):
        efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
        efootprint_object, expl_obj_dicts_to_create_after_objects_creation = efootprint_class.from_json_dict(
            json_input, {}, False, False)
        assert len(expl_obj_dicts_to_create_after_objects_creation) == 0, \
            f"{object_type} object {efootprint_object.id} has explainable objects to create after objects creation"
        efootprint_object.after_init()

        return efootprint_object

    def get_efootprint_objects_from_efootprint_type(self, obj_type):
        output_list = []
        if obj_type in DEFAULT_OBJECTS_CLASS_MAPPING:
            for json_input in DEFAULT_OBJECTS_CLASS_MAPPING[obj_type]().values():
                output_list.append(self._efootprint_object_from_json(json_input, obj_type))

            return output_list

        obj_type_class = MODELING_OBJECT_CLASSES_DICT.get(obj_type, None)
        if obj_type_class is None:
            obj_type_class = ABSTRACT_EFOOTPRINT_MODELING_CLASSES.get(obj_type, None)
        assert obj_type_class is not None, f"Object type {obj_type} not found in efootprint classes."
        for existing_obj_type in self.response_objs.keys():
            if issubclass(MODELING_OBJECT_CLASSES_DICT[existing_obj_type], obj_type_class):
                output_list += list(self.response_objs[existing_obj_type].values())

        return output_list

    def get_web_objects_from_efootprint_type(self, obj_type):
        return [wrap_efootprint_object(obj, self) for obj in self.get_efootprint_objects_from_efootprint_type(obj_type)]

    def get_web_object_from_efootprint_id(self, object_id):
        efootprint_object = self.flat_efootprint_objs_dict[object_id]
        return wrap_efootprint_object(efootprint_object, self)

    def get_efootprint_object_from_efootprint_id(self, efootprint_id: str, object_type: str):
        if efootprint_id in self.flat_efootprint_objs_dict.keys():
            efootprint_object = self.flat_efootprint_objs_dict[efootprint_id]
        else:
            web_object_json = DEFAULT_OBJECTS_CLASS_MAPPING[object_type]()[efootprint_id]
            efootprint_object = self._efootprint_object_from_json(web_object_json, object_type)
            web_object = self.add_new_efootprint_object_to_system(efootprint_object)
            logger.info(f"Object {web_object.name} created from default object and added to system data.")

        return efootprint_object

    def add_new_efootprint_object_to_system(self, efootprint_object: ModelingObject):
        object_type = efootprint_object.class_as_simple_str
        if object_type not in self.response_objs:
            self.response_objs[object_type] = {}
        self.response_objs[object_type][efootprint_object.id] = efootprint_object
        self.flat_efootprint_objs_dict[efootprint_object.id] = efootprint_object

        if isinstance(efootprint_object, UsagePattern):
            self.system.modeling_obj.usage_patterns.append(efootprint_object)
        elif isinstance(efootprint_object, EdgeUsagePattern):
            self.system.modeling_obj.edge_usage_patterns.append(efootprint_object)

        self.update_system_data_with_up_to_date_calculated_attributes()

        return wrap_efootprint_object(efootprint_object, self)

    @property
    def web_explainable_quantities(self):
        web_explainable_quantities = []
        for efootprint_object in self.flat_efootprint_objs_dict.values():
            web_explainable_quantities += [
                ExplainableObjectWeb(explainable_object, self)
                for explainable_object in get_instance_attributes(efootprint_object, ExplainableQuantity).values()]

        return web_explainable_quantities

    @property
    def storages(self):
        return self.get_web_objects_from_efootprint_type("Storage")

    @property
    def servers(self):
        return self.get_web_objects_from_efootprint_type("ServerBase")

    @property
    def edge_devices(self):
        return self.get_web_objects_from_efootprint_type("EdgeDevice")

    @property
    def services(self):
        return sum(
            [self.get_web_objects_from_efootprint_type(service.__name__) for service in SERVICE_CLASSES], start=[])

    @property
    def cpu_servers(self):
        return self.get_web_objects_from_efootprint_type("Server")

    @property
    def gpu_servers(self):
        return self.get_web_objects_from_efootprint_type("GPUServer")

    @property
    def jobs(self):
        return self.get_web_objects_from_efootprint_type("JobBase")

    @property
    def usage_journeys(self):
        return self.get_web_objects_from_efootprint_type("UsageJourney")

    @property
    def usage_journey_steps(self):
        return self.get_web_objects_from_efootprint_type("UsageJourneyStep")

    @property
    def countries(self):
        return self.get_web_objects_from_efootprint_type("Country")

    @property
    def available_countries(self):
        return EFOOTPRINT_COUNTRIES

    @property
    def hardware(self):
        return self.get_web_objects_from_efootprint_type("Hardware")

    @property
    def networks(self):
        return self.get_web_objects_from_efootprint_type("Network")

    @property
    def usage_patterns(self):
        return self.get_web_objects_from_efootprint_type("UsagePattern")

    @property
    def edge_usage_journeys(self):
        return self.get_web_objects_from_efootprint_type("EdgeUsageJourney")

    @property
    def system_emissions(self):
        energy = self.system.total_energy_footprints
        fab = self.system.total_fabrication_footprints

        ehqs = [q for q in list(energy.values()) + list(fab.values()) if isinstance(q, ExplainableHourlyQuantities)]

        if not ehqs:
            raise ValueError("No ExplainableHourlyQuantities found.")

        global_start, total_hours = determine_global_time_bounds(ehqs)

        emissions = {
            "dates" : [
                (global_start + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(math.ceil(total_hours / 24))
            ],
            "values" : {
                "Servers_and_storage_energy": to_rounded_daily_values(
                    get_reindexed_array_from_dict("Servers", energy, global_start, total_hours)
                    + get_reindexed_array_from_dict("Storage", energy, global_start, total_hours)
                ),
                "Devices_energy": to_rounded_daily_values(
                    get_reindexed_array_from_dict("Devices", energy, global_start, total_hours)
                ),
                "Network_energy": to_rounded_daily_values(
                    get_reindexed_array_from_dict("Network", energy, global_start, total_hours)
                ),
                "Servers_and_storage_fabrication": to_rounded_daily_values(
                    get_reindexed_array_from_dict("Servers", fab, global_start, total_hours)
                    + get_reindexed_array_from_dict("Storage", fab, global_start, total_hours)
                ),
                "Devices_fabrication": to_rounded_daily_values(
                    get_reindexed_array_from_dict("Devices", fab, global_start, total_hours)
                ),
            }
        }

        return emissions
