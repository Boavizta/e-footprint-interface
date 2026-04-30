import os
import json
from unittest import TestCase

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes
from efootprint.constants.countries import Countries
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from model_builder.domain.reference_data import DEFAULT_COUNTRIES, DEFAULT_DEVICES, DEFAULT_NETWORKS

root_dir = os.path.dirname(os.path.abspath(__file__))


class TestsReferenceData(TestCase):
    def test_default_objects(self):
        default_efootprint_networks = [network_archetype() for network_archetype in Network.archetypes()]
        default_efootprint_hardwares = [Device.laptop(), Device.smartphone()]
        efootprint_countries = []
        for attr_value in vars(Countries).values():
            if callable(attr_value):
                efootprint_countries.append(attr_value())

        def create_object_dict(object_list: list):
            output_dict = {}
            for elt in object_list:
                output_dict[elt.id] = elt.to_json()

            return output_dict

        network_archetypes = create_object_dict(default_efootprint_networks)
        hardware_archetypes = create_object_dict(default_efootprint_hardwares)
        countries = create_object_dict(efootprint_countries)

        default_networks = DEFAULT_NETWORKS
        default_devices = DEFAULT_DEVICES
        default_countries = DEFAULT_COUNTRIES

        def strip_volatile_keys(d):
            if isinstance(d, dict):
                return {k: strip_volatile_keys(v) for k, v in d.items() if k not in ("id", "source")}
            return d

        def check_dict_equality_ignoring_ids(dict1, dict2):
            for subdict1, subdict2 in zip(list(dict1.values()), list(dict2.values())):
                self.assertDictEqual(strip_volatile_keys(subdict1), strip_volatile_keys(subdict2))

        check_dict_equality_ignoring_ids(network_archetypes, default_networks)
        check_dict_equality_ignoring_ids(hardware_archetypes, default_devices)
        check_dict_equality_ignoring_ids(countries, default_countries)


if __name__ == "__main__":
    import os as script_os
    domain_ref_dir = script_os.path.join(
        script_os.path.dirname(__file__), "..", "..", "..", "model_builder", "domain", "reference_data")

    def recompute_default_object_json_files(efootprint_object_list, filename):
        json_dump = {}
        sources_dict = {}
        for elt in efootprint_object_list:
            json_dump[elt.id] = elt.to_json()
            for attr_val in get_instance_attributes(elt, ExplainableObject).values():
                if attr_val.source is not None and attr_val.source.id not in sources_dict:
                    sources_dict[attr_val.source.id] = attr_val.source.to_json()
        json_dump["Sources"] = sources_dict

        with open(script_os.path.join(domain_ref_dir, filename), "w") as f:
            json.dump(json_dump, f, indent=4)


    efootprint_countries = []
    for attr_value in vars(Countries).values():
        if callable(attr_value):
            efootprint_countries.append(attr_value())
    recompute_default_object_json_files(efootprint_countries, "default_countries.json")

    efootprint_devices = [Device.laptop(), Device.smartphone()]
    recompute_default_object_json_files(efootprint_devices, "default_devices.json")

    efootprint_networks = [archetype() for archetype in Network.archetypes()]
    recompute_default_object_json_files(efootprint_networks, "default_networks.json")
