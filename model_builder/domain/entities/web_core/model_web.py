from copy import deepcopy
from time import perf_counter

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes, ModelingObject
from efootprint.abstract_modeling_classes.source_objects import Sources
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params
from efootprint import __version__ as efootprint_version

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT, ABSTRACT_EFOOTPRINT_MODELING_CLASSES
from model_builder.domain.interfaces import ISystemRepository
from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import ExplainableQuantityWeb
from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object


from model_builder.domain.exceptions import SessionExpiredError
from model_builder.domain.reference_data import (
    DEFAULT_NETWORKS, DEFAULT_NETWORKS_SOURCES,
    DEFAULT_DEVICES, DEFAULT_DEVICES_SOURCES,
    DEFAULT_COUNTRIES, DEFAULT_COUNTRIES_SOURCES,
)

DEFAULT_OBJECTS_CLASS_MAPPING = {
    "Network": lambda: deepcopy(DEFAULT_NETWORKS),
    "Device": lambda: deepcopy(DEFAULT_DEVICES),
    "Country": lambda: deepcopy(DEFAULT_COUNTRIES),
}

DEFAULT_SOURCES_CLASS_MAPPING = {
    "Network": lambda: DEFAULT_NETWORKS_SOURCES,
    "Device": lambda: DEFAULT_DEVICES_SOURCES,
    "Country": lambda: DEFAULT_COUNTRIES_SOURCES,
}


