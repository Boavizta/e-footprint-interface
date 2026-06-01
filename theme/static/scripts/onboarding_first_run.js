/* First-run onboarding state — a per-browser localStorage flag.

   On the user's first-ever landing on a loaded builder canvas (after a template
   loads, after "Start from scratch", or when the model already had content) this
   records `efootprint_onboarding_seen` and emits an `onboarding:first-run` event.
   It defers while the template picker still overlays the canvas, so the guided tour
   (Step 6 Task 3) that listens for that event auto-runs on the loaded canvas, not on
   the bare picker. The picker itself is server-driven and does not depend on this flag.
   IIFE + custom-event, nothing on `window`. See conventions.md → JavaScript. */
(function () {
    const SEEN_KEY = "efootprint_onboarding_seen";

    function onboardingSeen() {
        try {
            return localStorage.getItem(SEEN_KEY) === "true";
        } catch (e) {
            return true;  // storage blocked → treat as seen so we never nag.
        }
    }

    function markOnboardingSeen() {
        try {
            localStorage.setItem(SEEN_KEY, "true");
        } catch (e) { /* storage blocked — nothing to persist. */ }
    }

    function handleBuilderEntry() {
        if (!document.getElementById("model-builder-page")) return;
        if (onboardingSeen()) return;
        // While the template picker overlays the canvas, the user hasn't chosen a starting
        // point yet. The guided tour orients them on a *loaded* canvas (or the empty "Start
        // from scratch" baseline), so defer the once-ever first-run signal until the picker
        // is gone — i.e. a template was loaded, scratch was chosen, or the model had content.
        if (document.getElementById("template-picker")) return;
        document.body.dispatchEvent(new CustomEvent("onboarding:first-run"));
        markOnboardingSeen();
    }

    document.addEventListener("DOMContentLoaded", handleBuilderEntry);

    /* Entering the builder from the home page is an HTMX swap into #main-content-block. */
    document.body.addEventListener("htmx:afterSettle", function (event) {
        const target = event.detail && event.detail.target;
        if (!target) return;
        if (target.id === "model-builder-page" || target.id === "main-content-block"
            || (target.querySelector && target.querySelector("#model-builder-page"))) {
            handleBuilderEntry();
        }
    });

    /* The picker is a welcome overlay over the canvas; opening a side panel or the help
       drawer (e.g. Import a model from the toolbar) is the user acting, so the picker steps
       aside rather than covering — and blocking — that panel. */
    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.detail && event.detail.target;
        if (!target) return;
        if (target.id === "sidePanel" || target.id === "helpDrawer") {
            const picker = document.getElementById("template-picker");
            if (picker) picker.remove();
        }
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { SEEN_KEY, onboardingSeen, markOnboardingSeen, handleBuilderEntry };
    }
})();
