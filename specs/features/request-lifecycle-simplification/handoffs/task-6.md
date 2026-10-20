# Task 6 — Apply the lock everywhere
Repository and implementation range: `e-footprint-interface` `08580a91..0ece3445`, handoff after it.

## Scan
Brief's tag-level scan: 31 tags without their own `hx-disabled-elt` before, 8 after. The 8 remaining are 1 inheriting and 7 background.

| Element | Class |
|---|---|
| `active_model_role.html` switch item | locked now |
| `help_menu.html` Open examples; Data & privacy boosted link (not in the scan) | locked now |
| `model_tab_strip.html` tab label, ✕ remove, +Add Duplicate, +Add Blank, ⇄Compare | locked now |
| `upload_download_reboot_model_tooltips.html` burger Compare, Duplicate, Blank | locked now |
| `dict_entry_count_unlink.html` count input and unlink ✕ | locked now |
| `dict_membership_section.html` link; `list_membership_section.html` unlink and link | locked now |
| `edit_panel__generic.html`, `edit_recurrent_edge_component_need.html` ask-delete | locked now |
| `data_privacy.html` retention form | locked now |
| `source_table_row_editor.html` form | locked now |
| `sankey_section.html` Add another analysis view | locked now |
| `bookmark.html` `<details>` (bookmark-save) | locked now |
| `timeseries_panel.html` form | locked now |
| `home.html` Start modeling | locked now |
| `workspace_storage_status.html` boosted link (not in the scan) | locked now |
| `bookmark.html` lazy controls (`bookmark-open once`) | inherits from its `<details>` |
| `editor.html` Edit timeseries | inherits from the editor form |
| `result_panel.html` Sources ×2 (`click once`) | background |
| `source_table_row.html` row editor load (`click once`) | background |
| `sankey_card.html` settings form, diagram `load` div | background |
| `sankey_section.html` cards `load` div | background |

Normalized to the project selector: reset (`hx-disabled-elt="this"`) and both example-picker buttons.

## Script-issued requests
- Help drawer: source `#helpDrawer`, which now carries the lock. The clicked trigger cannot be the source because tour.js clicks a removed button. Nothing inside the drawer uses `hx-*`.
- +Add Import: the trigger is the source; both trigger buttons carry the lock.
- Unsaved-modal Continue: the deferred element is the source, so it behaves like the original click.
- Feedback links already passed `source: link`; both links now carry the lock.
- Background, unchanged: previews, confidence autosave, storage status refreshes, Simplified slot (already locked).

## Review pointers
- `test_delayed_count_save_leaves_reading_available` asserted the old unlocked behavior. It is now `test_delayed_count_save_locks_buttons_until_it_ends`.
- New or extended held-request checks: model switch, list-membership link, bookmark save, unsaved-modal Continue.
- The bookmark lazy-controls load now inherits its bookmark's lock and briefly disables buttons on first open.

## Open concerns
- Non-HTMX `fetch` requests stay unlocked: Sankey card deletion and card-order save. They are outside the HTMX lock mechanism.
