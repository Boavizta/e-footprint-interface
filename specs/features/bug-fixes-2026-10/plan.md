# Plan — bug-fixes-2026-10, the bugs ported to pieces

The bugs of runs B and C, ported one at a time from `plan.html` and `tasks.md` as the experiment of `specs/features/comprehension-harness-bug-fixes/experiment.md` reaches them. Task 9 is the first: its two pieces follow.

## #dict-entry-own-template

Each entry of a calculated dict is drawn by the template of its own class: an entry the library leaves empty reads "no value", keeps its formula, offers no chart.

Today the dict template sends every entry that is not a quantity to the hourly chart, the empty ones included. The top-level section already includes by class. Refused: charting an empty value as zeros, which invents the date and the unit the library leaves out; a branch for the empty class, a list kept by hand.

## #fragment-views-show-modal

A fragment view that fails shows the exception modal: the four calculated-attribute read views, the delete confirmation, and the other fragment views that carry no decorator.

A raw 500 is swapped nowhere: the user sees a stale pane and no error (constitution §1.4). Only a stale id reaches it today, in the read views and the delete confirmation; the rest is hardening. A full page or a download stays as it is. The chart preparers gain no branch for an empty value.

To confirm: **Do the help drawer and the source-table row editor keep their own 404?** The decorator catches every exception, so an unknown class or row would show the modal, and the three tests that expect a 404 would change. The alternative leaves both undecorated.
