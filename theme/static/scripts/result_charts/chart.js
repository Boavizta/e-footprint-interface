// ============================================================================
// Chart Creation & Management
// ============================================================================

import { HARDWARE_TYPE_CONFIG, CHART_TYPE_CONFIG, TEMPORAL_UNIT_CONFIG, RESULT_CHART_OPTIONS } from "./config.js";
import { splitCapsuleLegendPlugin } from "./legend.js";
import { TOOLTIP_CONFIG, injectTooltipStyles } from "./tooltip.js";

/**
 * Show loading spinner and hide chart content
 */
export function displayLoaderResult() {
    document.querySelectorAll(".spinner-result-chart").forEach((loader) => {
        loader.classList.remove("d-none");
    });
    document.querySelectorAll(".content-result-chart").forEach((chart) => {
        chart.classList.add("d-none");
    });
}

/**
 * Prepare dataset configuration for a hardware type
 * @param {string} hardwareType - Hardware type key
 * @param {Array} chartValues - Data values for this hardware type
 * @param {string} chartType - Chart type ('line' or 'bar')
 * @returns {Object} Dataset configuration
 */
export function createDatasetConfig(hardwareType, chartValues, chartType) {
    const config = { ...HARDWARE_TYPE_CONFIG[hardwareType] };
    const typeConfig = CHART_TYPE_CONFIG[chartType] || {};

    return {
        ...config,
        ...typeConfig,
        data: chartValues,
    };
}

/**
 * Build chart data from emissions data
 * @param {string} chartType - Chart type ('line' or 'bar')
 * @param {string} granularity - Temporal granularity ('month' or 'year')
 * @returns {Object} Chart.js data object
 */
export function buildChartData(chartType, granularity) {
    const datasets = [];

    for (const hardwareType of Object.keys(window.emissions.values)) {
        let values = Object.values(
            sumDailyValuesByDisplayGranularity(
                window.emissions.dates,
                window.emissions.values[hardwareType],
                granularity
            )
        );

        // Apply cumulative sum for line charts
        if (chartType === "line") {
            values = cumulativeSumFromArray(values);
        }

        datasets.push(createDatasetConfig(hardwareType, values, chartType));
    }

    const labels = generateTimeIndexLabels(window.emissions.dates[0], granularity, datasets[0]?.data.length || 0);

    return { labels, datasets };
}

/**
 * Configure chart options based on temporal granularity
 * @param {string} granularity - Temporal granularity ('month' or 'year')
 * @returns {Object} Chart.js options object
 */
export function configureChartOptions(granularity) {
    const options = JSON.parse(JSON.stringify(RESULT_CHART_OPTIONS)); // Deep clone
    const timeConfig = TEMPORAL_UNIT_CONFIG[granularity] || TEMPORAL_UNIT_CONFIG.year;

    options.scales.x.time.unit = timeConfig.unit;
    options.scales.x.time.tooltipFormat = timeConfig.tooltipFormat;

    // Apply tooltip configuration
    options.plugins.tooltip = TOOLTIP_CONFIG;

    return options;
}

/**
 * Get or create legend container next to canvas
 * @param {HTMLCanvasElement} canvas - Canvas element
 * @param {string} chartType - Chart type identifier
 * @returns {HTMLElement} Legend container
 */
export function ensureLegendContainer(canvas, chartType) {
    const legendId = `${chartType}Chart-legend`;
    let container = document.getElementById(legendId);

    if (!container) {
        container = document.createElement("div");
        container.id = legendId;
        canvas.parentNode.insertBefore(container, canvas.nextSibling);
    } else {
        container.innerHTML = ""; // Clear existing content
    }

    return container;
}

/**
 * Destroy existing chart instance if it exists
 * @param {string} chartType - Chart type identifier
 */
export function destroyExistingChart(chartType) {
    const chartKey = `${chartType}Chart`;
    if (window.charts?.[chartKey]) {
        window.charts[chartKey].destroy();
        window.charts[chartKey] = null;
    }
}

/**
 * Create and render a result chart
 * @param {string} chartType - Chart type ('line' or 'bar')
 * @param {string} granularity - Temporal granularity ('month' or 'year')
 */
export function drawResultChart(chartType, granularity) {
    destroyExistingChart(chartType);

    const canvas = document.getElementById(`${chartType}Chart`);
    if (!canvas) return;

    ensureLegendContainer(canvas, chartType);

    const chartData = buildChartData(chartType, granularity);
    const chartOptions = configureChartOptions(granularity);

    const chart = new Chart(canvas.getContext("2d"), {
        type: chartType,
        data: chartData,
        options: chartOptions,
        plugins: [splitCapsuleLegendPlugin],
    });

    // Mark that legend needs initial build
    chart._legendNeedsRebuild = true;

    // Store chart instance
    window.charts = window.charts || {};
    window.charts[`${chartType}Chart`] = chart;
}

/**
 * Draw bar chart with current temporal granularity from UI
 */
export function drawBarResultChart() {
    const granularitySelect = document.getElementById("results_temporal_granularity");
    const granularity = granularitySelect?.value || "year";
    drawResultChart("bar", granularity);
}

/**
 * Initialize charts when results are ready
 */
export function initializeResultCharts() {
    // Inject tooltip styles once on initialization
    injectTooltipStyles();

    drawResultChart("line", "month");
    drawBarResultChart();
}
