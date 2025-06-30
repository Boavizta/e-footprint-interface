let formModified = false;
let pendingRequest = null;

function openSidePanel() {
    let sidePanel = document.getElementById("sidePanel");
    let modelCanvaScrollableArea = document.getElementById("model-canva-scrollable-area");
    sidePanel.classList.remove("d-none");
    updateLines();
    let btn = document.getElementById("btn-open-panel-result");
    if (!btn.classList.contains("result-width")) {
        btn.classList.remove("w-100");
        btn.classList.add("result-width");
    }
    modelCanvaScrollableArea.classList.remove("w-100");
    modelCanvaScrollableArea.classList.add("side-panel-open");
    hideEditIcons();
    updateLines();

    let scrollTarget = document.getElementById("sidePanelTitle");
    sidePanel.scrollTo({
        top: scrollTarget.offsetTop,
        behavior: "smooth"
    })

    formModified = false
    pendingRequest = null
}

function closeAndEmptySidePanel() {
    let sidePanel = document.getElementById("sidePanel");
    let flatpickrCalendar = document.querySelector('.flatpickr-calendar')
    let modelCanvaScrollableArea = document.getElementById("model-canva-scrollable-area");
    if (flatpickrCalendar) {
        flatpickrCalendar.remove();
    }
    sidePanel.classList.add("d-none");
    sidePanel.innerHTML = "";
    closeTimeseriesChart();

    let panel = document.getElementById("panel-result-btn");
    if (panel.classList.contains("result-width")) {
        panel.classList.remove("result-width");
        panel.classList.add("w-100");
    }

    let btn = document.getElementById("btn-open-panel-result");
    if (btn.classList.contains("result-width")) {
        btn.classList.remove("result-width");
        btn.classList.add("w-100");
    }

    modelCanvaScrollableArea.classList.remove("side-panel-open");
    modelCanvaScrollableArea.classList.add("w-100");

    formModified = false
    pendingRequest = null

    removeAllOpenedObjectsHighlights()
    updateLines();
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

function updateFormModified(){
    formModified = true;
}

document.body.addEventListener("htmx:beforeRequest", function (event) {
    const elt = event.target;
    if (event.detail.elt.getAttribute("hx-target") === "#sidePanel" && formModified) {
        event.preventDefault();
        pendingRequest = elt;
        const modal = new bootstrap.Modal(document.getElementById("unsavedModal"));
        document.getElementById('continue-unsaved-modal').setAttribute("onclick", "proceedWithChange()");
        modal.show();
    }
});

function warnBeforeCloseSidePanel() {
    if (formModified) {
        const modal = new bootstrap.Modal(document.getElementById("unsavedModal"));
        modal.show();
        document.getElementById('continue-unsaved-modal').setAttribute("onclick", "triggerCloseWarnModalAndTriggerCloseSidePanel()");
    } else {
        closeAndEmptySidePanel();
    }
}

function triggerCloseWarnModalAndTriggerCloseSidePanel() {
    closeWarnModal()
    closeAndEmptySidePanel();
}

function closeWarnModal(){
    const modalEl = document.getElementById("unsavedModal");
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (document.activeElement) {
        document.activeElement.blur();
    }
    modal.hide();
    modalEl.addEventListener("hidden.bs.modal", () => {
        document.getElementById("add_usage_pattern")?.focus();
    }, { once: true });
}

function proceedWithChange() {
    if (pendingRequest) {
        formModified = false;
        htmx.ajax("GET", pendingRequest.getAttribute("hx-get"), {
            target: "#sidePanel",
            swap: "innerHTML"
        });
        pendingRequest = null;
    }
    closeWarnModal();
}
