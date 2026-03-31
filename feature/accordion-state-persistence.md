# Accordion State Persistence on Structural Card Updates

## Context

When a modeling object's structure changes (child added, child removed, or a non-name attribute edited), the presenter re-renders the full parent card HTML and swaps it via `hx-swap-oob='outerHTML:#{web_id}'`. The new HTML arrives with accordions in their server-rendered default state (closed when children exist, open when empty), resetting whatever the user had manually opened.

This plan preserves accordion open/close state across these structural OOB swaps using the `htmx:beforeSwap` event to modify the incoming HTML **before** it is inserted into the DOM, eliminating any risk of flash or Bootstrap animation artifacts.

Name-only renames are already handled separately (fine-grained `innerHTML:#name-{web_id}` swap, no card re-render) and are unaffected by this feature.

## Mechanism

`htmx:beforeSwap` fires with `evt.detail.serverResponse` (the raw HTML string) before HTMX builds the DOM fragment and performs any swaps. By modifying this string in-place, the new HTML lands in the DOM already in the correct open/close state — no second JS pass, no visual glitch, no Bootstrap collapse animation triggered.

```
htmx:beforeSwap fires
  ↓
Snapshot: collect all #flush-* IDs with .show class in current DOM
  ↓
Parse evt.detail.serverResponse via DOMParser
  ↓
For each .accordion-collapse in new HTML whose ID is in snapshot:
  - add .show to the collapse element
  - add .chevron-rotate to its #icon_accordion_{web_id} SVG
  - set aria-expanded="true" on its [data-bs-target="#flush-{web_id}"] button
  ↓
Serialize back → evt.detail.serverResponse = doc.body.innerHTML
  ↓
HTMX builds fragment from modified string → DOM lands correct
```

## Scope

This only applies when the response contains `outerHTML` card swaps. The handler short-circuits early if:
- the response has no `hx-swap-oob='outerHTML:` content (e.g., side panel loads, name-only responses, result panel updates), or
- there are no currently-open accordions.

## Files changed

Only one file: `theme/static/scripts/model_builder_main.js`.

## Implementation

### Step 1 — Add the `htmx:beforeSwap` handler in `model_builder_main.js`

Add the following function and event listener. Place it near the bottom of the file, after the existing event listeners.

```javascript
function restoreAccordionStateInFragment(serverResponse) {
    // Snapshot all currently-known accordion states (open = true, closed = false)
    const accordionStates = new Map();
    document.querySelectorAll('.accordion-collapse').forEach(el => {
        accordionStates.set(el.id, el.classList.contains('show'));
    });
    if (accordionStates.size === 0) return serverResponse;

    const doc = new DOMParser().parseFromString(serverResponse, 'text/html');
    let modified = false;

    doc.querySelectorAll('.accordion-collapse').forEach(collapseEl => {
        const wasOpen = accordionStates.get(collapseEl.id);
        if (wasOpen === undefined) return; // new element — keep server default

        const webId = collapseEl.id.replace(/^flush-/, '');
        const icon = doc.getElementById(`icon_accordion_${webId}`);
        const toggleBtn = doc.querySelector(`[data-bs-target="#flush-${webId}"]`);
        const isOpenInFragment = collapseEl.classList.contains('show');

        if (wasOpen && !isOpenInFragment) {
            collapseEl.classList.add('show');
            if (icon) icon.classList.add('chevron-rotate');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
            modified = true;
        } else if (!wasOpen && isOpenInFragment) {
            collapseEl.classList.remove('show');
            if (icon) icon.classList.remove('chevron-rotate');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
            modified = true;
        }
    });

    return modified ? doc.body.innerHTML : serverResponse;
}

document.body.addEventListener('htmx:beforeSwap', function (evt) {
    const response = evt.detail.serverResponse;
    // Only process structural card swaps (outerHTML OOB), not side panel or name-only responses
    if (!response || !response.includes("hx-swap-oob='outerHTML:")) return;

    evt.detail.serverResponse = restoreAccordionStateInFragment(response);
});
```

**Notes:**
- `new DOMParser().parseFromString(...)` is synchronous and cheap — it does not execute scripts or load resources.
- Writing to `evt.detail.serverResponse` is supported by HTMX: after `htmx:beforeSwap` fires, HTMX reads `serverResponse` to build the swap fragment.
- `doc.body.innerHTML` serializes only the `<body>` content, which is correct — HTMX OOB response bodies are bare HTML with no `<html>`/`<head>`.
- The `accordion-all` class (present on some collapse elements, e.g., `resource_need_with_accordion_card.html`) does not interfere — Bootstrap's collapse behavior is driven by the `collapse`/`show` classes, which we are setting directly.

### Step 2 — Verify no interaction with `data-bs-parent`

Some accordions use `data-bs-parent="#{{ object.web_id }}"` (see `resource_need_with_accordion_card.html:39`) to enforce mutual exclusion (only one child open at a time). Since the state we restore was already valid (it came from user interaction and respected this constraint), restoring it should not create an illegal state. No action needed, but worth verifying manually when testing.

## Testing

### Manual
1. Open an accordion (e.g., expand a journey step to reveal its jobs).
2. Edit a non-name attribute of the journey step (e.g., change its connection type).
3. Verify the accordion stays open and the chevron remains rotated.
4. Repeat with deeply nested accordions (e.g., expand a resource_need inside a journey_step, then edit the journey_step).
5. Add a new child to an open parent — verify parent stays open and new child is visible.
6. Delete a child from an open parent — verify parent stays open.

### Edge cases
- Accordion that was **closed** before the swap → stays closed (server default, nothing to restore).
- Multiple mirrored cards of the same object in different accordions → each `flush-{web_id}` ID is unique, all are restored independently.
- Response with no OOB card swaps (e.g., side panel open, toast-only response) → handler early-exits, no DOMParser call.
- Empty response body → `!response` check prevents any processing.

## What is NOT changed

- `htmx_presenter.py` — no change. The `_generate_mirrored_cards_html` full-card swap path remains unchanged.
- `EditObjectOutput`, `EditService`, `EditResult` — no change. The `name_only_change` logic added previously is orthogonal.
- Bootstrap collapse JS — not re-initialized. Bootstrap uses event delegation so newly inserted `data-bs-toggle="collapse"` elements work automatically.
- `addAccordionListener` / `resetLeaderLines` — still triggered via `HX-Trigger` after settle, as today.
