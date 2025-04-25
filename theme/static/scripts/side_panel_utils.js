function openSidePanel() {
    let sidePanel = document.getElementById("sidePanel");
    sidePanel.classList.remove("d-none");
    updateLines();
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
}
