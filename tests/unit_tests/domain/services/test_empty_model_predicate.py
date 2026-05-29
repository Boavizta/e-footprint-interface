"""Unit tests for the empty-model predicate that triggers the first-run picker.

The predicate is "true when there is no content". Its robustness comes from keying
off efootprint *class* names rather than a hardcoded metadata exclusion list — so a
new top-level metadata key can never be mistaken for content. The drift guard below
asserts the serializer's metadata keys stay outside the class set, which is what
keeps them excluded (plan §4 risk "empty-model predicate drift").
"""
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT

from model_builder.domain.services import SCRATCH_ID, get_template_system_data, is_empty_model

# Keys the serializers (library + interface) emit alongside the object blocks.
SERIALIZER_METADATA_KEYS = {
    "efootprint_version", "Sources", "interface_config", "efootprint_interface_version",
}


def test_none_and_empty_are_empty():
    assert is_empty_model(None) is True
    assert is_empty_model({}) is True


def test_only_system_object_is_empty():
    system_data = {
        "efootprint_version": "21.1.2",
        "Sources": {"hypothesis": {"id": "hypothesis", "name": "x", "link": None}},
        "interface_config": {"some": "ui-state"},
        "efootprint_interface_version": "9.9.9",
        "System": {"uuid-system-1": {"name": "My system", "id": "uuid-system-1"}},
    }
    assert is_empty_model(system_data) is True


def test_scratch_baseline_is_empty():
    # The shipped "Start from scratch" default must read as empty, or the picker would
    # never show on a fresh session.
    assert is_empty_model(get_template_system_data(SCRATCH_ID)) is True


def test_model_with_real_object_is_not_empty():
    system_data = {
        "efootprint_version": "21.1.2",
        "System": {"uuid-system-1": {"name": "My system", "id": "uuid-system-1"}},
        "Server": {"srv-1": {"name": "Server", "id": "srv-1"}},
    }
    assert is_empty_model(system_data) is False


def test_introductory_template_is_not_empty():
    # An introductory template carries journeys, servers and patterns.
    assert is_empty_model(get_template_system_data("ecommerce")) is False


def test_serializer_metadata_keys_are_not_efootprint_classes():
    # Drift guard: the predicate ignores any top-level key that is not an efootprint class.
    # If the serializer ever emitted a metadata key colliding with a class name, the empty
    # model would stop reading as empty — this fails first.
    for key in SERIALIZER_METADATA_KEYS:
        assert key not in ALL_EFOOTPRINT_CLASSES_DICT, f"metadata key {key!r} collides with a class name"


def test_scratch_baseline_only_object_key_is_system():
    scratch = get_template_system_data(SCRATCH_ID)
    object_keys = {k for k in scratch if k in ALL_EFOOTPRINT_CLASSES_DICT}
    assert object_keys == {"System"}
    # Every non-object top-level key is known serializer metadata.
    assert set(scratch) - object_keys <= SERIALIZER_METADATA_KEYS
