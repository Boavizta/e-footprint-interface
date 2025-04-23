let sidePanelWidthSmall = 'col-4';
let sidePanelWidthLarge = 'col-3';

let modelCanvaWidthSmall = 'col-8';
let modelCanvaWidthLarge = 'col-9';

let root = document.documentElement;

let elementName = ['h6', 'h7', 'h8'];
let elementSize = [
    {"name": "min", "unit": "rem"},
    {"name": "max", "unit": "rem"},
    {"name": "ideal", "unit": "vw"}
];
let elementSizeValue = [];

elementName.forEach((el) => {
    elementSize.forEach((els) => {
        elementSizeValue.push({
            "id": `--${el}-${els.name}`,
            "value": parseFloat(getComputedStyle(root).getPropertyValue(`--${el}-${els.name}`)),
            "unit": els.unit
        })
    });
})

let factorToApplyOnFontSize = 0.2

let widthLimit = 1200;

function openSidePanel() {
    let modelCanva = document.getElementById("model-canva");
    let sidePanel = document.getElementById("sidePanel");
     modelCanva.classList.replace("col-12",
         window.innerWidth <= widthLimit ? modelCanvaWidthSmall : modelCanvaWidthLarge);
    sidePanel.classList.replace("d-none",
        window.innerWidth <= widthLimit ? sidePanelWidthSmall : sidePanelWidthLarge);
    let chartTimeseriesDiv = document.getElementById("chartTimeseries");
    if (chartTimeseriesDiv) {
        chartTimeseriesDiv.classList.add(window.innerWidth <= widthLimit ? "left-small" : "left-large");
    }
    elementSizeValue.forEach((el) => {
        root.style.setProperty(el.id, `${el.value - factorToApplyOnFontSize}${el.unit}`);
    })
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
    closeTimeseriesChart();
    elementSizeValue.forEach((el) => {
        root.style.setProperty(el.id, `${el.value}${el.unit}`);
    })
    updateLines();
}
