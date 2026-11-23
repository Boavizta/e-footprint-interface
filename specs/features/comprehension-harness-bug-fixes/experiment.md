# Bug batches on the comprehension harness — experiment

The comprehension harness plans a feature as pieces written into the code. A bug batch used the
earlier form (`tasks.md`, diagnostics, a hand-written `plan.html`). This experiment ports
`bug-fixes-2026-10` runs B and C to the harness, one bug at a time, to find what the harness needs
to plan and fix bugs well. Since 2026-11-23 the bug skills write pieces too, on the forms settled
so far: what the remaining bugs show corrects them.

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
- `tasks.md` is the baseline too, and is not run. A task delivered through the plan is marked
  complete there, and leaves the order of its run.

## The loop

A bug is ported before it is fixed, and bugs are approved and fixed in batches: the approval is a
plan's, not a bug's, so a bug ported after an approval is an edit of an approved plan.

1. Port the bug with the harness as it is, by `bug-fixes-plan`.
2. Compare the generated page with the bug's section of the baseline, and write the gaps below.
3. Add the smallest primitive the comparison asks for, and render again.
4. Once every bug of the batch is ported, its lots are written and the reviewer approves the plan
   with them; the batch is then fixed through the new form, and what the implement stage showed
   is written below.

## Next

The small batch is fixed, reviewed and approved again (2026-11-23): Tasks 9 and 10, three pieces,
one lot. What its run showed is under Findings, and the skills and the harness were changed for
it the same day.

Now **the rest of run B, ported in full before any of it is fixed**, as a batch is run: Tasks 7,
16, 12 and 2, a session a bug, in that order. They join the plan that holds the two fixed bugs:
each is an edit of an approved plan, and the four are approved together, with the lots they add.
The plan is not closed between rounds: it is archived whole, at the end (Decided so far).

Three things are met for the first time, and a misfit of any is reported, not worked around:

- `bug-fixes-plan` in its new form, which nothing has run. `bug-fixes` waits for a batch not
  yet diagnosed: these four are;
- an edit that takes back a built place, the `unbuilt` claim;
- an approval made with the tools that hold a reproduction as written and freeze its chain. The
  first fix after it is the first time a real page shows a bug's chain under a built piece.

To open the first session:

> Port Task 7 of `bug-fixes-2026-10` into its plan, with `bug-fixes-plan`. The plan
> (`specs/features/bug-fixes-2026-10/plan.md`) holds two bugs, fixed and approved: Task 7 joins
> it as a `## Bug:` section with its pieces, and its lot joins `## Delivery`. Fix nothing.
>
> This is a session of the experiment
> `specs/features/comprehension-harness-bug-fixes/experiment.md`: read it first. Its loop applies:
> port the bug with the harness as it is, compare the generated page with the bug's section of
> `plan.html`, write the gaps under Findings as Tasks 9 and 10 have theirs, and add a primitive
> only for a gap you name. `tasks.md`, `plan.html` and `diagnostics/` are the baseline the bug is
> ported from: the first two are the earlier form, not edited and not run. The table "Order" says
> what Task 7 probes.
>
> The bug is diagnosed already: `bug-fixes` is not run. Where the diagnosis left a reproduction
> under an expected-failure marker, it is declared in the stack's form and made to observe, then
> assert once.
>
> In the same session, take back the three places of `#fragment-views-show-modal` the plan still
> reads as built and the review undid, the two calculus-graph views and the Sankey card deletion:
> one `Changed:`, three `unbuilt` claims (`specs/workflow-formats.md` § "`plan.md`").
>
> `bug-fixes-plan` was rewritten for pieces and has never been run. End your report with where it,
> `spec-plan`, the check, the map or the pages did not fit, and work around none of them. Stop
> before the approval: it is the reviewer's, and waits for Tasks 16, 12 and 2.

The sessions of Tasks 16, 12 and 2 open the same way, the task and what it probes changed, and
without the paragraph on the three places. Each puts its pieces in a lot, since the check holds
every piece to one. The last one reads the four together, groups in one lot the bugs that share a
surface, and hands the plan to the reviewer.

