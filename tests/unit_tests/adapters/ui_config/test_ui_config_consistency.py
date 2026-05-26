"""Consistency invariants for class_ui_config.json and the UI token registry.

These guard the JSON edits in Step 3 (and any future ones) — every class key
must reference a real efootprint class, every concrete class must be reachable
via direct entry or MRO inheritance, and every {ui:token} used in interactions
must have a registered handler.
"""
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.utils.placeholder_resolver import extract_placeholders

from model_builder.adapters.ui_config import CLASS_UI_CONFIG
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.adapters.ui_config.ui_token_registry import UI_TOKENS
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.services.object_linking_service import dict_relationship_registry


# Interface-side abstract bases that legitimately key `class_ui_config.json` entries
# but do not exist as efootprint classes. Web-class names (e.g. `ServerWeb`) must
# never appear here — the JSON keys efootprint names only.
INTERFACE_ONLY_ABSTRACT_BASES: dict[str, str] = {
    "EdgeDeviceBase": "Interface-side abstract base spanning EdgeDevice + EdgeDeviceGroup for shared UI config.",
    "RecurrentEdgeDeviceNeedBase": "Interface-side abstract base for the RecurrentEdge*Need family.",
}


# Concrete classes that intentionally do not have a `class_ui_config.json` entry.
# Add a one-line justification next to each entry.
EXCLUDED_CLASSES_FROM_UI_CONFIG: dict[str, str] = {
    "EcoLogitsGenAIExternalAPIServer": "Internal server stub spawned by EcoLogitsGenAIExternalAPI; never user-created.",
    "EcoLogitsVideoGenExternalAPIServer": "Internal server stub spawned by EcoLogitsVideoGenExternalAPI; never user-created.",
    "ExternalAPIServer": "Internal server stub spawned by ExternalAPI; never user-created.",
    "RecurrentEdgeStorageNeed": "Internal subclass; not surfaced as a standalone Add target.",
    "RecurrentEdgeProcessRAMNeed": "Internal subclass; not surfaced as a standalone Add target.",
    "RecurrentEdgeProcessCPUNeed": "Internal subclass; not surfaced as a standalone Add target.",
    "RecurrentEdgeProcessStorageNeed": "Internal subclass; not surfaced as a standalone Add target.",
    "RecurrentEdgeWorkloadNeed": "Internal subclass; not surfaced as a standalone Add target.",
    "System": "Aggregate root; created implicitly, never via an Add button.",
}


# ---- {ui:token} resolution -------------------------------------------------

def _ui_tokens_used_in_interactions() -> set[str]:
    used = set()
    for entry in CLASS_UI_CONFIG.values():
        text = entry.get("interactions")
        if not text:
            continue
        for kind, target in extract_placeholders(text):
            if kind == "ui":
                used.add(target)
    return used


def test_every_ui_token_in_interactions_is_registered():
    used = _ui_tokens_used_in_interactions()
    missing = used - set(UI_TOKENS.keys())
    assert not missing, f"{{ui:...}} tokens used in class_ui_config.json without a UI_TOKENS entry: {missing}"


def test_every_ui_token_has_non_empty_display():
    for token, entry in UI_TOKENS.items():
        assert entry.get("display"), f"UI_TOKENS[{token!r}].display is empty"


# ---- class_ui_config.json completeness -------------------------------------

def test_every_class_ui_config_key_is_a_real_class():
    valid = set(ALL_EFOOTPRINT_CLASSES_DICT.keys()) | set(INTERFACE_ONLY_ABSTRACT_BASES.keys())
    unknown = set(CLASS_UI_CONFIG.keys()) - valid
    assert not unknown, (
        f"class_ui_config.json keys not in efootprint classes or INTERFACE_ONLY_ABSTRACT_BASES: {unknown}. "
        f"Add the class to the appropriate set with justification."
    )


def test_every_concrete_class_has_or_inherits_a_ui_config_entry():
    config_keys = set(CLASS_UI_CONFIG.keys())
    missing = []
    for class_name, klass in MODELING_OBJECT_CLASSES_DICT.items():
        if class_name in EXCLUDED_CLASSES_FROM_UI_CONFIG:
            continue
        # Direct entry or any ancestor with an entry counts.
        if any(ancestor.__name__ in config_keys for ancestor in klass.__mro__):
            continue
        missing.append(class_name)
    assert not missing, (
        f"Concrete classes without a CLASS_UI_CONFIG entry (own or via MRO): {missing}. "
        f"Add an entry, or list them in EXCLUDED_CLASSES_FROM_UI_CONFIG with a justification."
    )


# ---- field_ui_config.json membership wording ------------------------------

def test_every_dict_relationship_has_membership_wording_configured():
    """Membership sections render automatically for every dict relationship in the registry, so each
    one must carry its UI wording in field_ui_config.json — otherwise the runtime falls back to
    generic "Membership"/"Add" labels and the gap ships invisibly."""
    missing = []
    for parent_class, attr_name, _ in dict_relationship_registry():
        config = FieldUIConfigProvider.get_config(attr_name, parent_class.__name__)
        for key in ("membership_title", "add_to_label", "count_label"):
            if not config.get(key):
                missing.append(f"{parent_class.__name__}.{attr_name}: {key}")
    assert not missing, (
        f"Dict relationships missing membership wording in field_ui_config.json: {missing}. "
        f"Add the keys under the attribute entry (class-qualified key if the attr name is shared)."
    )
