# Plan — bug-fixes-2026-10, the bugs ported to pieces

The bugs of runs B and C, ported one at a time from `plan.html` and `tasks.md` as the experiment of `specs/features/comprehension-harness-bug-fixes/experiment.md` reaches them. Task 9 gives the first two pieces, Task 10 the third.

## #dict-entry-own-template

Each entry of a calculated dict is drawn by the template of its own class: an entry the library leaves empty reads "no value", keeps its formula, offers no chart.

Today the dict template sends every entry that is not a quantity to the hourly chart, the empty ones included. The top-level section already includes by class. Refused: charting an empty value as zeros, which invents the date and the unit the library leaves out; a branch for the empty class, a list kept by hand.

## #fragment-views-show-modal

A fragment view that fails shows the exception modal, a not-found at its own 404: the four calculated-attribute read views, the delete confirmation, and the other undecorated fragment views.

A raw 500 is swapped nowhere: a stale pane and no error (constitution §1.4). A view's own not-found is as silent, on a stale Sources row: it shows the modal and keeps its 404, a missing thing being no server error. A full page or a download stays as it is. The chart preparers gain no empty-value branch.

## #explanation-ids-per-item

Each calculated attribute's ids, and what points at them, are built from the item's web id: its collapse, the three references of its formula button, its input and its label.

Today they are built from the attribute name, which several objects of one panel share: HTMX swaps into the first match, Bootstrap toggles every match. The web id already names the dict toggles. Refused: a relative target, which leaves Bootstrap's; a prefix passed by the section, which is not the item's owner; the route id, the URL's contract.
