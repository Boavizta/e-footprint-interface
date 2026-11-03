# Task 6 — Internal-object inspection and cardless input saves

Repositories and implementation ranges:
- Library: `318aa090cf4923fec672485d07c80c66611688eb..2540ffad786389aaafe753b7df2c9a3dbd232308`.
- Interface: `a7cf3363bf6f4285766691211d6340deb7f5ec00..eac07c0f514d0b5ff4b815d46d3809f9d4fb5228`.

## Review pointers
- `ModelingObjectWeb.has_canvas_card` mirrors the root families selected by `adapters/card_order.py::ordered_card_lists`, then uses existing constructor list/dict nesting and `renders_relationship_children_as_nested_cards`. Keep those root families aligned if canvas placement changes. Generated external-API servers inherit `ModelingObject`, not `ServerBase`; builder components are absent from their parent constructor signature. No new placement override or parent refresh is needed.
- Edited objects and automatic-repair owners check placement before mirror traversal. Parent-form storage edits and custom-device storage cards retain their existing paths.
- The rewritten reproduction selector is `tests/unit_tests/adapters/views/test_views_edition.py::TestViewsEdition::test_library_built_child_panel_shows_read_only_inspection`.
- Standalone mutation guards remain for Task 8; chart failure handling and duplicate calculated-attribute IDs remain for Tasks 9/10.
