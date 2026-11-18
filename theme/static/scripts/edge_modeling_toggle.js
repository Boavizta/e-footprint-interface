/* Edge modeling toggle — drives `body.edge-modeling-on/off` from a localStorage flag and the
   server-rendered latch state. CSS keyed off that body class hides edge-paradigm add-buttons.
   A freshly opened AI bootstrap panel marks its scope fieldset; with Edge modeling on, the marker
   selects Web + edge once, so a later click on the radio is never overridden.
   See conventions.md → JavaScript (IIFE + data-action dispatch). */
(function () {
    const EDGE_MODELING_STORAGE_KEY = "efootprint.edgeModeling";
    const TOGGLE_ACTION = "edge-modeling-toggle";
    const AI_SCOPE_MARKER = "data-ai-scope-follows-edge-modeling";

    function readEdgeModelingPreference() {
        return localStorage.getItem(EDGE_MODELING_STORAGE_KEY) === "on" ? "on" : "off";
    }

    function writeEdgeModelingPreference(value) {
        localStorage.setItem(EDGE_MODELING_STORAGE_KEY, value === "on" ? "on" : "off");
    }

    function preselectAiScope(edgeModelingOn) {
        const fieldset = document.querySelector(`[${AI_SCOPE_MARKER}]`);
        if (!fieldset) {
            return;
        }
        fieldset.removeAttribute(AI_SCOPE_MARKER);
        if (edgeModelingOn) {
            fieldset.querySelector('input[value="web_edge"]').checked = true;
        }
    }

    function applyEdgeModelingState() {
        const toggle = document.getElementById("edge-modeling-toggle");
        const latched = !!(toggle && toggle.disabled && toggle.checked);
        const userPreference = readEdgeModelingPreference();
        const effectiveOn = latched || userPreference === "on";

        const stateChanged = document.body.classList.contains("edge-modeling-on") !== effectiveOn;

        document.body.classList.toggle("edge-modeling-on", effectiveOn);
        document.body.classList.toggle("edge-modeling-off", !effectiveOn);

        if (toggle) {
            toggle.checked = effectiveOn;
        }
        preselectAiScope(effectiveOn);

        // Toggling hides/shows the edge-paradigm add-buttons (display:none), which reflows the
        // canvas and leaves the leader lines between cards stale — same as an accordion show/hide.
        // Rebuild only when the state actually flips (not on every htmx:afterSettle), and only when
        // the leaderline module is loaded (absent on the Compare dashboard and in JS unit tests).
        if (stateChanged && typeof window.scheduleRebuildAllLeaderLines === "function") {
            window.scheduleRebuildAllLeaderLines();
        }
    }

    function handleEdgeModelingChange(event) {
        const target = event.target;
        if (!target || target.dataset.action !== TOGGLE_ACTION || target.disabled) {
            return;
        }
        writeEdgeModelingPreference(target.checked ? "on" : "off");
        applyEdgeModelingState();
    }

    document.addEventListener("DOMContentLoaded", applyEdgeModelingState);
    document.body.addEventListener("htmx:afterSettle", applyEdgeModelingState);
    document.body.addEventListener("change", handleEdgeModelingChange);

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            EDGE_MODELING_STORAGE_KEY,
            TOGGLE_ACTION,
            applyEdgeModelingState,
            handleEdgeModelingChange,
            readEdgeModelingPreference,
            writeEdgeModelingPreference,
        };
    }
})();
