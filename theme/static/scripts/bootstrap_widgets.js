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
                .forEach(el => bootstrap.Tooltip.getOrCreateInstance(
                    el, { container: "body", trigger: "hover" }));
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

    document.addEventListener("DOMContentLoaded", () => initBootstrapWidgets(document));
    document.body.addEventListener("htmx:afterSettle", (event) => {
        initBootstrapWidgets(event.detail && event.detail.elt ? event.detail.elt : document);
    });
    document.body.addEventListener("htmx:beforeSwap", (event) => {
        const target = event.detail && event.detail.target;
        if (target) disposeShownWidgets(target);
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { initBootstrapWidgets, disposeShownWidgets };
    }
})();
