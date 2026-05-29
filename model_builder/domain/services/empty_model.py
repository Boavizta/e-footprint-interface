"""Predicate that decides whether the builder was entered with an empty model.

The first-run template picker is shown whenever the model is empty (spec §4). A
serialized system carries metadata keys (``efootprint_version``, ``Sources``,
``interface_config``, ``efootprint_interface_version``) alongside the efootprint
*object* blocks, whose keys are efootprint class names. The model is "empty" when
the only object block present is ``System`` (an empty named system with no
journeys, servers, or patterns) — or when there is no system data at all.

Keying off membership in ``ALL_EFOOTPRINT_CLASSES_DICT`` rather than a hardcoded
exclusion list means a new top-level metadata key can never be mistaken for
content: only real class blocks count. ``test_empty_model_predicate`` asserts the
serializer's metadata keys stay outside that class set, so a serializer change
that introduced a colliding key would fail loudly.
"""
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT


def is_empty_model(system_data: dict | None) -> bool:
    if not system_data:
        return True
    object_class_keys = {key for key in system_data if key in ALL_EFOOTPRINT_CLASSES_DICT}
    return object_class_keys <= {"System"}
