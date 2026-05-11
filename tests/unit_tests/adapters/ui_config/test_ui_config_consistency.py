"""Consistency invariants for class_ui_config.json and the UI token registry.

These guard the JSON edits in Step 3 (and any future ones) — every class key
must reference a real efootprint class, every concrete class must be reachable
via direct entry or MRO inheritance, and every {ui:token} used in interactions
must have a registered handler.
"""
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.utils.placeholder_resolver import extract_placeholders

from model_builder.adapters.ui_config import CLASS_UI_CONFIG
from model_builder.adapters.ui_config.ui_token_registry import UI_TOKENS
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING


# Concrete classes that intentionally do not have a `class_ui_config.json` entry.
# Add a one-line justification next to each entry.
EXCLUDED_CLASSES_FROM_UI_CONFIG: dict[str, str] = {
    "EcoLogitsGenAIExternalAPIServer": "Internal server stub spawned by EcoLogitsGenAIExternalAPI; never user-created.",
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
    # Accept either an efootprint class (concrete or abstract) or an interface-side
    # abstract base that has a web wrapper (e.g. EdgeDeviceBase, RecurrentEdgeDeviceNeedBase).
    valid = set(ALL_EFOOTPRINT_CLASSES_DICT.keys()) | set(EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.keys())
    unknown = set(CLASS_UI_CONFIG.keys()) - valid
    assert not unknown, f"class_ui_config.json keys not in efootprint classes or web mapping: {unknown}"


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
