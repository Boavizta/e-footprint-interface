"""Guard the invariant that every constraint emitted by the domain has
presentation copy in CONSTRAINT_MESSAGES (and vice versa).

Without this test, renaming a web class, adding a new `can_create`, or tweaking
`_build_creation_constraints` will silently break toasts and disabled-button
tooltips.
"""
from model_builder.adapters.ui_config.constraint_messages import CONSTRAINT_MESSAGES
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING


def _defining_classes_for_can_create() -> set[str]:
    """Resolve the set of MRO-defining classes for `can_create` across all web classes.

    Mirrors the dedup logic in `ModelWeb._build_creation_constraints`.
    """
    seen = set()
    for web_class in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.values():
        if not hasattr(web_class, "can_create"):
            continue
        defining_class = next(c for c in web_class.__mro__ if "can_create" in c.__dict__)
        seen.add(defining_class.__name__)
    return seen


def test_constraint_messages_keys_match_domain_constraint_keys(minimal_model_web):
    """Every domain constraint key has a CONSTRAINT_MESSAGES entry, and every
    entry maps to a real domain key. `__results__` is always present."""
    domain_keys = set(minimal_model_web.creation_constraints.keys())
    message_keys = set(CONSTRAINT_MESSAGES.keys())

    assert "__results__" in domain_keys
    assert "__results__" in message_keys
    assert domain_keys == message_keys, (
        f"Domain-only keys: {domain_keys - message_keys}. "
        f"CONSTRAINT_MESSAGES-only keys: {message_keys - domain_keys}."
    )


def test_can_create_defining_classes_covered_by_messages():
    """Static check independent of a live ModelWeb: every `can_create` defining
    class has a matching CONSTRAINT_MESSAGES entry."""
    defining_classes = _defining_classes_for_can_create()
    missing = defining_classes - set(CONSTRAINT_MESSAGES.keys())
    assert not missing, f"Missing CONSTRAINT_MESSAGES entries for: {missing}"


def test_each_message_has_required_subkeys():
    """Each entry must expose tooltip + unlocked + locked copy."""
    required = {"unlocked", "locked", "tooltip"}
    for key, entry in CONSTRAINT_MESSAGES.items():
        missing = required - set(entry.keys())
        assert not missing, f"CONSTRAINT_MESSAGES[{key!r}] missing subkeys: {missing}"
        for subkey in required:
            assert entry[subkey], f"CONSTRAINT_MESSAGES[{key!r}][{subkey!r}] is empty"
