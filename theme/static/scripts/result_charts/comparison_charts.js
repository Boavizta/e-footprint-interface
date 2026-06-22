// ============================================================================
// Comparison dashboard charts (model-comparison Task 4)
// ============================================================================
//
// Three Chart.js variants for the §4.2 dashboard, all magnitude-honest (§4.3): a single shared y-axis
// and one legend per chart, so the two models' magnitudes read directly against each other. Model
// identity is carried by a constant colour pair baked into the payload by the ComparisonService
// adapter — never by per-chart auto-colours.
//
//   - paired bars: per-year, model A | model B side by side; within each model usage stacks on
//     fabrication (dark = usage, light = fabrication). Two stacks ("A", "B") on one shared y-axis.
//   - cumulative overlay: two curves on one axis; the gap between them is the running avoided/added
//     emissions, the end gap the headline Δ. The area between is shaded.
//   - decomposition: horizontal diverging bars, one per category × phase, signed (green left =
//     reduction, red right = increase).
//
// The *_config builders below are pure (DOM-free) so Jest can assert the data-shaping; drawComparisonCharts
// reads the swapped-in payloads and instantiates the charts.

const SHARED_FONT = {
    family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    size: 12,
};
const GRID_COLOR = "rgba(0, 0, 0, 0.05)";
const TICK_COLOR = "#6b7280";

/**
 * Paired per-year bars on one shared y-axis (kg), one legend over the four series.
 * @param {Object} payload - {labels, datasets:[A usage, A fab, B usage, B fab]} from the adapter.
 * @returns {Object} Chart.js config.
 */
function buildPairedChartConfig(payload) {
    const datasets = payload.datasets.map((dataset) => ({
        ...dataset,
        borderWidth: 0,
        // Each model is its own stack, so A and B sit side by side per year and usage/fab stack within.
        stack: dataset.stack,
    }));

    return {
        type: "bar",
        data: { labels: payload.labels, datasets },
        options: {
            locale: "en-EN",
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            // One shared y-axis; bars from both models are measured against it (magnitude honesty).
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { font: SHARED_FONT, color: TICK_COLOR } },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: { display: true, text: "kg CO₂e", font: SHARED_FONT, color: TICK_COLOR },
                    grid: { color: GRID_COLOR },
                    ticks: { font: SHARED_FONT, color: TICK_COLOR },
                },
            },
            // One legend driving both models' series.
            plugins: { legend: { display: true, position: "bottom", labels: { font: SHARED_FONT } } },
        },
    };
}

/**
 * Cumulative overlay: two curves on one shared y-axis, the area between them shaded as the gap.
 * @param {Object} payload - {labels, datasets:[A, B]} of cumulative kg from the adapter.
 * @returns {Object} Chart.js config.
 */
function buildCumulativeChartConfig(payload) {
    const datasets = payload.datasets.map((dataset, index) => ({
        ...dataset,
        borderWidth: 2.5,
        pointRadius: 3,
        tension: 0.3,
        spanGaps: false,
        // Shade the band between the two curves (B fills to A): the gap is the running Δ (B − A).
        // B above A ⇒ B emits more ⇒ red; B below A ⇒ a reduction ⇒ green.
        fill: index === 1 ? { target: 0, above: "rgba(198,40,40,0.12)", below: "rgba(46,125,50,0.12)" } : false,
    }));

    return {
        type: "line",
        data: { labels: payload.labels, datasets },
        options: {
            locale: "en-EN",
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            scales: {
                x: { grid: { display: false }, ticks: { font: SHARED_FONT, color: TICK_COLOR } },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "kg CO₂e", font: SHARED_FONT, color: TICK_COLOR },
                    grid: { color: GRID_COLOR },
                    ticks: { font: SHARED_FONT, color: TICK_COLOR },
                },
            },
            plugins: { legend: { display: true, position: "bottom", labels: { font: SHARED_FONT } } },
        },
    };
}

/**
 * Inline plugin: print each decomposition bar's pre-formatted Δ at the tip of the bar (the figures
 * that used to sit in the list below the chart). Reads ``dataset.valueLabels`` (display strings shaped
 * by the adapter, e.g. "+571 kg" / "−3 g") so the JS never reformats magnitudes. Positive bars point
 * right and label to the right of the tip, negative bars point left and label to the left; the label
 * takes the bar's own direction colour.
 */
