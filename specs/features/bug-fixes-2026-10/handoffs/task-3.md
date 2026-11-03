# Task 3 — Server-owned card removal

Repository and implementation range: `e-footprint-interface`, `47a9f48d158559a71bd9b0afd35b70590dca68f0..72c0a808`.
Companion library tested unchanged at `8793fd7ab101787179a544d9f276551fb28008b4`.

## Review pointers
- `DeleteObjectUseCase._delete` captures the canonical system-prefixed `web_id` before `self_delete`; list/nested deletion keeps its parent/mirror refresh path.
- `HtmxPresenter.present_deleted_object` emits the top-level OOB delete before targeted edge-list replacements and omits it when a canvas replacement already removes the card. This ordering matters for root edge groups.

## Open concerns
- The supervisor's combined Run A non-E2E, E2E and Jest gates remain pending; focused task validation is complete.
