// ============================================================================
// Result Charts - Main Entry Point
// ============================================================================

import { drawBarResultChart, displayLoaderResult, initializeResultCharts } from "./chart.js";

// ============================================================================
// Global Exports for HTML Event Handlers
// ============================================================================

/**
 * Handle temporal granularity change
 * Updates the chart title and redraws the chart
 */
function handleTemporalGranularityChange() {
    const select = document.getElementById("results_temporal_granularity");
    const title = document.getElementById("barChartTitle");

    if (select && title) {
        const value = select.value;
        const capitalized = value.charAt(0).toUpperCase() + value.slice(1);
        title.textContent = `${capitalized}ly CO2 emissions`;
    }

    drawBarResultChart();
}

// Expose functions to global scope for inline event handlers and other scripts
window.drawBarResultChart = drawBarResultChart;
window.displayLoaderResult = displayLoaderResult;
window.handleTemporalGranularityChange = handleTemporalGranularityChange;

// ============================================================================
// Event Listeners
// ============================================================================

/**
 * Initialize charts when results are ready
 */
document.body.addEventListener("triggerResultRendering", () => {
    initializeResultCharts();
});
