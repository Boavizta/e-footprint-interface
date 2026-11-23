# Bug batches on the comprehension harness — experiment

The comprehension harness plans a feature as pieces written into the code. A bug batch still uses
the earlier form (`tasks.md`, diagnostics, a hand-written `plan.html`). This experiment ports
`bug-fixes-2026-10` runs B and C to the harness, one bug at a time, to find what the harness needs
to plan and fix bugs well.

It is an experiment on the harness, not a feature of the product: it has no spec, no approval and
no delivery of its own. Each change to the harness is decided on the bug in hand, made small, and
held by the harness's own tests. This file is named `experiment.md` so that the tools, which read a
feature folder's `plan.md`, leave it alone.

## What stays fixed

- `specs/features/bug-fixes-2026-10/plan.html` is the baseline and is not edited. Each ported bug
  is compared with its section there.
- The ported plan lives beside it: `specs/features/bug-fixes-2026-10/plan.md`, the sites in the
  code, and the page generated at `specs/comprehension_harness/plans/bug-fixes-2026-10.html`. The
  piece tags keep the batch's name.
- `diagnostics/*.md` stay as the record of each investigation.

## The loop, once per bug

1. Port the bug with the harness as it is.
2. Compare the generated page with the bug's section of the baseline, and write the gaps below.
3. Add the smallest primitive the comparison asks for, and render again.
4. Implement the fix through the new form.
5. Pick the next bug for the gap it probes.

## Order

| Bug | Why here | State |
|---|---|---|
| Task 9 — empty calculated dict entries | In-process reproduction, the baseline's richest chain of values, four Python links and one template link | Ported, then ported again on the four harness changes it asked for. Next: the reviewer reads its page, then the fix |
| Task 10 — explanation ids per item | Template-only: first use of a template site. Shares Task 9's test file | |
| Task 7 — "each hour" after the unit | Template-only: second use of the template site | |
| Task 16 — group-member confirmation | Pure Python, no reproduction yet: one written from scratch with the new primitives | |
| Task 12 — system prefix first in card ids | Cause in Python, symptom in a jest test: two evidence tests joined at the piece | |
| Task 2 — membership-section region | Symptom in a browser: an in-process cause test, and the browser test served by `live_server` | |
| Run C — Tasks 13, 14, 15 | Refactors: the check that the bug primitives stay optional | |
| A JavaScript stack, then Task 1 | Task 1 is pure JavaScript; it waits for a stack that gives its code sites | |

The order follows what each bug probes and can change after any of them. Task 10 depends on
Task 9; Task 13 follows Task 16.

## The primitives

Built on Task 9, and stated for a reader in `specs/workflow-formats.md` § "A bug":

- **A reproduction**: `@reproduces("<feature>#<slug>: <title>")`, a written test a run expects to
  fail. Several per piece. Its story is kept whatever it crossed, with how it failed.
- **Evidence**: `planned.evidence(tag, sentence, watch, expect={…})`, a place the bug shows, which
  marks no change and goes with the fix. `expect` is what the place should see: a literal, or a
  lambda where the right value depends on the crossing.
- **The chain on the page**: under the piece, each reproduction, the places it crossed in run order
  with the values seen, in red against the expected one, then the failure's message.
- **A debug button on each reproduction**, on the route the narratives' button uses.
- **A template site**: `{% narrate %}`, `{% event %}`, `{% planned %}` and `{% evidence %}`, tags of
  `model_builder/templatetags/narrate.py`.

- **The pages own the reproductions' runs**: the render and the check run them first, whole files,
  and the served pages at each save. A debug run writes no story.

Still candidates:

- A home for what the baseline holds and a piece does not: the verdict, the clusters by failure
  mechanism, the link to the diagnostic.
- The debug run stopping at the evidence by itself: today it stops at the reader's breakpoints.
- The order of several reproductions of one piece: today the order of their file.

## Decided so far

- A chain that crosses a process is not traced. It is joined at the piece: one evidence test per
  process, the seam's value watched on both sides.
- A browser reproduction runs on the server of the test process (`live_server`), as the journeys
  do, so that its story holds the server's calls.
- No header, middleware or spool file to trace the external development server.
- The JavaScript stack is built after the bug primitives are settled on Python and the template
  site, so that they are designed once.

## Findings

One section per ported bug: what the generated page says better than the baseline, what it cannot
say, and what was changed in the harness for it.

### Task 9 — ported with the harness as it is (2026-11-23)

