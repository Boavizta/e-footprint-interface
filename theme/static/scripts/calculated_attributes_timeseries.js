let calculatedAttributeChartJSOptions = {
    locale: "en-EN",
    responsive: true,
    maintainAspectRatio: true,
    scales: {
        x: {
            type: 'time',
            time: {
                tooltipFormat: 'yyyy',
                unit: 'year'
            },
            title: { display: false },
            grid: { display: false }
        },
        y: {
            display: true,
            title: {
                display: true,
                text: 'default_text',
            },
            beginAtZero: true
        }
    },
    plugins: {
        tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || '';
                    let value = context.parsed.y;
                    if (value !== null && value !== undefined) {
                        value = value.toFixed(1);
                    }
                    return `${label}: ${value}`;
                }
            }
        },
        legend: { display: false },
        responsive: true,
        maintainAspectRatio: false,
        zoom: {
            zoom: {
                drag: {enabled: true,},
                pinch: {enabled: true},
                mode: 'x',
            }
        }
    }
};

const chartRegistry = new Map();

function openCalculatedAttributesChart(attributeId) {
   let element = document.getElementById("chart-calculated-attribute");

    if(element.classList.contains("d-none")){
        element.classList.remove("d-none");
        element.classList.add("d-block");
    }
    createOrUpdateCalculatedAttributeChart(attributeId);
}

function closeCalculatedAttributesChart() {
    let element = document.getElementById("chart-calculated-attribute");
    if(element.classList.contains("d-block")){
        element.classList.remove("d-block");
        element.classList.add("d-none");
    }
    let canva = document.getElementById("chart-render-calculated-attribute");
    if (canva && chartRegistry.has(canva)) {
        chartRegistry.get(canva).destroy();
        chartRegistry.delete(canva);
    }
}

function createOrUpdateCalculatedAttributeChart(attributeId) {
    let sourceElement = document.getElementById("calculated-attribute-chart-data-" + attributeId);
    let canva = document.getElementById("chart-render-calculated-attribute");
    if (!sourceElement || !canva) {
        console.warn("Élément introuvable");
        return;
    }

    let data = JSON.parse(sourceElement.dataset.json);
    let startDate = luxon.DateTime.fromISO(sourceElement.dataset.startDate);
    let hours = data.map((_, index) =>
        startDate.plus({ hours: index }).toISO()
    );

    let aggregatedByDay = sumDailyValuesByDisplayGranularity(hours, data, "day");

    let timeSeries = Object.entries(aggregatedByDay).map(([date, value]) => ({
        x: date,
        y: value
    }));

    if (chartRegistry.has(canva)) {
        chartRegistry.get(canva).destroy();
    }

    let label = sourceElement.dataset.label;
    let unit = sourceElement.dataset.unit || "";

    let chart = new Chart(canva.getContext("2d"), {
        type: "line",
        data: {
            datasets: [{
                label: label + (unit ? ` (${unit})` : ""),
                data: timeSeries,
                borderColor: "#007bff",
                fill: false,
                pointRadius: 2,
                tension: 0.1
            }]
        },
        options: {
            ...calculatedAttributeChartJSOptions,
            scales: {
                ...calculatedAttributeChartJSOptions.scales,
                x: {
                    ...calculatedAttributeChartJSOptions.scales.x,
                    type: "time",
                    time: {
                        unit: "day",
                        tooltipFormat: "yyyy-MM-dd"
                    }
                },
                y: {
                    ...calculatedAttributeChartJSOptions.scales.y,
                    title: {
                        ...calculatedAttributeChartJSOptions.scales.y.title,
                        text: label + (unit ? ` (${unit})` : "")
                    }
                }
            }
        }
    });

    chartRegistry.set(canva, chart);

    document.getElementById("calculate-attribute-label").innerHTML = `
        <b>${label}</b>
        </br>
        (in ${unit})
    `;

    document.getElementById("calculated-attribute-formula").innerHTML = `${sourceElement.dataset.formula}`;
    document.getElementById("link-render-calculated-attribute").href = "/model_builder/display-calculus-graph/"+sourceElement.dataset.modObjContainer+"/"+sourceElement.dataset.attrNameInModObjContainer+"/"
}