class ModelWeb:
    def __init__(self, repository: ISystemRepository, system_data: dict = None):
        """Initialize ModelWeb with a system repository.

        Args:
            repository: An ISystemRepository implementation for loading and saving system data.
        """
        self.repository = repository
        self._system_emissions = None
        self.system_data_source = None
        if system_data is not None:
            raw_system_data = system_data
            self.system_data_source = "provided"
        else:
            raw_system_data, self.system_data_source = self.repository.get_system_data_with_source()
        if raw_system_data is not None:
            self.initial_system_data_efootprint_version = raw_system_data.get("efootprint_version")
            interface_upgraded_system_data = self.repository.upgrade_system_data(raw_system_data)
            start = perf_counter()
            self.response_objs, self.flat_efootprint_objs_dict, self.system_data = json_to_system(
                interface_upgraded_system_data, launch_system_computations=True,
                efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
            self.system = wrap_efootprint_object(list(self.response_objs["System"].values())[0], self)
            logger.info(f"ModelWeb object created in {1000 * (perf_counter() - start):.1f} ms.")
            self.creation_constraints = self._build_creation_constraints()
            if self.system_data_source == "postgres":
                self.persist_to_cache()
        else:
            self.system_data = raw_system_data
            self.creation_constraints = {}
            logger.info(f"Empty system data so e-footprint modeling hasn’t been hydrated.")
        self.constraint_changes = []

    def __getattr__(self, name):
        if name in ("system", "response_objs", "flat_efootprint_objs_dict", "initial_system_data_efootprint_version"):
            raise SessionExpiredError(
                "Your session has expired (model data is no longer available). "
                "Please reload the page to start a new session."
            )
        raise AttributeError(f"’ModelWeb’ object has no attribute ‘{name}’")

    def to_json(self, save_calculated_attributes=True):
        """
        Serializes the current system data to JSON format.
        :param save_calculated_attributes: If True, calculated attributes will be included in the serialization.
        :return: JSON representation of the system data.
        """
        sources_by_id = {}
        modeling_blocks = {}
        for efootprint_obj in self.flat_efootprint_objs_dict.values():
            obj_type = efootprint_obj.class_as_simple_str
            if obj_type not in modeling_blocks:
                modeling_blocks[obj_type] = {}
            modeling_blocks[obj_type][efootprint_obj.id] = efootprint_obj.to_json(
                save_calculated_attributes=save_calculated_attributes)
            for attr_val in efootprint_obj.__dict__.values():
                if isinstance(attr_val, ExplainableObject) and attr_val.source is not None:
                    sources_by_id.setdefault(attr_val.source.id, attr_val.source)
                elif isinstance(attr_val, ExplainableObjectDict):
                    for elt in attr_val.values():
                        if isinstance(elt, ExplainableObject) and elt.source is not None:
                            sources_by_id.setdefault(elt.source.id, elt.source)

        output_json = {"efootprint_version": efootprint_version}
        if sources_by_id:
            output_json["Sources"] = {sid: src.to_json() for sid, src in sorted(sources_by_id.items())}
        output_json.update(modeling_blocks)

        return output_json

    def persist_to_cache(self):
        """Serialize current system state and persist it to the repository."""
        start = perf_counter()
        data_with_calculated_attributes = self.to_json(save_calculated_attributes=True)
        data_without_calculated_attributes = self.to_json(save_calculated_attributes=False)
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(f"Serialized system data in {round(elapsed_ms, 1)} ms.")
        self.repository.save_data(
            data_with_calculated_attributes,
            data_without_calculated_attributes=data_without_calculated_attributes
        )

    def _build_creation_constraints(self) -> dict:
        """Snapshot of per-class creation gates plus __results__.

        For class-based entries the dict carries only {"enabled", "disabled"} — tooltip
        copy is resolved at render time via the `constraint_tooltip` template filter so
        the domain never depends on adapter presentation strings. The special __results__
        entry additionally carries `reason` (the live validation errors) because those
        messages are computed here, not static copy.
        """
        from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
        from model_builder.domain.services import SystemValidationService

        constraints = {}
        seen_defining_classes = set()
        for web_class in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.values():
            if not hasattr(web_class, "can_create"):
                continue
            defining_class = next(c for c in web_class.__mro__ if "can_create" in c.__dict__)
            if defining_class in seen_defining_classes:
                continue
            seen_defining_classes.add(defining_class)
            enabled = web_class.can_create(self)
            constraints[defining_class.__name__] = {"enabled": enabled, "disabled": not enabled}

        validation_result = SystemValidationService().validate_for_computation(self)
        constraints["__results__"] = {
            "enabled": validation_result.is_valid,
            "disabled": not validation_result.is_valid,
            "reason": "" if validation_result.is_valid
                      else "\n\n".join(e.message for e in validation_result.errors),
        }
        return constraints

    def raise_incomplete_modeling_errors(self):
        """Validate system completeness and raise ValueError if incomplete."""
        from model_builder.domain.services import SystemValidationService
        validation_service = SystemValidationService()
        result = validation_service.validate_for_computation(self)
        result.raise_if_invalid()

    @staticmethod
    def _efootprint_object_from_json(json_input: dict, object_type: str, sources_dict: dict | None = None):
        efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
        efootprint_object, expl_obj_dicts_to_create_after_objects_creation = efootprint_class.from_json_dict(
            json_input, {}, False, False, sources_dict=sources_dict)
        assert len(expl_obj_dicts_to_create_after_objects_creation) == 0, \
            f"{object_type} object {efootprint_object.id} has explainable objects to create after objects creation"
        efootprint_object.after_init()

        return efootprint_object

    def get_efootprint_objects_from_efootprint_type(self, obj_type):
        output_list = []
        if obj_type in DEFAULT_OBJECTS_CLASS_MAPPING:
            sources_dict = DEFAULT_SOURCES_CLASS_MAPPING[obj_type]()
            for json_input in DEFAULT_OBJECTS_CLASS_MAPPING[obj_type]().values():
                output_list.append(self._efootprint_object_from_json(json_input, obj_type, sources_dict))

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
            sources_dict = DEFAULT_SOURCES_CLASS_MAPPING[object_type]()
            efootprint_object = self._efootprint_object_from_json(web_object_json, object_type, sources_dict)
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
    def web_explainable_quantities_sources(self):
        web_explainable_quantities_sources = []
        for efootprint_object in self.flat_efootprint_objs_dict.values():
            init_param_names = get_init_signature_params(efootprint_object.efootprint_class).keys()
            calculated_attribute_names = getattr(efootprint_object, "calculated_attributes", [])
            explainable_quantities = get_instance_attributes(efootprint_object, ExplainableQuantity)
            web_explainable_quantities_sources += [
                ExplainableQuantityWeb(explainable_object, self)
                for attr_name, explainable_object in explainable_quantities.items()
                if (
                    explainable_object.source is not None
                    and (attr_name in init_param_names or attr_name in calculated_attribute_names)
                )]

        return web_explainable_quantities_sources

    @property
    def available_sources(self):
        """Distinct Source instances referenced across the model, plus USER_DATA and HYPOTHESIS sentinels."""
        sources_by_id = {}
        for efootprint_obj in self.flat_efootprint_objs_dict.values():
            for attr_val in get_instance_attributes(efootprint_obj, ExplainableObject).values():
                if attr_val.source is not None:
                    sources_by_id.setdefault(attr_val.source.id, attr_val.source)
            for attr_dict in get_instance_attributes(efootprint_obj, ExplainableObjectDict).values():
                for elt in attr_dict.values():
                    if isinstance(elt, ExplainableObject) and elt.source is not None:
                        sources_by_id.setdefault(elt.source.id, elt.source)
        for sentinel in (Sources.USER_DATA, Sources.HYPOTHESIS):
            sources_by_id.setdefault(sentinel.id, sentinel)
        return sorted(sources_by_id.values(), key=lambda s: s.name)

    @property
    def storages(self):
        return self.get_web_objects_from_efootprint_type("Storage")

    @property
    def servers(self):
        return self.get_web_objects_from_efootprint_type("ServerBase")

    @property
    def external_apis(self):
        return self.get_web_objects_from_efootprint_type("ExternalAPI")

    @property
    def edge_devices(self):
        """Returns all edge devices."""
        all_edge_devices = self.get_web_objects_from_efootprint_type("EdgeDevice")
        return all_edge_devices

    @property
    def edge_device_groups(self):
        return self.get_web_objects_from_efootprint_type("EdgeDeviceGroup")

    @property
    def root_edge_device_groups(self):
        """Root-level groups (not sub-groups of any other group)."""
        return [group for group in self.edge_device_groups if not group.modeling_obj._find_parent_groups()]

    @property
    def ungrouped_edge_devices(self):
        """Edge devices not referenced by any group."""
        return [device for device in self.edge_devices if not device.modeling_obj._find_parent_groups()]

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
        if self._system_emissions is None:
            from model_builder.domain.services import EmissionsCalculationService

            service = EmissionsCalculationService()
            result = service.calculate_daily_emissions(self.system)
            self._system_emissions = result.to_dict()
        return self._system_emissions