Two pieces, `#dict-entry-own-template` and `#fragment-views-show-modal`: one `@planned` comment
in the dict template, a `planned` call in each of the thirteen fragment views, two reproductions.
The check passes and the page renders beside the old `plan.html` and `tasks.md`.

What the port did that the baseline did not:

- **The reproduction was split in two, one a piece.** A title carries one piece, and one strict
  expected failure across two pieces cannot be flipped by the first piece's commit. Each half fails
  for its own reason. The baseline says the same in prose, as its "discrimination" paragraph.
- **It raised a question the baseline passed over.** The decorator catches every exception, so
  the help drawer's and the row editor's own 404 would become the modal, and three tests expect a
  404. The page lists, under each site, the tests that reach it; the 404 test is among them.
- **It counts what reaches each view.** Four of the thirteen are reached by no test outside the
  browser tier: the two calculus-graph views, the recurrent chart and the EcoLogits explanation.
- **Its places cannot go stale.** The baseline cites `views.py:573`; the view is at 591.

What the generated page cannot say:

1. **No value anywhere.** The baseline's chain has five links with values. Three are no place the
   fix changes (`class_as_snake_str`, the chart preparer's first line, the URL the hourly partial
   renders), and `planned` is for a place that changes: evidence has no call.
2. **A `planned` site's watch is recorded and not drawn.** The one watch written, on the hourly
   chart view, is in the story (`attr_name`, `id_of_key_in_dict`) and nowhere on the plan page.
3. **The root cause is a template line.** It is a comment: no hit, no value. Django's own comment
   is not read either: the site is written as an HTML comment inside a Django one, since a bare
   HTML comment would be sent to the browser. (Quoting that form here stopped the check: the
   scanner read this page's example as a site.)
4. **A reproduction reads as any written test.** "unit · written": nothing says it fails on
   purpose, its state is recorded as `skipped`, its failure is not shown, and the piece has no
   debug button.
5. **A failing test's story stops at its first failed assertion.** The second reproduction
   crosses one of the five views it names, and the first crosses none. A reproduction whose story
   is the evidence has to observe everything and assert once, at its end.
6. **Some wrong values are the response's.** For the decorator piece the fault is a 500 with no
   `HX-Reswap`: it exists after the view returned, in the test alone. Its expected value is the
   assertion's, so the failure's excerpt is where it shows.
7. **One clause thirteen times.** A ripple with no single cause has no place to be stated once.
8. **No home** for the verdict, the cluster by failure mechanism, the dated decisions, the
   acceptance on the shipped examples, the library lines that show the value is empty on purpose,
   and the link to the diagnostic.

### Task 9 — on the four harness changes (2026-11-23)

Gaps 1 to 6 are closed by the primitives above. The two reproductions were rewritten to observe
then assert once, the template's comment became a `planned` tag with an evidence tag in the branch
that draws an empty entry as a series, and the chart preparer holds one evidence call.

What the second port showed:

- **What a place should see can depend on the crossing.** The template's branch is crossed 22 times
  and wrong 3 times, and the right template is the entry's own class: `expect` is computed at each
  crossing. The page shows the three that differ and folds the nineteen that do not.
- **"Should be" is read as a claim about the watched value.** The first version watched the entry's
  class and expected the one class the branch draws well, so the page said an empty entry "should
  be" an hourly series: true of the branch, false of the entry, and the reviewer read it as the
  second. The evidence now watches the template used. This is what made `expect` a lambda.
- **A value that is right can still be evidence.** The preparer receives an empty value, which the
  library means: the call has no `expect`, and reads as a link of the chain.
- **A failure's message is worth designing.** Asserting one dict of named observations gives a
  message a reviewer reads without the test: "a stale delete confirmation: a raw 500".
- **Evidence is a piece's own.** The first reproduction also crosses the chart view and the
  preparer, which are the second piece's: they are not drawn under the first.

What reading the page showed (the reviewer's, 2026-11-23):

- **The chain said things twice.** The piece's own lists repeated the places and the reproduction
  the chain had just drawn. They now hold what the chain does not: the places no reproduction
  crosses, the tests that are no reproduction.
- **The page showed whichever run came last.** A debug run of one test left the file's other
  reproduction as "no run", and its failure in the long form a verbose run words. Hence the two
  rules above.

Left open by Task 9:

- Gap 7, one clause thirteen times, and gap 8, what has no home.
- Reproductions a browser runs: left out of the tools' own run for now, to settle at Task 2.
- The 404 question on the second piece, which is the reviewer's.
- The tag library is written here and held by a test of this project; `e-footprint` takes the
  shared files at its next sync and needs none.
