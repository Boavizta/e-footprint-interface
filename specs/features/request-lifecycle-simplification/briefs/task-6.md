# Task 6 — Apply the lock everywhere
Written 2026-10-20 against `e-footprint-interface` commit `0da76e82`.
Plan: [PLAN-UPDATE-13](../plan.html#plan-update-13) (principle paragraph), [PLAN-UPDATE-09](../plan.html#plan-update-09).
Task: [Task 6](../tasks.md#task-6--apply-the-lock-everywhere).
Status: under review.

## Start here
- Run this scan first and keep its output as your worklist (tag-level, because the lock often sits on another line of the same tag):

```python
import re, pathlib
tag_re = re.compile(r'<([a-zA-Z][\w-]*)\b([^>]*)>', re.S)
for p in list(pathlib.Path("model_builder/templates").rglob("*.html")) + list(pathlib.Path("theme/templates").rglob("*.html")):
    s = p.read_text()
    for m in tag_re.finditer(s):
        a = m.group(2)
        if re.search(r'\bhx-(get|post|patch|put|delete)=', a) and "hx-disabled-elt" not in a:
            print(p, s.count("\n", 0, m.start()) + 1, m.group(1), re.search(r'hx-trigger="([^"]*)"', a))
```
  At `0da76e82` it lists 31 tags. Classify each as (a) inherits the lock from an ancestor (HTMX inherits `hx-disabled-elt`; check the enclosing form or container), (b) user-initiated and unlocked → add the lock, or (c) background → leave and document.
- Script-issued requests: `grep -rn "htmx.ajax(" theme/static/scripts`. User-initiated ones (side-panel opens in `side_panel_utils.js`, support/help drawer, `model_comparison.js` import panel) get the lock; previews (`timeseries_preview.js`), autosaves (`source_metadata.js`), storage polls (`model_builder_main.js`, `sankey.js`) are background.
- The convention bullet Task 5 added to `specs/conventions.md`.

## Change along the code path
1. For each (b) element add `hx-disabled-elt="button:not(:disabled)"` on the element itself (or on the enclosing form when the form issues the request). Use exactly the project selector; do not invent per-element variants. Inside Simplified inputs use the workspace selector from `editor.html` where the element lives in a workspace.
2. For script-issued user requests, pass `source` as an element that carries the lock, or add `hx-disabled-elt` to the element already passed as `source`; verify in the vendored HTMX 2.0.6 how `htmx.ajax` resolves `hx-disabled-elt` (Task 5's handoff records the answer).
3. Background set: list it in the conventions bullet and remove the "separate follow-up" sentence Task 5 wrote.
4. Changelog: one sentence in the feature's Changed entry that every user action now locks buttons until it completes.

## Earlier tasks
Task 5 locked the slot during reads and wrote the convention. Task 1 made every lock skip already-disabled controls, so adding locks cannot re-enable prerequisite-disabled buttons.

## Invariants and traps
- Decision 4's accepted edge remains for overlaps with background requests; do not add listeners for it.
- Model tab strip: a locked tab during a switch must not break `switchModelCanvas` or the compare flow; run the compare and two-model E2E tests after changing it.
- `hx-trigger="click once"` lazy loads (source table rows, Results source table) are reads of their own region: background.
- The `data-autosave-*` widgets (confidence menu) are background by convention; leave them.
- Do not add `hx-sync` anywhere. The field editor's `hx-sync="this:drop"` stays (single-element dedupe).

## Validation
E2E spot checks with `page.route` holds: a membership link, a model-tab switch, a bookmark save, and one side-panel open from a card. Then `npm run build:js:dev`, `npm run jest`, `poetry run pytest tests --ignore=tests/e2e`, `poetry run pytest tests/e2e -n 4` against a local server.

## Out of scope
Changing what any request does, its target or its indicator; the parked pre-existing `htmx:oobErrorNoTarget` defects.

## Unverified
Whether every element classified (a) really inherits: HTMX stops inheritance at `hx-disinherit`; grep for it and check.
