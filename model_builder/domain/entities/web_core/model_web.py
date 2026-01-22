from copy import deepcopy
from time import time

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes, ModelingObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.logger import logger
from efootprint import __version__ as efootprint_version

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT, ABSTRACT_EFOOTPRINT_MODELING_CLASSES
from model_builder.domain.interfaces import ISystemRepository
from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import ExplainableObjectWeb
from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object


from model_builder.domain.reference_data import DEFAULT_NETWORKS, DEFAULT_DEVICES, DEFAULT_COUNTRIES

DEFAULT_OBJECTS_CLASS_MAPPING = {
    "Network": lambda: deepcopy(DEFAULT_NETWORKS),
    "Device": lambda: deepcopy(DEFAULT_DEVICES),
    "Country": lambda: deepcopy(DEFAULT_COUNTRIES),
}


class ModelWeb:
    def __init__(self, repository: ISystemRepository):
        """Initialize ModelWeb with a system repository.

        Args:
            repository: An ISystemRepository implementation for loading and saving system data.
        """
        start = time()
        self.repository = repository
        raw_system_data = self.repository.get_system_data()
        self.system_data = self.repository.upgrade_system_data(raw_system_data)
        logger.info(f"System data loaded in {time() - start:.3f} seconds.")

        start = time()
        self.response_objs, self.flat_efootprint_objs_dict = json_to_system(
            self.system_data, launch_system_computations=True, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        self.system = wrap_efootprint_object(list(self.response_objs["System"].values())[0], self)
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
        """Updates the stored system data with the calculated attributes data."""
        self.repository.save_system_data(self.to_json(save_calculated_attributes=True))

    def raise_incomplete_modeling_errors(self):
        """Validate system completeness and raise ValueError if incomplete."""
        from model_builder.domain.services import SystemValidationService
        validation_service = SystemValidationService()
        result = validation_service.validate_for_computation(self)
        result.raise_if_invalid()

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

        obj_type_class = MODELING_OBJECT_CLASSES_DICT.get(obj_type, None)
        if obj_type_class is None:
            obj_type_class = ABSTRACT_EFOOTPRINT_MODELING_CLASSES.get(obj_type, None)
        for existing_obj_type in self.response_objs.keys():
            if issubclass(MODELING_OBJECT_CLASSES_DICT[existing_obj_type], obj_type_class):
                output_list += [obj for obj in list(self.response_objs[existing_obj_type].values())
                                if obj not in output_list]

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

    def add_new_efootprint_object_to_object_dicts(self, efootprint_object: ModelingObject):
        object_type = efootprint_object.class_as_simple_str
        if object_type not in self.response_objs:
            self.response_objs[object_type] = {}
        self.response_objs[object_type][efootprint_object.id] = efootprint_object
        self.flat_efootprint_objs_dict[efootprint_object.id] = efootprint_object

    def add_new_efootprint_object_to_system(self, efootprint_object: ModelingObject):
        self.add_new_efootprint_object_to_object_dicts(efootprint_object)
        for modeling_obj_attribute in efootprint_object.mod_obj_attributes:
            if modeling_obj_attribute.id not in self.flat_efootprint_objs_dict:
                logger.info(f"{modeling_obj_attribute.class_as_simple_str} {modeling_obj_attribute.name} has been "
                            f"automatically created by {efootprint_object.name} and added to system data.")
                self.add_new_efootprint_object_to_object_dicts(modeling_obj_attribute)

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
        """Returns all edge devices."""
        all_edge_devices = self.get_web_objects_from_efootprint_type("EdgeDevice")
        return all_edge_devices

    @property
    def edge_computers(self):
        return self.get_web_objects_from_efootprint_type("EdgeComputer")

    @property
    def edge_appliances(self):
        return self.get_web_objects_from_efootprint_type("EdgeAppliance")

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
    def hardware(self):
        return self.get_web_objects_from_efootprint_type("Hardware")

    @property
    def networks(self):
        return self.get_web_objects_from_efootprint_type("Network")

    @property
    def usage_patterns(self):
        return self.get_web_objects_from_efootprint_type("UsagePattern")

    @property
    def edge_usage_patterns(self):
        return self.get_web_objects_from_efootprint_type("EdgeUsagePattern")

    @property
    def edge_usage_journeys(self):
        return self.get_web_objects_from_efootprint_type("EdgeUsageJourney")

    @property
    def edge_functions(self):
        return self.get_web_objects_from_efootprint_type("EdgeFunction")

    @property
    def recurrent_edge_device_needs(self):
        """Returns all RecurrentEdgeDeviceNeed instances (processes and workloads)."""
        return self.get_web_objects_from_efootprint_type("RecurrentEdgeDeviceNeed")

    @property
    def recurrent_edge_processes(self):
        return self.get_web_objects_from_efootprint_type("RecurrentEdgeProcess")

    @property
    def recurrent_edge_workloads(self):
        return self.get_web_objects_from_efootprint_type("RecurrentEdgeWorkload")

    @property
    def system_emissions(self):
        """Calculate daily emissions timeseries for the system."""
        from model_builder.domain.services import EmissionsCalculationService
        service = EmissionsCalculationService()
        result = service.calculate_daily_emissions(self.system)
        return result.to_dict()
