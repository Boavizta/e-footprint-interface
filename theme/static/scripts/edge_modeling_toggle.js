/* Edge modeling toggle — drives `body.edge-modeling-on/off` from a localStorage flag and the
   server-rendered latch state. CSS keyed off that body class hides edge-paradigm add-buttons.
   See conventions.md → JavaScript. */
const EDGE_MODELING_STORAGE_KEY = "efootprint.edgeModeling";

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

    if (typeof bootstrap !== "undefined" && bootstrap.Popover) {
        const wrapper = document.getElementById("edge-modeling-toggle-wrapper");
        if (wrapper) {
            wrapper.querySelectorAll('[data-bs-toggle="popover"]')
                .forEach(el => bootstrap.Popover.getOrCreateInstance(el));
        }
        document.querySelectorAll('.modeling-paradigm-dot[data-bs-toggle="popover"]')
            .forEach(el => bootstrap.Popover.getOrCreateInstance(el));
    }
}

function handleEdgeModelingChange(event) {
    const toggle = event.target;
    if (!toggle || toggle.id !== "edge-modeling-toggle" || toggle.disabled) {
        return;
    }
    writeEdgeModelingPreference(toggle.checked ? "on" : "off");
    applyEdgeModelingState();
}

document.addEventListener("DOMContentLoaded", applyEdgeModelingState);
document.body.addEventListener("htmx:afterSettle", applyEdgeModelingState);
document.body.addEventListener("change", handleEdgeModelingChange);

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        EDGE_MODELING_STORAGE_KEY,
        applyEdgeModelingState,
        handleEdgeModelingChange,
        readEdgeModelingPreference,
        writeEdgeModelingPreference,
    };
}
