# Task 5 — Reads lock like saves
Repositories and implementation ranges: `e-footprint-interface` `0da76e82..9d797047`, review fix after it on `dev`.

## Review pointers
- HTMX 2.0.6 resolves `hx-disabled-elt` from the request source with the closest-attribute lookup, so `htmx.ajax(..., {source: target})` locks with the slot's selector and puts the request class on the slot. No call-site option was needed.
- The slot's lock is inherited by requests issued inside it (review removed an `hx-disinherit`). Today every such request sits under a closer lock: the field editor (including its timeseries open button) and the Configure form. No bookmark renders inside the slot.
- Model switches are issued only by `<button>`s (tab labels, mobile role dropdown items), and every read-issuing control is a button. `test_late_read_lands_in_its_slot_and_is_shown_on_return` is deleted along with the workspace-page sentence.
- The loader is a pure CSS block on `[data-simplified-target].htmx-request`: dimmed, non-clickable children and a spinner pseudo-element reusing Bootstrap's `spinner-border` keyframes. It gives an empty slot a minimum height on first entry.
- The double-click test asserts exactly one request. The held-read test asserts the request class, the spinner, and the disabled then enabled Configure, toolbar toggle and both model tabs. Both tests fail when the slot's lock is removed.

## Open concerns
- None.
