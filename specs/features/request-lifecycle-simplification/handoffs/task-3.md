# Task 3 — Bookmark fragments
Repositories and implementation ranges: `e-footprint-interface` `63a5284b..2b73f40c`.

## Review pointers
- The save-status rules moved out of `.simplified-workspace` to top level as `:is([data-simplified-save-status], [data-bookmark-status])`, because bookmarks render in side panels and Sources, outside the workspace. Specificity drops from two classes to one; Bootstrap's `.small` on the field status ties and loses on source order.
- Saved bookmarks declare `hx-disinherit="hx-indicator"`. Without it the lazy Sources controls inherit `find [data-bookmark-status]` and HTMX logs "returned no matches" on their GET.
- `data-saved-included` and `data-required-label` are gone from the template. Provisional code resets `requiredLabel` before reading it, so nothing read the rendered value.
- `updateBookmark` is now the unexported `updateProvisionalBookmark`.
- `test_inline_sources_creation_requirements_and_delete` also clicked Undo; it now unchecks the toggle instead.
- The failed-help E2E now fails through a server rejection rather than an aborted request, since an unanswered request leaves the status empty. It also holds the next request to check the cleared status and "Saving…".
- `test_failed_bookmark_preserves_the_panel_and_unsaved_value` now keeps the original form data when rewriting `patch`, so the 422 comes from the unknown owner rather than a missing `mounted`.

## Open concerns
- No bookmark flow logs `htmx:oobErrorNoTarget`. Unrelated E2E flows still do: edge device group linking, canvas inline counts and model comparison count saves.
