"""Drift guards for EDGE_EFOOTPRINT_CLASS_NAMES vs. the efootprint mapping."""
from unittest.mock import MagicMock

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.modeling_paradigm import EDGE_EFOOTPRINT_CLASS_NAMES, paradigm_for


def test_edge_class_names_is_subset_of_mapping_keys():
    missing = EDGE_EFOOTPRINT_CLASS_NAMES - set(EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING)
    assert not missing, f"Edge class names not in the mapping: {sorted(missing)}"


def test_edge_classification_matches_efootprint_module_path():
    """For every concrete class in the mapping, "module path contains an edge segment" iff classified edge.

    Catches drift in both directions: a new edge class added to the mapping without joining
    EDGE_EFOOTPRINT_CLASS_NAMES, and a name kept in the set after the underlying class moves
    out of an edge module. Interface-side aliases (e.g. EdgeDeviceBase) that have no concrete
    efootprint class are skipped because there is no module path to consult.
    """
    mismatches = []
    for class_name in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING:
        efootprint_cls = MODELING_OBJECT_CLASSES_DICT.get(class_name)
        if efootprint_cls is None:
            continue
        module_is_edge = ".edge." in efootprint_cls.__module__ or efootprint_cls.__module__.endswith(".edge")
        set_says_edge = class_name in EDGE_EFOOTPRINT_CLASS_NAMES
        if module_is_edge != set_says_edge:
            mismatches.append((class_name, efootprint_cls.__module__, set_says_edge))
    assert not mismatches, (
        f"Module-path vs. EDGE_EFOOTPRINT_CLASS_NAMES disagree: {mismatches}")


def test_paradigm_for_known_examples():
    assert paradigm_for("EdgeDevice") == "edge"
    assert paradigm_for("Server") == "web"


def test_modeling_paradigm_property_for_every_mapped_web_class():
    """Each web wrapper exposes modeling_paradigm that matches the class_name's paradigm."""
    seen = set()
    for class_name, web_class in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.items():
        if web_class in seen:
            continue
        seen.add(web_class)
        modeling_obj = MagicMock()
        modeling_obj.class_as_simple_str = class_name
        instance = web_class(modeling_obj, MagicMock())
        expected = "edge" if class_name in EDGE_EFOOTPRINT_CLASS_NAMES else "web"
        assert instance.modeling_paradigm == expected, (
            f"{web_class.__name__} for class_name={class_name} returned "
            f"{instance.modeling_paradigm!r}, expected {expected!r}")


def test_modeling_object_web_base_class_modeling_paradigm():
    modeling_obj = MagicMock()
    modeling_obj.class_as_simple_str = "EdgeDevice"
    wrapper = ModelingObjectWeb(modeling_obj, MagicMock())
    assert wrapper.modeling_paradigm == "edge"

    modeling_obj.class_as_simple_str = "Server"
    assert wrapper.modeling_paradigm == "web"
