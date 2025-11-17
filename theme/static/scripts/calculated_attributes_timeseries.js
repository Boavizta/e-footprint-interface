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

// ========== Common Chart Utilities ==========

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

function prepareChartCanvas(canvasId) {
    let canva = document.getElementById(canvasId);

    if (window.calculatedAttributesChart !== null) {
        window.calculatedAttributesChart.destroy();
        window.calculatedAttributesChart = null;
        resetCanvas(canva);
    }

    return canva;
}

function extractLabelAndUnit() {
    let labelUnit = document.getElementById("calculate-attribute-label");
    let label = labelUnit.dataset.label;
    let unit = labelUnit.dataset.unit || "";
    return { label, unit };
}

function createChart(canva, timeSeries, label, unit, chartConfig) {
    window.calculatedAttributesChart = new Chart(canva.getContext("2d"), {
        type: "line",
        data: {
            datasets: [{
                label: label + (unit ? ` (${unit})` : ""),
                data: timeSeries,
                borderColor: "#007bff",
                fill: false,
                pointRadius: chartConfig.pointRadius || 2,
                tension: 0.1
            }]
        },
        options: {
            locale: "en-EN",
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: chartConfig.xScale,
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: label + (unit ? ` (${unit})` : "")
                    },
                    beginAtZero: true
                }
            },
            plugins: chartConfig.plugins || calculatedAttributeChartJSOptions.plugins
        }
    });
}

// ========== Specific Chart Creators ==========

function createOrUpdateCalculatedAttributeChart() {
    let canva = prepareChartCanvas("chart-render-calculated-attribute");
    let aggregatedByDay = JSON.parse(document.getElementById('data_timeseries').textContent);
    let timeSeries = Object.entries(aggregatedByDay).map(([date, value]) => ({ x: date, y: value }));
    let { label, unit } = extractLabelAndUnit();

    createChart(canva, timeSeries, label, unit, {
        xScale: calculatedAttributeChartJSOptions.scales.x,
        pointRadius: 2
    });
}

function createOrUpdateRecurrentQuantityChart() {
    let canva = prepareChartCanvas("chart-render-recurrent-attribute");
    let hourlyData = JSON.parse(document.getElementById('data_timeseries').textContent);

    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

    // Create time labels in format "Day HH:00"
    let timeSeries = Object.entries(hourlyData).map(([hourStr, value]) => {
        let hour = parseInt(hourStr);
        let dayIndex = Math.floor(hour / 24);
        let hourOfDay = hour % 24;
        return {
            x: hour,
            y: value,
            label: `${dayNames[dayIndex]} ${hourOfDay.toString().padStart(2, '0')}:00`
        };
    });

    let { label, unit } = extractLabelAndUnit();

    createChart(canva, timeSeries, label, unit, {
        xScale: {
            type: 'linear',
            title: { display: true, text: 'Hour of Week' },
            min: 0,
            max: 167,
            ticks: {
                stepSize: 24,
                callback: function(value) {
                    if (value % 24 === 0) {
                        return dayNames[Math.floor(value / 24)];
                    }
                    return '';
                },
                maxRotation: 45,
                minRotation: 45
            },
            grid: {
                display: true,
                color: function(context) {
                    return context.tick.value % 24 === 0 ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.05)';
                }
            }
        },
        pointRadius: 1,
        plugins: {
            ...calculatedAttributeChartJSOptions.plugins,
            tooltip: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    title: function(context) { return context[0].raw.label; },
                    label: function(context) {
                        let value = context.parsed.y?.toFixed(1);
                        return `${label}: ${value}${unit ? ' ' + unit : ''}`;
                    }
                }
            }
        }
    });
}
