"""Domain reference data.

Contains default configurations for domain objects (countries, devices, networks, systems).
"""
import os
import json

from efootprint.api_utils.json_to_system import build_sources_dict_from_system_dict

_root = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_root, "default_countries.json"), "r") as f:
    _countries = json.load(f)
    DEFAULT_COUNTRIES_SOURCES = build_sources_dict_from_system_dict(_countries)
    del _countries["Sources"]
    DEFAULT_COUNTRIES = _countries

with open(os.path.join(_root, "default_devices.json"), "r") as f:
    _devices = json.load(f)
    DEFAULT_DEVICES_SOURCES = build_sources_dict_from_system_dict(_devices)
    del _devices["Sources"]
    DEFAULT_DEVICES = _devices

with open(os.path.join(_root, "default_networks.json"), "r") as f:
    _networks = json.load(f)
    DEFAULT_NETWORKS_SOURCES = build_sources_dict_from_system_dict(_networks)
    del _networks["Sources"]
    DEFAULT_NETWORKS = _networks

with open(os.path.join(_root, "default_system_data.json"), "r") as f:
    DEFAULT_SYSTEM_DATA = json.load(f)
