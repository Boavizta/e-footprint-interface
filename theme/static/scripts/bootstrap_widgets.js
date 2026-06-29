/* Central Bootstrap tooltip/popover initializer.

   Bootstrap 5 popovers and tooltips need explicit JS init — they don't auto-attach to
   `data-bs-toggle` elements. HTMX swaps in new DOM that needs the same treatment.

   This module exposes `initBootstrapWidgets(root)`, wired to DOMContentLoaded and
   `htmx:afterSettle` so any swap-target subtree gets its widgets wired up, and
   `disposeShownWidgets(root)`, wired to `htmx:beforeSwap` to clean up tips left orphaned
   when a swap removes their trigger (see below).

   `.truncated-text-tooltip` elements are skipped here: `model_builder_main.js` owns them
   because they need a truncation-guard listener and a zero-delay config; calling
   `getOrCreateInstance` again here would lock in the wrong config (the first init wins).

   See conventions.md → JavaScript (IIFE, central widget init). */
(function () {
    const POPOVER_SELECTOR = '[data-bs-toggle="popover"]';
    const TOOLTIP_SELECTOR = '[data-bs-toggle="tooltip"]:not(.truncated-text-tooltip)';

    function collectMatches(scope, selector) {
        const matches = Array.from(scope.querySelectorAll(selector));
        if (scope.nodeType === 1 && scope.matches && scope.matches(selector)) {
            matches.push(scope);
        }
        return matches;
    }

    function initBootstrapWidgets(root) {
        if (typeof bootstrap === "undefined") return;
        const scope = root || document;
        if (bootstrap.Popover) {
            collectMatches(scope, POPOVER_SELECTOR)
                .forEach(el => bootstrap.Popover.getOrCreateInstance(el));
        }
        if (bootstrap.Tooltip) {
            collectMatches(scope, TOOLTIP_SELECTOR)
                // animation: false keeps hide() synchronous. An animated hide defers its cleanup
                // (this._element.removeAttribute(...)) past the fade via executeAfterTransition; if an
                // HTMX swap disposes the instance in that window, the deferred callback throws on a
                // nulled _element. No fade ⇒ no deferred callback ⇒ no race (see disposeShownWidgets).
                // (hardenAgainstDisposedTipEvents pins _isAnimated() false globally as the real backstop
                // — this flag is the local, documented expression of the same intent.)
                .forEach(el => bootstrap.Tooltip.getOrCreateInstance(
                    el, { container: "body", trigger: "hover", animation: false }));
        }
    }

    // A shown tooltip/popover lives in a floating tip element Bootstrap appends to
    // <body> (default `container: false`), outside any HTMX swap target. When a swap
    // removes the trigger while its tip is shown — e.g. the toolbar's "Reset to default
    // model" button, which posts and replaces all of #main-content-block including
    // itself — the trigger's mouseleave never fires, so the orphaned tip lingers in
    // <body> forever. Before each swap, dispose the instances on the about-to-be-removed
    // triggers; dispose() removes the tip synchronously. Only currently-shown triggers
    // carry an aria-describedby pointing at a tooltip-/popover- tip, so this leaves
    // surviving widgets (outside the swap target) untouched.
    function disposeShownWidgets(root) {
        if (typeof bootstrap === "undefined") return;
        collectMatches(root || document, "[aria-describedby]").forEach(el => {
            const id = el.getAttribute("aria-describedby") || "";
            if (id.startsWith("tooltip")) bootstrap.Tooltip.getInstance(el)?.dispose();
            else if (id.startsWith("popover")) bootstrap.Popover.getInstance(el)?.dispose();
        });
    }

    // Make a disposed tooltip/popover instance inert to trailing interaction events.
    //
    // disposeShownWidgets() (above) disposes a shown tip on htmx:beforeSwap so it can't orphan in
    // <body>. But the same DOM mutation that removes the trigger generates a trailing hover/focus
    // event (mouseleave/focusout) that Bootstrap dispatches *after* the dispose, re-entering the
    // just-disposed instance. dispose() nulls every own property (BaseComponent zeroes them via
    // getOwnPropertyNames), so the re-entered handler hits `Object.values(this._activeTrigger)` →
    // "Cannot convert undefined or null to object" in _isWithActiveTrigger, or `this._element
    // .removeAttribute(...)` → "...reading 'removeAttribute'" in the hide path. Guard the interaction
    // entry points so a dead instance (no _element) no-ops instead of throwing. Popover inherits
    // Tooltip.prototype, so this one patch covers both. Installed once, idempotently.
    function hardenAgainstDisposedTipEvents() {
        if (typeof bootstrap === "undefined" || !bootstrap.Tooltip) return;
        const proto = bootstrap.Tooltip.prototype;
        if (proto._efDisposedGuardInstalled) return;
        proto._efDisposedGuardInstalled = true;
        ["_enter", "_leave", "show", "hide", "toggle", "_isWithActiveTrigger"].forEach(name => {
            const original = proto[name];
            if (typeof original !== "function") return;
            proto[name] = function (...args) {
                if (this._element == null || this._activeTrigger == null) {
                    // _isWithActiveTrigger must stay boolean; the rest are void.
                    return name === "_isWithActiveTrigger" ? false : undefined;
                }
                return original.apply(this, args);
            };
        });

        // Force every tooltip/popover to hide synchronously, killing the deferred-cleanup race at its
        // root. Bootstrap's hide() queues its cleanup (this._element.removeAttribute("aria-describedby"))
        // behind the fade via _queueCallback(…, this._isAnimated()); when an HTMX swap disposes the
        // instance during that fade, the trailing transitionend fires the queued closure on a nulled
        // _element → "Cannot read properties of null (reading 'removeAttribute')". The guard above can't
        // reach that closure (it isn't a prototype method). _isAnimated() returns true when config
        // animation is on OR the tip carries the `fade` class, so a per-init `animation: false` is not
        // enough — a hardcoded-`fade` template (or any init site that forgets the flag) still races.
        // Pinning it false makes _queueCallback run cleanup inline, while _element is still live. Every
        // tip in this app already opts out of animation, so this removes no intended fade.
        proto._isAnimated = function () { return false; };
    }

    hardenAgainstDisposedTipEvents();

    document.addEventListener("DOMContentLoaded", () => initBootstrapWidgets(document));
    document.body.addEventListener("htmx:afterSettle", (event) => {
        initBootstrapWidgets(event.detail && event.detail.elt ? event.detail.elt : document);
    });
    document.body.addEventListener("htmx:beforeSwap", (event) => {
        const target = event.detail && event.detail.target;
        if (target) disposeShownWidgets(target);
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { initBootstrapWidgets, disposeShownWidgets, hardenAgainstDisposedTipEvents };
    }
})();
