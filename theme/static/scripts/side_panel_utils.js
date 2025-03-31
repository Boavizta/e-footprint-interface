function openSidePanel() {
    let modelCanva = document.getElementById("model-canva");
    let sidePanel = document.getElementById("sidePanel");
    modelCanva.classList.replace("col-12", "col-9");
    sidePanel.classList.replace("d-none", "col-3");
    updateLines();
}

function closeAndEmptySidePanel() {
    let modelCanva = document.getElementById("model-canva");
    let sidePanel = document.getElementById("sidePanel");
    let flatpickrCalendar = document.querySelector('.flatpickr-calendar')
    if (flatpickrCalendar) {
        flatpickrCalendar.remove();
    }
    modelCanva.classList.replace("col-9", "col-12");
    sidePanel.classList.replace("col-3", "d-none");
    sidePanel.innerHTML = "";
    closeTimeseriesChart();
    updateLines();
}