**Then the fix**, one lot a run of `feature-implement`, and back here with what each run listed.

## Order

| Bug | Why here | State |
|---|---|---|
| Task 9 — empty calculated dict entries | In-process reproduction, the baseline's richest chain of values, four Python links and one template link | Fixed (2026-11-23), in the lot `calculated-attribute-panel` |
| Task 10 — explanation ids per item | Template-only: template sites as the only evidence. Shares Task 9's test file and its cluster of the baseline | Fixed (2026-11-23), in the same lot |
| Task 7 — "each hour" after the unit | Template-only: third use of the template site. First run of `bug-fixes-plan` in its new form, and of an edit that takes a built place back | Next to port |
| Task 16 — group-member confirmation | Pure Python, no reproduction yet: one written from scratch with the new primitives | |
| Task 12 — system prefix first in card ids | Cause in Python, symptom in a jest test: two evidence tests joined at the piece | |
| Task 2 — membership-section region | Symptom in a browser: an in-process cause test, and a browser reproduction, whose run is to settle then | |
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
- **A bug**, built on reading Tasks 9 and 10 together: a `## Bug: <what is wrong>` section of
  `plan.md`, and the pieces whose sections stand under it. The page is read a bug at a time.
- **`distinct`**, built on Task 10: on a `planned` or an evidence call, the keys of the watch each
  crossing should see a value of its own for. For a bug no crossing shows alone: one value at
  several. Read from the source; no run and no story holds it.
- **The pages own the reproductions' runs**: the render and the check run them first, whole files,
  and the served pages at each save. A debug run writes no story.

Built on the fix of Tasks 9 and 10, for what the implement stage showed:

- **`unbuilt`**: a claim of a `Changed:` that names a place the plan reads as built and the code
  does not hold. The piece loses the line, the page draws it "taken back" under its edit, and the
  next approval drops it. A kind of its own: a `code` claim never drops a built place.
- **The approval holds a reproduction as written.** The title reader gives a declared test's body
  as a hash, its declaration left out. One edited since the approval, fixed or not, is a line of
  its piece's difference.
- **The chain outlives the fix.** The approval freezes what each reproduction saw and how it
  failed, and the pages draw it under the built piece, beside the test that now passes. A bug
  reads "fixed" once its pieces are built; the reproductions have their own block of a lot's
  tests; evidence that went is no place built.
- **The brief of a built piece** prints each place that became code with its clause as approved,
  and each test written: what a reviewer sets the code against.
- **A place is built when its function gained a line.** The lot check read a place by its file: a
  place skipped beside built ones, or undone by a later commit, read as built. It now reads the
  place's function, from the approval's commit to the code as it stands, what stands directly on
  it counted with it. So the check asks for the `unbuilt` paragraph where nothing was written.

Still candidates:

- A home for what the baseline holds and neither a bug nor a piece does: the verdict, the clusters
  by failure mechanism.
- The debug run stopping at the evidence by itself: today it stops at the reader's breakpoints.
- The order of several reproductions of one piece: today the order of their file.
- One clause for a ripple: seen at Task 9 and again at Task 10. The lot check wants a place in each
  file the piece changes, so a ripple cannot be stated at its cause alone. The fix of Task 9 gave
  it a cost: one clause over thirteen views hid the three it did not fit.
- A place built wrongly: code stands there and does not do what the clause says. No tool tells,
  and the `unbuilt` paragraph is then written only when a reviewer sees it. Nor does one tell a
  place built by taking lines off from one that was skipped: its `Changed:` says which.
- A change in a file the plan names, on a line no place names: neither the lot check nor the
  brief shows it.
- A feature name used again after an archive: a plan reads every commit that names one of its
  feature's pieces, and fails on one whose piece it no longer holds.

## Decided so far

- A chain that crosses a process is not traced. It is joined at the piece: one evidence test per
  process, the seam's value watched on both sides.
- A browser reproduction runs on the server of the test process (`live_server`), as the journeys
  do, so that its story holds the server's calls.
