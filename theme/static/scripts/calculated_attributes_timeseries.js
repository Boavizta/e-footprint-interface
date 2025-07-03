let calculatedAttributeChartJSOptions = {
    locale: "en-EN",
    responsive: true,
    maintainAspectRatio: true,
    scales: {
        x: {
            type: 'time',
            time: {
                unit: "day",
                tooltipFormat: "yyyy-MM-dd"
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
        zoom: {
            zoom: {
                drag: {enabled: true,},
                pinch: {enabled: true},
                mode: 'x',
            }
        }
    }
};

window.calculatedAttributesChart = null;

function openCalculatedAttributesChart() {
   let element = document.getElementById("chart-calculated-attribute");
    if(element.classList.contains("d-none")){
        element.classList.remove("d-none");
        element.classList.add("d-block");
    }
}

function closeCalculatedAttributesChart() {
    let element = document.getElementById("chart-calculated-attribute");
    if(element.classList.contains("d-block")){
        element.classList.remove("d-block");
        element.classList.add("d-none");
    }
    window.calculatedAttributesChart = null;
}

function createOrUpdateCalculatedAttributeChart() {
    function resetCanvas(canva) {
      // Remove inline styles that might affect size
      canva.style.width = "";
      canva.style.height = "";
      canva.style.maxWidth = "";
      canva.style.maxHeight = "";

      // Set fixed size (essential for reset to work)
      canva.width = canva.parentElement.clientWidth;
      canva.height = 400;

      // Clear drawing area to be safe
      const ctx = canva.getContext("2d");
      ctx.clearRect(0, 0, canva.width, canva.height);
    }
    let canva = document.getElementById("chart-render-calculated-attribute");

    if (window.calculatedAttributesChart !== null) {
        window.calculatedAttributesChart.destroy();
        window.calculatedAttributesChart = null;
        resetCanvas(canva);
    }

    let aggregatedByDay = JSON.parse(document.getElementById('data_timeseries').textContent);
    let timeSeries = Object.entries(aggregatedByDay).map(([date, value]) => ({
        x: date,
        y: value
    }));
    let labelUnit = document.getElementById("calculate-attribute-label");
    let label = labelUnit.dataset.label;
    let unit = labelUnit.dataset.unit || "";

    window.calculatedAttributesChart = new Chart(canva.getContext("2d"), {
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
}
