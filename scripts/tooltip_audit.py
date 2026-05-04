"""Audit `field_ui_config.json` tooltips against efootprint `param_descriptions`.

Investigation tool for Step 3 of the tutorial-and-documentation plan: identify
tooltips currently held in the interface's `field_ui_config.json` that should
be merged into (or replaced by) library-side `param_descriptions`, so the
single-source-of-truth lives next to each modeling class.

For every field that carries a `tooltip`, the script lists:
  - the raw tooltip text;
  - every container class declared in `modeling_obj_containers`;
  - whether that class defines a `param_descriptions` entry for the field;
  - the description text when present, "(missing)" when absent.

When the same field is declared on multiple container classes, divergent
descriptions are flagged so the merge decision can take both into account.

Run from the interface repo root:

    /Users/vinville/Library/Caches/pypoetry/virtualenvs/efootprint-interface-VnNRFR-T-py3.13/bin/python \
        specs/features/tutorial-and-documentation/scripts/tooltip_audit.py
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from dataclasses import dataclass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT  # noqa: E402

FIELD_UI_CONFIG_PATH = os.path.join(
    REPO_ROOT, "model_builder", "adapters", "ui_config", "field_ui_config.json")


@dataclass
class ContainerEntry:
    class_name: str
    has_class: bool
    description: str | None  # None means class has no entry; "" allowed but unusual


def load_field_ui_config() -> dict:
    with open(FIELD_UI_CONFIG_PATH) as f:
        return json.load(f)


def collect_param_description(class_name: str, field: str) -> ContainerEntry:
    cls = MODELING_OBJECT_CLASSES_DICT.get(class_name)
    if cls is None:
        return ContainerEntry(class_name=class_name, has_class=False, description=None)
    descriptions = getattr(cls, "param_descriptions", {}) or {}
    description = descriptions.get(field)
    return ContainerEntry(class_name=class_name, has_class=True, description=description)


def normalize(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(text.split())


def print_field_block(field: str, tooltip: str, label: str, entries: list[ContainerEntry]) -> None:
    bar = "=" * 88
    print(bar)
    print(f"FIELD: {field}    (label: {label!r})")
    print("-" * 88)
    print("Interface tooltip:")
    for line in textwrap.wrap(tooltip, width=84):
        print(f"  {line}")
    print()

    print("Library param_descriptions per container class:")
    if not entries:
        print("  (no modeling_obj_containers declared)")
    else:
        unique_descriptions = {normalize(e.description) for e in entries if e.has_class}
        unique_descriptions.discard("")
        divergent = len(unique_descriptions) > 1
        for entry in entries:
            if not entry.has_class:
                tag = "[unknown class]"
                body = "(class not in MODELING_OBJECT_CLASSES_DICT)"
            elif entry.description is None:
                tag = "[missing]"
                body = "(no param_descriptions entry)"
            else:
                tag = "[present]"
                body = entry.description
            print(f"  {tag} {entry.class_name}:")
            for line in textwrap.wrap(body, width=80):
                print(f"      {line}")
        if divergent:
            print()
            print("  !! container classes disagree on this field's description")

    # Quick text similarity hint between tooltip and library entries.
    tooltip_norm = normalize(tooltip).lower()
    lib_matches = [
        e.class_name for e in entries
        if e.has_class and e.description is not None
        and tooltip_norm and tooltip_norm == normalize(e.description).lower()
    ]
    if lib_matches:
        print()
        print(f"  Tooltip text already matches library description for: {', '.join(lib_matches)}")
    print()


def main() -> int:
    field_config = load_field_ui_config()

    fields_with_tooltip = [
        (field, cfg) for field, cfg in field_config.items() if cfg.get("tooltip")
    ]

    print(f"Audited {FIELD_UI_CONFIG_PATH}")
    print(f"Found {len(fields_with_tooltip)} field(s) with a tooltip.\n")

    summary_rows: list[tuple[str, int, int, int]] = []  # field, n_containers, n_with_desc, n_missing

    for field, cfg in fields_with_tooltip:
        tooltip = cfg["tooltip"]
        label = cfg.get("label", "")
        containers = cfg.get("modeling_obj_containers", [])
        entries = [collect_param_description(name, field) for name in containers]
        print_field_block(field, tooltip, label, entries)

        n_with = sum(1 for e in entries if e.has_class and e.description)
        n_missing = sum(1 for e in entries if e.has_class and not e.description)
        summary_rows.append((field, len(entries), n_with, n_missing))

    # Compact summary at the bottom for at-a-glance review.
    print("=" * 88)
    print("SUMMARY")
    print("-" * 88)
    print(f"{'field':<42} {'#cls':>5} {'#desc':>6} {'#miss':>6}")
    for field, n_total, n_with, n_missing in summary_rows:
        print(f"{field:<42} {n_total:>5} {n_with:>6} {n_missing:>6}")
    print()

    fully_missing = [row for row in summary_rows if row[2] == 0]
    if fully_missing:
        print("Fields whose tooltip has NO library counterpart on any container class:")
        for field, *_ in fully_missing:
            print(f"  - {field}")
        print()

    partial = [row for row in summary_rows if 0 < row[3]]
    if partial:
        print("Fields where SOME container classes are missing the description:")
        for field, _n, _w, _m in partial:
            print(f"  - {field}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