- No header, middleware or spool file to trace the external development server.
- The JavaScript stack is built after the bug primitives are settled on Python and the template
  site, so that they are designed once.
- A plan of bugs has no tasks stage: the plan stage writes its lots, and one approval holds both.
- A bug that is a value several crossings share is said with `distinct`, not with an `expect` that
  every crossing fails: what is red on the page is the bug, not the reach of the fix.
- The bug skills write pieces (2026-11-23): `bug-fixes` leaves a diagnostic a bug and its
  reproductions in the stack's form, `bug-fixes-plan` the plan as `spec-plan` does with what a
  batch adds, and `feature-implement`, `task-implement` and `task-review` hold no earlier form.
  No batch is left to run it: the rest of this one is ported. The tools of a `plan.html` stay for
  the ones already written.
- A plan leaves nothing to the implementer: a place is written or it is not. The implementer
  reads each place against what the piece's reason leaves as it is, and reports the one it rules
  out.
- What a diagnostic lists beyond its reproduction, as the sweep of the shipped examples, is a
  test, a check for the user named in its lot's reason, or dropped in a clause of the piece's
  reason: the plan says which. Written into the skills; no bug has met it yet.
- A cause that is only plausible is planned as the piece that produces the reading, the fix a
  piece of a later lot that waits on it. Written into the skills; no bug has met it yet.
- The plan is extended between rounds and archived whole at the end (the reviewer's,
  2026-11-23). Closing it after a round would take the tags off its tests and leave its commits
  naming pieces the next plan does not hold, and its folder holds the baseline.
- No global review of a round: rounds are the experiment's, and a batch is normally approved
  once. The leads of each lot's review wait in the gates file for the review of the whole.

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
- Settled by the reviewer: a view's own not-found shows the modal and keeps its 404. The decorator
  gained a site for it, and the reproduction two observations.
- The tag library is written here and held by a test of this project; `e-footprint` takes the
  shared files at its next sync and needs none.

### Task 10 — ported with the harness as it is (2026-11-23)

One piece, `#explanation-ids-per-item`: seven `planned` tags in five templates, a comment on each
of the three browser tests whose selector changes, one reproduction. No evidence tag: every line
the bug shows at is a line the fix changes.

What the port did that the baseline did not:

- **The reproduction says who collides.** The baseline's stops at its first assertion, on two ids
  written three times. Rewritten to observe then assert once, it also names the formula buttons
  that open one row: the CPU's, the RAM's and the storage's.
- **It had to decide what the baseline left optional.** The section button's `aria-controls` is
  "optional" there. A place is written or it is not, and the lot check refuses a file no place
  names: it is written, as a place the reviewer can refuse.
- **It counts what reaches each place.** The EcoLogits override is reached by no test outside the
  browser tier: the two browser tests that carry the piece's comment are all that hold it.
- **Its places cannot go stale**, again: the baseline breaks at `:103` of a test that has moved.

What the generated page cannot say:

1. **The bug is no crossing's own.** The collapse's line is crossed sixteen times and is right at
   each for its item: what is wrong is that three crossings wrote the same id. With `expect` set to
   the web id, each of the two places drew sixteen crossings in red, the three that collide among
   them. Without it, six of the sixteen were listed and nothing was red.
2. **One clause three times**, gap 7 again: a template that overrides a block repeats its parent's
   line, and each file needs its place.
3. **The second usage pattern shows nothing yet.** The dict entries reach these templates once
   Task 9's piece is built: the chain of one piece's reproduction depends on another piece's
   state. The baseline says it in prose, as its "discrimination".
4. **What the browser does with a shared id** (the first match swapped, every match toggled, the
   fetch made once) was observed for the diagnostic and no test holds it. It is a clause of the
   piece's reason.
5. **No home**, gap 8 again: the sweep of the shipped examples as acceptance, the link to the
   diagnostic.
6. **The values hold generated ids**, so the page differs at each render. Nothing approved moves:
   the approval holds what a place says, not what a run saw.

### Task 10 — on the one harness change (2026-11-23)

