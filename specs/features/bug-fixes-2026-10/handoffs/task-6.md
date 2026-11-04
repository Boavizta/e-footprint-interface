# Task 6 — Internal-object inspection and cardless input saves

Repositories and implementation ranges:
- Library: `318aa090cf4923fec672485d07c80c66611688eb..8793fd7ab101787179a544d9f276551fb28008b4`.
- Interface: `a7cf3363bf6f4285766691211d6340deb7f5ec00..eac07c0f514d0b5ff4b815d46d3809f9d4fb5228`.

## Review pointers
- Review cleanup starts after interface commit `415b0bfd`; its commit is the one introducing `adapters/canvas.py`. `canvas_root_lists` supplies both card ordering and `has_canvas_card`, which checks actual root membership before following existing constructor list/dict nesting and `renders_relationship_children_as_nested_cards`. Generated external-API servers are absent from the server root list; builder components are absent from their parent constructor signature. No new placement override or parent refresh is needed.
- The edit presenter checks placement before discovering refresh mirrors for edited objects and automatic-repair owners. The edit use case no longer prepares mirrors. Existing mutation-time mirror traversal remains unchanged, as do parent-form storage edits and visible custom-device storage cards. Broader lifecycle/wrapper work is parked in `specs/features/clean-architecture-refactoring/README.md`.
- The rewritten reproduction selector is `tests/unit_tests/adapters/views/test_views_edition.py::TestViewsEdition::test_library_built_child_panel_shows_read_only_inspection`.
- Task 8 owns the delivered standalone mutation guards; the cleanup leaves them unchanged. Chart failure handling and duplicate calculated-attribute IDs remain for Tasks 9/10.
