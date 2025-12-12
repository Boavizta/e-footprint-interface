"""Domain reference data.

Contains default configurations for domain objects (countries, devices, networks, systems).
"""
import os
import json

_root = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_root, "default_countries.json"), "r") as f:
    DEFAULT_COUNTRIES = json.load(f)

with open(os.path.join(_root, "default_devices.json"), "r") as f:
    DEFAULT_DEVICES = json.load(f)

with open(os.path.join(_root, "default_networks.json"), "r") as f:
    DEFAULT_NETWORKS = json.load(f)

with open(os.path.join(_root, "default_system_data.json"), "r") as f:
    DEFAULT_SYSTEM_DATA = json.load(f)
