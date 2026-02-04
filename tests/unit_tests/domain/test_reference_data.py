import os
import json
from unittest import TestCase

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

        def check_dict_equality_ignoring_ids(dict1, dict2):
            for subdict1, subdict2 in zip(list(dict1.values()), list(dict2.values())):
                subdict1.pop("id", None)
                subdict2.pop("id", None)
                self.assertDictEqual(subdict1, subdict2)

        check_dict_equality_ignoring_ids(network_archetypes, default_networks)
        check_dict_equality_ignoring_ids(hardware_archetypes, default_devices)
        check_dict_equality_ignoring_ids(countries, default_countries)


if __name__ == "__main__":
    import os as script_os
    domain_ref_dir = script_os.path.join(
        script_os.path.dirname(__file__), "..", "model_builder", "domain", "reference_data")

    def recompute_default_countries():
        efootprint_countries = []
        for attr_value in vars(Countries).values():
            if callable(attr_value):
                efootprint_countries.append(attr_value())

        json_dump = {}
        for elt in efootprint_countries:
            json_dump[elt.id] = elt.to_json()

        with open(script_os.path.join(domain_ref_dir, "default_countries.json"), "w") as f:
            json.dump(json_dump, f, indent=4)

    recompute_default_countries()
