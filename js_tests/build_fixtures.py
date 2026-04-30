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
    return (
        render_to_string(
            "model_builder/side_panels/dynamic_form_fields/confidence_badge.html",
            {"field": field_ctx},
        )
        + render_to_string(
            "model_builder/side_panels/dynamic_form_fields/source.html",
            {"field": field_ctx},
        )
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
