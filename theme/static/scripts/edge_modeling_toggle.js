/* Edge modeling toggle — drives `body.edge-modeling-on/off` from a localStorage flag and the
   server-rendered latch state. CSS keyed off that body class hides edge-paradigm add-buttons.
   See conventions.md → JavaScript (IIFE + data-action dispatch). */
(function () {
    const EDGE_MODELING_STORAGE_KEY = "efootprint.edgeModeling";
    const TOGGLE_ACTION = "edge-modeling-toggle";
    const POPOVER_SELECTORS =
        '#edge-modeling-toggle-wrapper [data-bs-toggle="popover"], '
        + '.modeling-paradigm-dot[data-bs-toggle="popover"]';

    function readEdgeModelingPreference() {
        return localStorage.getItem(EDGE_MODELING_STORAGE_KEY) === "on" ? "on" : "off";
    }

    function writeEdgeModelingPreference(value) {
        localStorage.setItem(EDGE_MODELING_STORAGE_KEY, value === "on" ? "on" : "off");
    }

    function applyEdgeModelingState() {
        const toggle = document.getElementById("edge-modeling-toggle");
        const latched = !!(toggle && toggle.disabled && toggle.checked);
        const userPreference = readEdgeModelingPreference();
        const effectiveOn = latched || userPreference === "on";

        document.body.classList.toggle("edge-modeling-on", effectiveOn);
        document.body.classList.toggle("edge-modeling-off", !effectiveOn);

        if (toggle) {
            toggle.checked = effectiveOn;
        }
    }

    function initEdgePopovers(root) {
        if (typeof bootstrap === "undefined" || !bootstrap.Popover) return;
        root.querySelectorAll(POPOVER_SELECTORS)
            .forEach(el => bootstrap.Popover.getOrCreateInstance(el));
    }

    function handleEdgeModelingChange(event) {
        const target = event.target;
        if (!target || target.dataset.action !== TOGGLE_ACTION || target.disabled) {
            return;
        }
        writeEdgeModelingPreference(target.checked ? "on" : "off");
        applyEdgeModelingState();
    }

    document.addEventListener("DOMContentLoaded", () => {
        applyEdgeModelingState();
        initEdgePopovers(document);
    });
    document.body.addEventListener("htmx:afterSettle", (event) => {
        applyEdgeModelingState();
        initEdgePopovers(event.detail && event.detail.elt ? event.detail.elt : document);
    });
    document.body.addEventListener("change", handleEdgeModelingChange);

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            EDGE_MODELING_STORAGE_KEY,
            TOGGLE_ACTION,
            applyEdgeModelingState,
            handleEdgeModelingChange,
            initEdgePopovers,
            readEdgeModelingPreference,
            writeEdgeModelingPreference,
        };
    }
})();
