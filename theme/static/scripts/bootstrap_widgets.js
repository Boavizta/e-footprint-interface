/* Central Bootstrap tooltip/popover initializer.

   Bootstrap 5 popovers and tooltips need explicit JS init — they don't auto-attach to
   `data-bs-toggle` elements. HTMX swaps in new DOM that needs the same treatment.

   This module exposes one entry point, `initBootstrapWidgets(root)`, wired to
   DOMContentLoaded and `htmx:afterSettle` so any swap-target subtree gets its widgets
   wired up.

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

    document.addEventListener("DOMContentLoaded", () => initBootstrapWidgets(document));
    document.body.addEventListener("htmx:afterSettle", (event) => {
        initBootstrapWidgets(event.detail && event.detail.elt ? event.detail.elt : document);
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { initBootstrapWidgets };
    }
})();
