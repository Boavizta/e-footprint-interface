import json
import os
from time import time

import numpy as np
import pandas as pd
from django.contrib.sessions.backends.base import SessionBase
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject, ExplainableHourlyQuantities
from efootprint.api_utils.json_to_system import json_to_system, json_to_explainable_object
from efootprint.core.all_classes_in_order import SERVICE_CLASSES
from efootprint.logger import logger
from efootprint.constants.units import u

from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT, ABSTRACT_EFOOTPRINT_MODELING_CLASSES
from model_builder.modeling_objects_web import wrap_efootprint_object
from utils import EFOOTPRINT_COUNTRIES

model_web_root = os.path.dirname(os.path.abspath(__file__))

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
    def __init__(
        self, session: SessionBase, launch_system_computations=False, set_trigger_modeling_updates_to_false=True):
        start = time()
        self.session = session
        self.system_data = session["system_data"]
        self.response_objs, self.flat_efootprint_objs_dict = json_to_system(
            self.system_data, launch_system_computations, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        self.system = wrap_efootprint_object(list(self.response_objs["System"].values())[0], self)
        if set_trigger_modeling_updates_to_false:
            self.set_all_trigger_modeling_updates_to_false()
        logger.info(f"ModelWeb object created in {time() - start:.3f} seconds.")

    def set_all_trigger_modeling_updates_to_false(self):
        for efootprint_obj in self.flat_efootprint_objs_dict.values():
            efootprint_obj.trigger_modeling_updates = False

    @staticmethod
    def _efootprint_object_from_json(json_input: dict, object_type: str):
        efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
        efootprint_object = efootprint_class.__new__(efootprint_class)
        efootprint_object.__dict__["contextual_modeling_obj_containers"] = []
        efootprint_object.trigger_modeling_updates = False
        for attr_key, attr_value in json_input.items():
            if type(attr_value) == dict:
                efootprint_object.__setattr__(attr_key, json_to_explainable_object(attr_value))
            else:
                efootprint_object.__dict__[attr_key] = attr_value
        efootprint_object.after_init()

        return efootprint_object

    def get_efootprint_objects_from_efootprint_type(self, obj_type):
        output_list = []
        if obj_type in DEFAULT_OBJECTS_CLASS_MAPPING.keys():
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

    def add_new_efootprint_object_to_system(self, efootprint_object):
        object_type = efootprint_object.class_as_simple_str

        if object_type not in self.session["system_data"]:
            self.session["system_data"][object_type] = {}
            self.response_objs[object_type] = {}
        self.session["system_data"][object_type][efootprint_object.id] = efootprint_object.to_json()
        # Here we updated a sub dict of request.session so we have to explicitly tell Django that it has been updated
        self.session.modified = True

        self.response_objs[object_type][efootprint_object.id] = efootprint_object
        self.flat_efootprint_objs_dict[efootprint_object.id] = efootprint_object

        return wrap_efootprint_object(efootprint_object, self)

    @property
    def storages(self):
        return self.get_web_objects_from_efootprint_type("Storage")

    @property
    def servers(self):
        return self.get_web_objects_from_efootprint_type("ServerBase")

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

    def get_reindexed_system_energy_and_fabrication_footprint_as_df_dict(self):
        energy_footprints = self.system.total_energy_footprints
        fabrication_footprints = self.system.total_fabrication_footprints

        all_explainable_hourly_quantities_values = [
            elt for elt in list(energy_footprints.values()) + list(fabrication_footprints.values())
            if isinstance(elt, ExplainableHourlyQuantities)]

        combined_index = pd.period_range(
            start=min(
                explainable_hourly_quantities.value.index.min() for explainable_hourly_quantities in
                all_explainable_hourly_quantities_values),
            end=max(explainable_hourly_quantities.value.index.max() for explainable_hourly_quantities in
                    all_explainable_hourly_quantities_values),
            freq='h'
        )

        for footprint_dict in [energy_footprints, fabrication_footprints]:
            for key, explainable_hourly_quantities in footprint_dict.items():
                if isinstance(explainable_hourly_quantities, EmptyExplainableObject):
                    footprint_dict[key] = pd.DataFrame(
                {"value": np.full(shape=len(combined_index), fill_value=0.0)}, index=combined_index, dtype="pint[kg]")
                else:
                    footprint_dict[key] = explainable_hourly_quantities.value.reindex(combined_index, fill_value=0)

        return energy_footprints, fabrication_footprints, combined_index

    @property
    def system_emissions(self):
        energy_footprints, fabrication_footprints, combined_index = (
            self.get_reindexed_system_energy_and_fabrication_footprint_as_df_dict())

        # Resample all dataframes to daily frequency
        hours = combined_index.view('int64')
        days_since_epoch = hours // 24
        unique_days, unique_days_indices = np.unique(days_since_epoch, return_inverse=True)

        def to_rounded_daily_values_list(df, rounding_depth=5):
            daily_sums = np.bincount(unique_days_indices, weights=df["value"].pint.to(u.kg).values)

            return np.round(daily_sums, rounding_depth).tolist()

        values = {
            "Servers_and_storage_energy": to_rounded_daily_values_list(
            energy_footprints["Servers"] + energy_footprints["Storage"]),
            "Devices_energy": to_rounded_daily_values_list(energy_footprints["Devices"]),
            "Network_energy": to_rounded_daily_values_list(energy_footprints["Network"]),
            "Servers_and_storage_fabrication": to_rounded_daily_values_list(
            fabrication_footprints["Servers"] + fabrication_footprints["Storage"]),
            "Devices_fabrication": to_rounded_daily_values_list(fabrication_footprints["Devices"])
        }

        date_index = pd.to_datetime(unique_days, unit='D', origin="1970-01-01")
        emissions = {
            "dates": date_index.strftime("%Y-%m-%d").tolist(),
            "values": values
        }

        return emissions
