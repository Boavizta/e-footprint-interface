let formModified = false;
let pendingRequest = null;

function recomputationVals() {
    let btnResultPanel = document.getElementById("btn-open-panel-result");
    if (btnResultPanel && btnResultPanel.style.display === "none") {
        return {recomputation: true};
    }
    return {};
}

function expandRightColumn() {
    const btn = document.getElementById("btn-open-panel-result");
    if (!btn.classList.contains("result-width")) {
        btn.classList.remove("w-100");
        btn.classList.add("result-width");
    }
    // The canvas scroll wrapper is builder-only; on the Compare dashboard the side panel opens over the
    // comparison content (no canvas to reflow), so skip the reflow + line update when it is absent.
    const canvas = document.getElementById("model-canva-scrollable-area");
    if (canvas) {
        canvas.classList.remove("w-100");
        canvas.classList.add("side-panel-open");
        updateLines();
    }
}

function collapseRightColumn() {
    const panel = document.getElementById("panel-result-btn");
    if (panel.classList.contains("result-width")) {
        panel.classList.remove("result-width");
        panel.classList.add("w-100");
    }
    const btn = document.getElementById("btn-open-panel-result");
    if (btn.classList.contains("result-width")) {
        btn.classList.remove("result-width");
        btn.classList.add("w-100");
    }
    const canvas = document.getElementById("model-canva-scrollable-area");
    if (canvas) {
        canvas.classList.remove("side-panel-open");
        canvas.classList.add("w-100");
        updateLines();
    }
}

function openSidePanel() {
    let sidePanel = document.getElementById("sidePanel");
    sidePanel.classList.remove("d-none");
    expandRightColumn();
    hideEditIcons();

    let scrollTarget = document.getElementById("sidePanelTitle");
    sidePanel.scrollTo({
        top: scrollTarget.offsetTop,
        behavior: "smooth"
    })
    closeCalculatedAttributesChart();
    formModified = false;
    pendingRequest = null;
}

function closeAndEmptySidePanel() {
    let sidePanel = document.getElementById("sidePanel");
    let flatpickrCalendar = document.querySelector('.flatpickr-calendar')
    if (flatpickrCalendar) {
        flatpickrCalendar.remove();
    }
    sidePanel.classList.add("d-none");
    sidePanel.innerHTML = "";
    closeTimeseriesChart();
    closeCalculatedAttributesChart();
    collapseRightColumn();

    formModified = false
    pendingRequest = null

    removeAllOpenedObjectsHighlights()
}

function setRecomputationToTrueIfResultPaneIsOpen(){
    let btnResultPanel = document.getElementById("btn-open-panel-result")
    if(btnResultPanel.style.display === 'none'){
        let form = document.getElementById("sidePanelForm");
        let rawVals = form.getAttribute("hx-vals");
        let vals = {};

        if (rawVals) {
            if(rawVals.startsWith("js:")) {
                vals = eval('(' + rawVals.slice(3) + ')');
            } else {
                vals = JSON.parse(rawVals);
            }
        }
        vals["recomputation"] = true;
        form.setAttribute("hx-vals", JSON.stringify(vals));
        displayLoaderResult();
    }
}

function tagFormAsModified(){
    formModified = true;
}

document.body.addEventListener("htmx:beforeRequest", function (event) {
    const elt = event.target;
    if (event.detail.elt.getAttribute("hx-target") === "#sidePanel" && formModified) {
        event.preventDefault();
        pendingRequest = elt;
        const modal = new bootstrap.Modal(document.getElementById("unsavedModal"));
        document.getElementById('continue-unsaved-modal').setAttribute("onclick", "proceedWithPendingRequest()");
        modal.show();
        setTimeout(() => {
            hideLoadingBar();
        }, 200);
    }
});

// Pre-navigation unsaved-changes guard. Leaving the active model with the side panel open silently
// discards its edits. Switching models (switch-model), opening the Compare dashboard (compare/) and the
// +Add actions (add-model for Duplicate/Blank, open-add-model-import-panel for Import) all either
// re-render the builder or swap the side panel without going through the #sidePanel-targeted
// beforeRequest guard above, so it misses them. htmx:confirm fires before the request, so we defer it
// behind the shared unsaved modal and only let it through on "Continue" (issueRequest re-fires the
// exact request). On cancel it is never issued, so the panel and its edits survive. Matching on the
// request path (not a DOM element) covers every entry point — tab strip, mobile pill, burger.
// (remove-model also discards the panel but has its own destructive confirm in model_comparison.js,
// made unsaved-aware there to avoid stacking two dialogs on one click; reset/template-load are exempt —
// they obviously discard the current model, so a separate unsaved warning would be noise.)
// Request URL path segments (not Django route names: e.g. the Compare route is named "compare-models"
// but served at /compare/). Slash-delimited so they can't partial-match a neighbouring path.
const PANEL_DISCARDING_PATHS = [
    "/switch-model/", "/compare/", "/add-model/", "/open-add-model-import-panel/",
];
let pendingNavRequest = null;

document.body.addEventListener("htmx:confirm", function (event) {
    if (!formModified) return;
    const path = event.detail.path || "";
    if (!PANEL_DISCARDING_PATHS.some(p => path.includes(p))) return;
    event.preventDefault();
    pendingNavRequest = event.detail;
    const modal = new bootstrap.Modal(document.getElementById("unsavedModal"));
    document.getElementById('continue-unsaved-modal').setAttribute("onclick", "proceedWithPendingNavigation()");
    modal.show();
});

function proceedWithPendingNavigation() {
    if (pendingNavRequest) {
        formModified = false;
        const detail = pendingNavRequest;
        pendingNavRequest = null;
        detail.issueRequest(true);  // re-fire the deferred request without re-confirming
    }
    closeWarningModal();
}

// Read-only peek for other modules (e.g. model_comparison.js's remove-model confirm) that fold the
// unsaved-changes warning into their own dialog rather than going through the modal above.
function isSidePanelFormModified() {
    return formModified;
}

function warnBeforeClosingSidePanel() {
    if (formModified) {
        const modal = new bootstrap.Modal(document.getElementById("unsavedModal"));
        modal.show();
        document.getElementById('continue-unsaved-modal').setAttribute("onclick", "closeWarningModalAndCloseSidePanel()");
    } else {
        closeAndEmptySidePanel();
    }
}

function proceedWithPendingRequest() {
    if (pendingRequest) {
        formModified = false;
        let rawVals = pendingRequest.getAttribute("hx-vals");
        let vals = {};

        if (rawVals) {
            if (rawVals.startsWith("js:")) {
                vals = eval('(' + rawVals.slice(3) + ')');
            } else {
                vals = JSON.parse(rawVals);
            }
        }

        const url = pendingRequest.getAttribute("hx-get");
        const target = pendingRequest.getAttribute("hx-target") || "#sidePanel";
        const swap = pendingRequest.getAttribute("hx-swap") || "innerHTML";
        htmx.ajax("GET", url, {target: target, swap: swap, values: vals});
        pendingRequest = null;
    }
    closeWarningModal();
}

function closeWarningModalAndCloseSidePanel() {
    closeWarningModal();
    closeAndEmptySidePanel();
}

function closeWarningModal(){
    const modalEl = document.getElementById("unsavedModal");
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (document.activeElement) {
        document.activeElement.blur();
    }
    modal.hide();
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { tagFormAsModified, proceedWithPendingNavigation, isSidePanelFormModified };
}