const decompositionValueLabelsPlugin = {
    id: "decompositionValueLabels",
    afterDatasetsDraw(chart) {
        const { ctx } = chart;
        const dataset = chart.data.datasets[0];
        const labels = dataset && dataset.valueLabels;
        if (!labels) return;
        const meta = chart.getDatasetMeta(0);
        ctx.save();
        ctx.font = `600 11px ${SHARED_FONT.family}`;
        ctx.textBaseline = "middle";
        meta.data.forEach((bar, index) => {
            const text = labels[index];
            if (text == null) return;
            const positive = (dataset.data[index] || 0) >= 0;
            ctx.fillStyle = Array.isArray(dataset.backgroundColor)
                ? dataset.backgroundColor[index]
                : dataset.backgroundColor;
            ctx.textAlign = positive ? "left" : "right";
            ctx.fillText(text, bar.x + (positive ? 4 : -4), bar.y);
        });
        ctx.restore();
    },
};

/**
 * Horizontal diverging decomposition bars on a single value axis, signed and per-bar coloured, with
 * each bar's Δ printed at its tip (decompositionValueLabelsPlugin).
 * @param {Object} payload - {labels, datasets:[{data, backgroundColor[], valueLabels[]}]} from the adapter.
 * @returns {Object} Chart.js config.
 */
function buildDecompositionChartConfig(payload) {
    return {
        type: "bar",
        data: payload,
        options: {
            indexAxis: "y", // horizontal bars
            locale: "en-EN",
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            scales: {
                x: {
                    // Headroom on both ends so the tip labels are not clipped at the chart edge.
                    grace: "10%",
                    title: { display: true, text: "kg CO₂e difference (B − A)", font: SHARED_FONT, color: TICK_COLOR },
                    grid: { color: GRID_COLOR },
                    ticks: { font: SHARED_FONT, color: TICK_COLOR },
                },
                y: { grid: { display: false }, ticks: { font: SHARED_FONT, color: TICK_COLOR } },
            },
            // No legend (the colour reads the direction) and no tooltip (the tip labels already
            // print each Δ, so a hover would only repeat them).
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
        },
        plugins: [decompositionValueLabelsPlugin],
    };
}

const COMPARISON_CHART_KEYS = ["comparisonPairedChart", "comparisonCumulativeChart", "comparisonDecompositionChart"];

function destroyComparisonChart(canvasId) {
    window.charts = window.charts || {};
    if (window.charts[canvasId]) {
        window.charts[canvasId].destroy();
        window.charts[canvasId] = null;
    }
}

function renderChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    destroyComparisonChart(canvasId);
    window.charts = window.charts || {};
    window.charts[canvasId] = new Chart(canvas.getContext("2d"), config);
}

/**
 * Read the dashboard's swapped-in payloads and (re)draw all three comparison charts. Re-entrant: the
 * Compare tab re-renders fresh on every visit, so any prior chart instances are destroyed first.
 */
function drawComparisonCharts() {
    const dashboard = document.getElementById("comparison-dashboard");
    if (!dashboard || typeof window.Chart === "undefined") return;

    COMPARISON_CHART_KEYS.forEach(destroyComparisonChart);

    const paired = JSON.parse(dashboard.dataset.pairedChart || "null");
    const cumulative = JSON.parse(dashboard.dataset.cumulativeChart || "null");
    const decomposition = JSON.parse(dashboard.dataset.decompositionChart || "null");

    if (paired) renderChart("comparisonPairedChart", buildPairedChartConfig(paired));
    if (cumulative) renderChart("comparisonCumulativeChart", buildCumulativeChartConfig(cumulative));
    if (decomposition && decomposition.labels.length) {
        renderChart("comparisonDecompositionChart", buildDecompositionChartConfig(decomposition));
    }
}

// CommonJS exports (like display.js): esbuild bundles this into the ESM result_charts bundle, and Jest
// (CommonJS, no babel) can require the pure config builders directly.
module.exports = {
    buildPairedChartConfig,
    buildCumulativeChartConfig,
    buildDecompositionChartConfig,
    drawComparisonCharts,
};
