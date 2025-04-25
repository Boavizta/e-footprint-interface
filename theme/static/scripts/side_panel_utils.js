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
    let sidePanel = document.getElementById("sidePanel");
    sidePanel.classList.remove("d-none");
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
    let sidePanel = document.getElementById("sidePanel");
    let flatpickrCalendar = document.querySelector('.flatpickr-calendar')
    if (flatpickrCalendar) {
        flatpickrCalendar.remove();
    }
    sidePanel.classList.add("d-none");
    sidePanel.innerHTML = "";
    closeTimeseriesChart();
    elementSizeValue.forEach((el) => {
        root.style.setProperty(el.id, `${el.value}${el.unit}`);
    })
    updateLines();
}
