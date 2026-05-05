"""Render Django partials used by jest tests into static HTML fixtures.

Run ahead of `jest` so the JS tests load real template output instead of a
hand-rolled approximation. The npm `jest` script chains this in front of jest;
running it directly works too:

    poetry run python js_tests/build_fixtures.py

To add a fixture, append an entry to the relevant manifest below — keep them
flat, duplication is fine. Naming convention: `<domain>_<shape>` so both the
fixture file and the test reference are self-describing.
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import django

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "e_footprint_interface.settings")
django.setup()

from django.template.loader import render_to_string  # noqa: E402

OUT_DIR = REPO_ROOT / "js_tests" / "fixtures"


# ---------------------------------------------------------------------------
# source_metadata.test.js — confidence_badge.html + source.html (+ source_editor.html via include)
# ---------------------------------------------------------------------------

SRC1 = {"id": "src1", "name": "ADEME 2024", "link": "https://ademe.fr"}
HYPOTHESIS = {"id": "hypothesis", "name": "e-footprint hypothesis", "link": ""}
USER_DATA = {"id": "user_data", "name": "user data", "link": ""}
SENTINELS = [USER_DATA, HYPOTHESIS]


def metadata_field(web_id="Compute_cpu_cores", confidence=None, source=None, comment="", available_sources=()):
    return {
        "web_id": web_id,
        "metadata": {
            "confidence": confidence,
            "comment": comment,
            "source": source,
            "available_sources": list(available_sources),
        },
    }


# A value is either a single field dict or a list of field dicts (rendered
# back-to-back into one fixture, for tests that mount sibling fields).
SOURCE_METADATA_CASES = {
    "field_empty": metadata_field(),
    "field_high_no_source": metadata_field(confidence="high"),
    "field_src_listed": metadata_field(available_sources=[SRC1]),
    "field_src_selected_with_comment": metadata_field(
        source=SRC1, comment="vetted note", available_sources=[SRC1]),
    "field_unlisted_source": metadata_field(
        source={"id": "abc123", "name": "Internal", "link": ""},
        available_sources=[SRC1],
    ),
    "field_hypothesis_with_comment": metadata_field(
        source=HYPOTHESIS, comment="keep me", available_sources=SENTINELS),
    "field_src_with_sentinels": metadata_field(
        source=SRC1, available_sources=[SRC1, *SENTINELS]),
    "field_high_hypothesis": metadata_field(
        confidence="high", source=HYPOTHESIS, available_sources=SENTINELS),
    "two_empty_fields": [metadata_field(web_id="FieldA"), metadata_field(web_id="FieldB")],
}


def render_metadata_field(field_ctx):
    web_id = field_ctx["web_id"]
    metadata = field_ctx["metadata"]
    return (
        render_to_string(
            "model_builder/side_panels/dynamic_form_fields/confidence_badge.html",
            {
                "conf_dom_id": web_id,
                "conf_name_prefix": web_id,
                "conf_current": metadata["confidence"],
            },
        )
        + render_to_string(
            "model_builder/side_panels/dynamic_form_fields/source.html",
            {
                "source_dom_id": web_id,
                "source_name_prefix": web_id,
                "source_meta_source": metadata["source"],
                "source_meta_comment": metadata["comment"],
                "source_meta_available": metadata["available_sources"],
            },
        )
    )


# ---------------------------------------------------------------------------
# source_metadata.test.js — source_table_row_editor.html (in-form source editor)
# ---------------------------------------------------------------------------

ROW_EDITOR_AVAILABLE = [SRC1, USER_DATA]


def row_editor(prior_source, prior_comment="", available_sources=ROW_EDITOR_AVAILABLE):
    return {
        "prior_source": prior_source,
        "prior_comment": prior_comment,
        "available_sources": list(available_sources),
    }


ROW_EDITOR_CASES = {
    # priorId is in the available list (sentinel) — init keeps the select on it.
    "row_editor_listed_user_data": row_editor(prior_source=USER_DATA),
    # priorId is in the available list (a known source) — init keeps the select on it.
    "row_editor_listed_src1": row_editor(prior_source=SRC1),
    # priorId isn't in the available list — init flips the select to __custom__ + prefills name/link.
    "row_editor_unlisted_custom": row_editor(
        prior_source={"id": "abc123", "name": "Internal", "link": ""}),
}


def render_row_editor(case_ctx):
    src = case_ctx["prior_source"]
    eq = SimpleNamespace(
        web_id="row1",
        comment=case_ctx["prior_comment"],
        source=SimpleNamespace(id=src["id"], name=src["name"], link=src["link"]),
        modeling_obj_container=SimpleNamespace(efootprint_id="obj1"),
    )
    return render_to_string(
        "model_builder/result/source_table_row_editor.html",
        {
            "eq": eq,
            "field_name_prefix": "Server_compute",
            "available_sources": [
                SimpleNamespace(id=s["id"], name=s["name"], link=s["link"])
                for s in case_ctx["available_sources"]
            ],
            "edit_object_url": "/edit/obj1/",
        },
    )


# ---------------------------------------------------------------------------
# source_metadata.test.js — source_table_row.html display cells
# ---------------------------------------------------------------------------

SOURCE_TABLE_ROW_CASES = {
    "source_table_row_listed_user_data": row_editor(prior_source=USER_DATA),
    "source_table_row_listed_src1": row_editor(prior_source=SRC1, prior_comment="old note"),
}


def render_source_table_row(case_ctx):
    src = case_ctx["prior_source"]
    eq = SimpleNamespace(
        web_id="row1",
        label="compute",
        display_magnitude="12",
        display_unit="cpu_core",
        confidence=None,
        comment=case_ctx["prior_comment"],
        is_calculated=False,
        attr_name_in_mod_obj_container="compute",
        source=SimpleNamespace(id=src["id"], name=src["name"], link=src["link"]),
        modeling_obj_container=SimpleNamespace(
            efootprint_id="obj1",
            name="Server A",
            class_as_simple_str="Server",
        ),
    )
    return render_to_string(
        "model_builder/result/source_table_row.html",
        {"explainable_quantity": eq},
    )


# ---------------------------------------------------------------------------
# dict_count.test.js — dict_count.html
# ---------------------------------------------------------------------------

def dict_count_field(web_id, options, selected=None):
    selected = selected or {}
    return {
        "web_id": web_id,
        "options": options,
        "selected_json": json.dumps(selected),
        "options_json": json.dumps(options),
    }


DICT_COUNT_CASES = {
    "dict_count_two_options_empty": dict_count_field(
        web_id="EdgeDeviceGroup_edge_device_counts",
        options=[
            {"value": "device-1", "label": "Device 1"},
            {"value": "device-2", "label": "Device 2"},
        ],
    ),
}


def render_dict_count(field_ctx):
    return render_to_string(
        "model_builder/side_panels/dynamic_form_fields/dict_count.html",
        {"field": field_ctx},
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GROUPS = [
    (SOURCE_METADATA_CASES, render_metadata_field),
    (ROW_EDITOR_CASES, render_row_editor),
    (SOURCE_TABLE_ROW_CASES, render_source_table_row),
    (DICT_COUNT_CASES, render_dict_count),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for cases, render in GROUPS:
        for name, spec in cases.items():
            fields = spec if isinstance(spec, list) else [spec]
            html = "".join(render(f) for f in fields)
            (OUT_DIR / f"{name}.html").write_text(html, encoding="utf-8")
            total += 1
    print(f"Wrote {total} fixtures to {OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
