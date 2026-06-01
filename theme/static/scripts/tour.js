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

    /* Open the help drawer for a class on the tour's help step. The endpoint + swap is
       owned by help_drawer_utils.js; we just trigger its established
       `data-action="open-help-drawer"` dispatch. Keeping the drawer (and the toolbar)
       clickable above driver's modal overlay is handled in CSS — see tour.css. */
    function openHelpDrawerForTour(className) {
        if (!className) return;
        const trigger = document.createElement("button");
        trigger.setAttribute("data-action", "open-help-drawer");
        trigger.setAttribute("data-help-class", className);
        trigger.style.display = "none";
        document.body.appendChild(trigger);
        trigger.click();  // bubbles to help_drawer_utils.js's delegated listener
        trigger.remove();
    }

    /* Map a server step to a driver.js step. */
    function toDriverStep(step) {
        const driverStep = {
            element: step.target,
            popover: { title: step.title, description: step.body },
        };
        if (step.open_help_class) {
            driverStep.onHighlighted = () => openHelpDrawerForTour(step.open_help_class);
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
        }
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            readTourSteps,
            buildDriverSteps,
            toDriverStep,
            runTour,
            openHelpDrawerForTour,
        };
    }
})();
