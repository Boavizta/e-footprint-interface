# bug-fixes-2026-10 — gates (for the user, after the run)

The run of 2026-11-23: the one lot of the ported plan, `calculated-attribute-panel` (Tasks 9 and
10 of the earlier form). Runs of the earlier form (`tasks.md`, `plan.html`) keep no gates here.

## Standing calls

- **No user-held gate was sorted for the lot.** Its reason and its three pieces name no check on
  a device, no evidence to read and no operation after the run.
- **The supervisor ran on `claude-fable-5-2`**, not on the model `implementer-hard` pins
  (`claude-fable-5-1[1m]`).
- **No global review was run.** The delivery has one lot, which its reviewer read at FULL depth,
  and the plan gains the rest of run B in a second approval: the leads below wait for the review
  of that whole.
- **No `plan-review-guide` was written.** It is the close-out of the earlier form.
- **The acceptance of Tasks 9 and 10 on the shipped examples was not run**: the crawl of every
  hourly-chart link and the sweep for duplicate ids, which `tasks.md` holds and the ported plan
  does not.

## Checklist

Nothing. What is to answer is on the delivery page, not here: two edits and one question in
`#fragment-views-show-modal`.

## Post-run operations

Nothing.

## Evidence

Nothing.

## Watch in normal use

- **Opening an edge computer's panel** (one with a CPU, a RAM and a storage), calculated
  attributes unfolded: the storage's three empty per-usage-pattern entries read "no value", with a
  formula button and no chart button; each formula button of the CPU, the RAM and the storage
  opens the explanation in its own row, and still does on a second click.
- **A fragment that fails** in the calculated attributes, the delete confirmation, the Sources
  table, the Sankey settings and cards or the help drawer: the exception modal opens, and the
  panel behind it is left as it was.

## Parked

Nothing.

## Leads for the global review

From the reviewer of `calculated-attribute-panel`:

- **The dict's include by class is interim.** A library subclass of an hourly value, or a
  recurrent value, as an entry of a calculated dict has no template of its own or no dict branch.
  Nothing produces either today (the shipped examples hold hourly and empty entries only), and the
  top-level section carries the same risk (smell-sweep S6). Task 14's dispatch must cover the
  dict's include and a recurrent entry in a dict.
- **Seven HTMX fragment views are still undecorated**, the question of
  `#fragment-views-show-modal`. The test of S5, every fragment route decorated or exempt, is
  still absent; Task 15's example-wide invariants could hold it, with "no id twice in an edit
  panel".
- **The explanation ids come from the explainable's web id**, which has no system prefix. Task 12
  changes the modeling object's web id only: the two are independent, and the dict toggles mix
  both shapes.
- `render_exception_modal_if_error` has no `functools.wraps` (it was so before the lot): a
  decorated view loses its name.
- The EcoLogits explanation view and its template places are reached by the EcoLogits browser
  tests only: an edge model holds no EcoLogits attribute.
- Added by the lot: the test helper `_answer(response)` of
  `tests/unit_tests/adapters/views/test_views_calculated_attributes.py`, which classes a
  fragment's answer.

## End-of-run gate

Green on `767be804`, 2026-11-23, with no retry:

- `poetry run pytest --ignore=tests/e2e`: 1283 passed, 4 xfailed.
- `npm run jest`: 306 passed, 24 suites.
- `poetry run pytest tests/e2e -n 4`, on a local server: 175 passed, 2 skipped, 1 xfailed.

## Spend

```
Usage snapshot: 171 requests · USD API-equivalent (tokens only) · rates 2026-09-30
Known subtotal: 3.6939; unpriced: 20; unattributed: 0
Known tokens: input 356; cached 20,014,507; write 431,707; output 117,554
Coverage: 0 source errors; 14 registered intervals missing measurements. Standard mode assumed for 0 requests.
  gate: 0.0069 (follow-up 0.0000); 2 requests; claude-haiku-5-5; effort medium
  implementer: 0.0051 (follow-up 0.0000); 1 requests; claude-haiku-5-5; effort high
  implementer-easy: 0.5682 (follow-up 0.0000); 74 requests; claude-haiku-5-5; effort high
  light: 0.0037 (follow-up 0.0000); 5 requests; claude-haiku-5-5; effort medium
  reviewer: 3.1099 (follow-up 1.0261); 69 requests; claude-opus-5-5; effort high
  supervisor: 0.0000 (follow-up 0.0000); 20 requests; claude-fable-5-2; effort high
Unassigned-to-task overhead: 3.6939. No inference about completed-task quality or subscription limits.
  Unpriced: claude-fable-5-2: unknown model (20 requests)
```

A snapshot taken before the close-out. The supervisor's requests are unpriced, its model being
absent from the rate card: the subtotal is the sub-agents' alone.
