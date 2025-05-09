function openSidePanel() {
    let sidePanel = document.getElementById("sidePanel");
    sidePanel.classList.remove("d-none");
    updateLines();
    let btn = document.getElementById("btn-open-panel-result");
    if (!btn.classList.contains("result-width")) {
        btn.classList.remove("w-100");
        btn.classList.add("result-width");
    }
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
    updateLines();

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