Gap 1 is closed by `distinct`. The collapse and the button each name the key their crossings
should see their own value for, and the page reads as the baseline's first three links: the
attribute name three times, in red, "should be one for each crossing", then the three owners,
each with the web id it already has; the thirteen other crossings are counted, and folded.

What it showed:

- **The fix's value is context, not an expectation.** The web id is watched beside the shared key
  and expects nothing: it is right today, and unused. This is the baseline's third link.
- **The declaration is the source's.** Which crossings share a value is told from the watches a
  story already holds: the collector, the calls at run time and the story are unchanged.
- **The check holds the diagnosis**, as it does for `expect`: a place that names distinct keys and
  whose reproduction saw a value of its own at each crossing fails.
- **The message and the chain say the same thing twice**, from two sides: the test sees the panel,
  the tags see each item. Neither is dropped: the message is what the fix has to turn, the chain
  is where.

Left open by Task 10:

- Gap 2, with Task 9's gap 7: now a candidate above.
- Whether a plan may leave a place to the implementer.

### Tasks 9 and 10 — read as one plan (the reviewer's, 2026-11-23)

With a second bug the page stopped reading: three pieces in the order of their files, Task 10's
first and Task 9's two after it, with nothing saying which bug a piece fixes. A plan of pieces
had no notion of bug.

- **A bug is a section, and its pieces stand under it.** Membership is the file's order, not a
  list of names: a bug's text can then name another bug's piece in passing, as Task 10's does of
  Task 9's, and a piece is under one bug by construction.
- **It gives a home to what a user met.** The symptom was nowhere: a piece states the change, its
  chain the cause. The link to the diagnostic stands there too, opened from the page.
- **A bug's text is held to what is wrong.** Sixty words, and no cause: the baseline's "root
  cause" and "fix" are the pieces'.
- **It costs the approval nothing new.** A bug is approved as a decision across pieces is: its
  text, under its title.

Still with no home: the verdict, the clusters by failure mechanism, the acceptance on the
shipped examples.

### The delivery of a plan of bugs (the reviewer's, 2026-11-23)

A tasks session was planned between the approval and the fix, as a feature has. The reviewer asked
what it would do.

- **Nothing but one line.** That stage plans the unit tests, grounds the plan in the code and
  cuts it into lots. A bug's reproduction is its test, already written and failing; its diagnosis
  is its grounding, and the chain a run of it. The lots are left, and the bug sections already
  group the pieces.
- **The earlier form had none either.** A diagnosis gave the tasks, and the plan ordered the runs.
- **The tools still need the list.** The lot check, the brief and "this place is built" read
  `## Delivery`, and from an approval that holds it. So the plan stage writes it, and the plan is
  approved once, with it.
- **It settles the question left by the first port**: a reproduction is a unit test written at
  the plan stage because, for a bug, no later stage plans tests.
- **Left for a larger batch**: lots told from the bug sections alone. Two bugs do not say how
  several bugs of one run would be grouped.

### The small batch — fixed through `feature-implement` (2026-11-23)

One lot, `calculated-attribute-panel`, `easy`: three pieces in three commits, a docs commit and a
changelog commit, then three commits of review fixes. The reviewer read it at full depth, for
the shared exception wrapper, and returned eight findings. The suites were green at the end, and
the plan was approved again once two edits and one question were answered.

What held, of the two things the batch was run to test:

- **An evidence call went with nothing written in its place**, and the lot check said nothing.
- **Each reproduction became a written test under its title**, and its lot read as delivered.

What the review found that the forms had let through:

- **The plan contradicted itself.** Three of the thirteen views are no fragment: the two
  calculus-graph views are full pages, and the Sankey card deletion is called by a script. The
  piece's own reason says a full page stays as it is. The baseline had left it to the implementer
  ("check each"); the port froze every view as a place, and nothing sets a place against a reason.
- **The statement claimed more than its places.** "The other undecorated fragment views" read as
  all of them: seven more are undecorated. They are left to the backlog's HTMX-aware server error
  handler, which now names them.
