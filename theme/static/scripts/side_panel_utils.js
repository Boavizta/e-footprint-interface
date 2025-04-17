let sidePanelWidthSmall = 'col-4';
let sidePanelWidthLarge = 'col-3';

let modelCanvaWidthSmall = 'col-8';
let modelCanvaWidthLarge = 'col-9';

let fontSizeSmall = 'fz-0-6';
let fontSizeSLarge = 'fz-0-7';

let widthLimit = 1200;

function openSidePanel() {
    let modelCanva = document.getElementById("model-canva");
    let sidePanel = document.getElementById("sidePanel");
     modelCanva.classList.replace("col-12",
         window.innerWidth <= widthLimit ? modelCanvaWidthSmall : modelCanvaWidthLarge);
    sidePanel.classList.replace("d-none",
        window.innerWidth <= widthLimit ? sidePanelWidthSmall : sidePanelWidthLarge);
    let elementsToReduce = document.querySelectorAll(".button-card");
    elementsToReduce.forEach((element) => {
        element.classList.remove("fz-0-8");
        element.classList.add(window.innerWidth <= widthLimit ? fontSizeSmall : fontSizeSLarge);
    });
    let chartTimeseriesDiv = document.getElementById("chartTimeseries");
    if (chartTimeseriesDiv) {
        chartTimeseriesDiv.classList.add(window.innerWidth <= widthLimit ? "left-small" : "left-large");
    }
    updateLines();
}

function closeAndEmptySidePanel() {
    let modelCanva = document.getElementById("model-canva");
    let sidePanel = document.getElementById("sidePanel");
    let flatpickrCalendar = document.querySelector('.flatpickr-calendar')
    if (flatpickrCalendar) {
        flatpickrCalendar.remove();
    }
    modelCanva.classList.replace(window.innerWidth <= widthLimit ? modelCanvaWidthSmall : modelCanvaWidthLarge,
        "col-12");
    sidePanel.classList.replace(window.innerWidth <= widthLimit ? sidePanelWidthSmall : sidePanelWidthLarge,
        "d-none");
    sidePanel.innerHTML = "";
    let elementsToReduce = document.querySelectorAll(".button-card");
    elementsToReduce.forEach((element) => {
        element.classList.remove(window.innerWidth <= widthLimit ? fontSizeSmall : fontSizeSLarge);
        element.classList.add("fz-0-8");
    });
    closeTimeseriesChart();
    updateLines();
}
