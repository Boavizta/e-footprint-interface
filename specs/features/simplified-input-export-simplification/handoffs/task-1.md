# Task 1 — Replace export continuation with saved-state admission

Repository and implementation range: `e-footprint-interface` — `751511d97767857e3ca45d86847e65e52fe42e20..f6eee07e430a61fb7513863d710347cbc42878db`.

## Review pointers

- `theme/static/scripts/simplified_inputs/index.js` intercepts dirty Configure at window capture before Bootstrap; busy activation remains owned by the existing shared guard. `workspace.js` exempts export before pending-read cancellation while retaining other Configure exit continuations.
- `js_tests/simplified_inputs.test.js` loads the real guard after the simplified-input module. Actual focus ordering, Bootstrap toggling and downloaded contents remain the browser verification owned by [Task 2](../briefs/task-2.md).