- **A reproduction asserted less than its title**: "reads no value" was in the title alone. The
  review made it assert it, after the fix.
- **A line the fix left dangling**: the dict's label pointed at an input id the piece renamed. It
  was no place of the plan.

Where the skills, the check, the map and the pages did not fit:

1. The three skills spoke of bugs only in their sections for `tasks.md`: the forms of a piece
   that fixes a bug had to be written into each brief.
2. `task-review` asked for the story of the last commit and for deleted tests, which a bug's
   piece has not, and did not ask whether a reproduction's body moved with its declaration.
3. Nothing said what becomes of a template's load line once its last tag is gone.
4. A comment on a browser test, "the selector matches its prefix", was built too loosely first.
5. The gates are sorted from a lot's reason and its pieces: the baseline's acceptance on the
   shipped examples has no home in the plan, so it was not sorted and not run.
6. "When the last lot is reviewed" has no moment in a plan approved in rounds.
7. Nothing said where the changelog entry goes: it was a commit naming three pieces, which a
   review fix edited again.
8. **A built place undone by a review fix is invisible.** The check reads a place as built once
   its call is gone from the source, whatever was written there: a `Changed:` that claimed the
   three views was refused, and stood on the reason's line alone. The delivery page and the next
   approval went on holding them as built.
9. The approval holds a test by its title: the reproduction the review strengthened passed
   unseen.
10. A change on a line no place names, in a file the plan names, passes unseen.
11. The brief of a built lot printed counts: the reviewer read the approved clauses in
    `plan.approved.json`. It counted the evidence that went as places built.
12. A place of a bug's piece that no test reaches was sent to "the narrative tests it should sit
    in".
13. The map's `help` crashed, and a stale story file was counted and not named.
14. **Once a piece is built, the page tells nothing of the bug**: no evidence, no value, no
    failure, and the reproduction listed "written" under "Tests to write". A bug's section has
    no state.

### The small batch — what was changed for it (2026-11-23)

A commit a change, each held by the tools' tests where it is the tools':

| What | For | Commit |
|---|---|---|
| The three skills say how a piece that fixes a bug is built, reviewed and supervised | 1, 2, 3 | `24d2b8ec` |
| The implementer reads each place against what the piece's reason leaves as it is | the plan that contradicted itself | `65b50d23` |
| Each lot adds its part of the changelog entry in its last commit | 7 | `42ce3729` |
| A `Changed:` takes back a place that reads as built, by an `unbuilt` claim | 8 | `5ea53588` |
| The approval holds a reproduction as written | 9 | `2288b18e` |
| The approval freezes each reproduction's chain, and the pages draw it under the built piece | 14, and 11's count | `272a8c4f` |
| The brief prints a built piece as the approval holds it; `help`; the stale story's name | 11, 12, 13 | `79a422fc` |
| `bug-fixes` and `bug-fixes-plan` write pieces, and the earlier form leaves the skills | 1, at its root | `dd1964bf` |

What building them showed:

- **Taking back needs a claim of its own.** The first version let a `code` claim name a built
  place when it named no line of the difference. An old claim of another plan, on a file its
  piece had built three places in, took the three back without a word. `unbuilt` cannot do that.
- **The frozen chain has been seen on no real approval.** This plan was approved before the
  tools froze anything, and an approval file is the approval command's alone: the drawing was
  checked on the plan read in memory. The next approval is the first to freeze, and the fix after
  it the first page to show.
- **The body is held for a reproduction, not for every written test**: a planned change of a
  test like another is announced by a comment on it, and is no edit to explain.
- **A place that is code has no line.** The frozen chain and the brief name it by its file and
  its function: the approval holds no line number, on purpose.

Left open by the small batch:

- 4, 5, 6 and 10 of the list. 5 is decided in the skills and met by no bug yet; 6 is the
  experiment's own, and asks nothing of a batch approved once.
- The three views are still built in this plan's approval: the session that ports Task 7 takes
  them back.
- Whether a place can be set against its piece's reason by a tool. The implementer now does it.
