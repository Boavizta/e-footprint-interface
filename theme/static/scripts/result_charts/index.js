// ============================================================================
// Result Charts - Main Entry Point
// ============================================================================

import { drawBarResultChart, displayLoaderResult, initializeResultCharts } from "./chart.js";
import { drawComparisonCharts, destroyComparisonCharts } from "./comparison_charts.js";

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
// The Compare dashboard (HTMX-swapped into the resident #comparison-view) drives its own draw from
// this; dismissing the comparison view destroys the charts (model_comparison.js) so they don't leak.
window.drawComparisonCharts = drawComparisonCharts;
window.destroyComparisonCharts = destroyComparisonCharts;

// ============================================================================
// Event Listeners
// ============================================================================

/**
 * Initialize charts when results are ready
 */
document.body.addEventListener("triggerResultRendering", () => {
    initializeResultCharts();
});
