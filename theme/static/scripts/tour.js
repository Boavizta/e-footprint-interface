/* Guided tour — a thin, non-blocking wrapper around driver.js (vendored as
   external_librairies/driver.iife.js, which exposes window.driver.js.driver).

   The step copy and targets are server-provided: views.py resolves tour_steps.py
   (placeholders already expanded to HTML) and renders them into a
   <script type="application/json" id="tour-steps-data"> via tour_steps.html, so the
   words never live in JS. This module only sequences and positions them.

   - Auto-runs once ever, on the `onboarding:first-run` event onboarding_first_run.js
     emits on the user's first-ever builder entry.
   - Replayable any time via the toolbar Help menu's `data-action="replay-tour"`.
   - The help step opens the help drawer via help_drawer_utils.js's shared open path and
     keeps it clickable while the tour stays open — the tour is non-blocking.

   IIFE + data-action dispatch, nothing on window. See conventions.md → JavaScript. */
(function () {
    function getDriverFactory() {
        // The vendored IIFE build exposes the factory at window.driver.js.driver.
        return window.driver && window.driver.js && window.driver.js.driver;
    }

    function readTourSteps() {
        const dataEl = document.getElementById("tour-steps-data");
        if (!dataEl) return [];
        try {
            return JSON.parse(dataEl.textContent) || [];
        } catch (e) {
            return [];
        }
    }

    /* Drive the help drawer from the tour by firing help_drawer_utils.js's established
       `data-action` dispatch (it owns the endpoint, swap, open/close + canvas resize).
       Keeping the drawer (and the toolbar) clickable above driver's modal overlay is
       handled in CSS — see tour.css. */
    function fireHelpDrawerAction(action, className) {
        const trigger = document.createElement("button");
        trigger.setAttribute("data-action", action);
        if (className) trigger.setAttribute("data-help-class", className);
        trigger.style.display = "none";
        document.body.appendChild(trigger);
        trigger.click();  // bubbles to help_drawer_utils.js's delegated listener
        trigger.remove();
    }

    function openHelpDrawerForTour(className) {
        if (className) fireHelpDrawerAction("open-help-drawer", className);
    }

    function closeHelpDrawerForTour() {
        fireHelpDrawerAction("close-help-drawer");
    }

    /* Pick the element to highlight. A step may carry a `mobile_target` fallback for when its
       primary target lives in a surface that collapses on small screens (e.g. the toolbar's
       Help menu, hidden inside the burger below the lg breakpoint). An element with no layout
       box (offsetParent === null) can't be anchored, so driver.js would float the popover to
       the top — fall back to the mobile target then. Resolved lazily (a function), so a viewport
       resize between building the steps and reaching the step still picks the right anchor. */
    function resolveElement(step) {
        const primary = document.querySelector(step.target);
        if (primary && primary.offsetParent !== null) return primary;
        if (step.mobile_target) {
            const fallback = document.querySelector(step.mobile_target);
            if (fallback && fallback.offsetParent !== null) return fallback;
        }
        // Return the (possibly hidden or null) primary element — never the selector string,
        // since driver.js uses a function's return value as the element directly. A null lets
        // driver.js fall back to its centered dummy rather than mis-anchoring.
        return primary;
    }

    /* Map a server step to a driver.js step. */
    function toDriverStep(step) {
        const driverStep = {
            element: step.mobile_target ? (() => resolveElement(step)) : step.target,
            popover: { title: step.title, description: step.body },
        };
        if (step.open_help_class) {
            // Open the drawer as the step begins. It opens via an async htmx swap that
            // resizes the canvas and shifts the highlighted "?" button — the
            // htmx:afterSwap handler below refreshes the tour onto its new position.
            driverStep.onHighlightStarted = () => openHelpDrawerForTour(step.open_help_class);
        }
        if (step.close_help) {
            // Close the drawer opened by an earlier step before highlighting this one.
            driverStep.onHighlightStarted = () => closeHelpDrawerForTour();
        }
        return driverStep;
    }

    function buildDriverSteps(steps) {
        return steps.map(toDriverStep);
    }

    // Track the live driver so a replay never stacks a second tour over an active one.
    let activeTour = null;

    function runTour() {
        const driverFactory = getDriverFactory();
        if (!driverFactory) return;
        const driverSteps = buildDriverSteps(readTourSteps());
        if (driverSteps.length === 0) return;

        if (activeTour) activeTour.destroy();

        const tour = driverFactory({
            showProgress: true,
            allowClose: true,
            // Non-blocking: clicking the dimmed canvas dismisses the tour rather than trapping
            // the user. The toolbar and the help drawer stay reachable above the overlay (tour.css).
            overlayClickBehavior: "close",
            steps: driverSteps,
            onDestroyed: () => { activeTour = null; },
        });
        activeTour = tour;
        tour.drive();
        return tour;
    }

    /* ===== Auto-run once ever, then replay on demand ===== */

    document.body.addEventListener("onboarding:first-run", function () {
        runTour();
    });

    document.body.addEventListener("click", function (event) {
        const target = event.target.closest('[data-action="replay-tour"]');
        if (!target) return;
        event.preventDefault();
        runTour();
    });

    /* Re-opening the template picker (Help ▸ Open templates) ends the tour: the picker is
       a fresh "choose a starting point" surface that would otherwise sit under the tour's
       overlay, and the tour's targets no longer apply once the picker covers the canvas. */
    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.detail && event.detail.target;
        if (!activeTour || !target) return;
        if (target.id === "template-picker" || (target.querySelector && target.querySelector("#template-picker"))) {
            activeTour.destroy();
        } else if (target.id === "helpDrawer") {
            // The drawer just opened and resized the canvas, moving the highlighted "?"
            // button. driver's refresh() is rAF-deferred, so it recomputes the overlay and
            // popover after help_drawer_utils.js's sibling handler has settled the layout.
            activeTour.refresh();
        }
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            readTourSteps,
            buildDriverSteps,
            toDriverStep,
            resolveElement,
            runTour,
            openHelpDrawerForTour,
            closeHelpDrawerForTour,
        };
    }
})();
