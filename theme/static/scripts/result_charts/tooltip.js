/**
 * Tooltip Configuration and Transforms for Result Charts
 * Handles tooltip appearance, item ordering, and section grouping
 */

import { CHART_FONT, CHART_COLORS } from "./config.js";

/**
 * Categorize and sort tooltip items into fabrication and usage groups
 * @param {Array} tooltipItems - Array of Chart.js tooltip items
 * @returns {Object} Object with sorted fabrication and usage arrays
 */
function categorizeAndSortTooltipItems(tooltipItems) {
    const fabrication = [];
    const usage = [];

    tooltipItems.forEach((item) => {
        if (item.dataset.label.includes("fabrication")) {
            fabrication.push(item);
        } else if (item.dataset.label.includes("usage")) {
            usage.push(item);
        }
    });

    // Reverse both arrays to show items in reverse order
    fabrication.reverse();
    usage.reverse();

    return { fabrication, usage };
}

/**
 * Calculate total for a category
 * @param {Array} items - Array of tooltip items
 * @returns {number} Sum of all values
 */
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + (item.parsed.y || 0), 0);
}

/**
 * Custom tooltip external function that renders HTML with sections
 */
export function customTooltipHandler(context) {
    // Tooltip Element
    let tooltipEl = document.getElementById("chartjs-tooltip");

    // Create element on first render
    if (!tooltipEl) {
        tooltipEl = document.createElement("div");
        tooltipEl.id = "chartjs-tooltip";
        tooltipEl.innerHTML = "<table></table>";
        document.body.appendChild(tooltipEl);
    }

    // Hide if no tooltip
    const tooltipModel = context.tooltip;
    if (tooltipModel.opacity === 0) {
        tooltipEl.style.opacity = 0;
        return;
    }

    // Set Text
    if (tooltipModel.body) {
        const titleLines = tooltipModel.title || [];
        const { fabrication, usage } = categorizeAndSortTooltipItems(tooltipModel.dataPoints);

        let innerHtml = "<thead>";
        titleLines.forEach((title) => {
            innerHtml += "<tr><th>" + title + "</th></tr>";
        });
        innerHtml += "</thead><tbody>";

        // Add FABRICATION section
        if (fabrication.length > 0) {
            const fabricationTotal = calculateTotal(fabrication);
            innerHtml +=
                '<tr><td class="section-header">FABRICATION: <span class="section-total">' +
                fabricationTotal.toFixed(2) +
                " t CO₂-eq</span></td></tr>";
            fabrication.forEach((item) => {
                const colors = item.dataset.backgroundColor;
                const label = item.dataset.label;
                const value = item.parsed.y.toFixed(2);

                innerHtml += "<tr><td>";
                innerHtml += '<span class="tooltip-color-box" style="background:' + colors + '"></span>';
                innerHtml += label + ": " + value + " t CO₂-eq";
                innerHtml += "</td></tr>";
            });
        }

        // Add USAGE section
        if (usage.length > 0) {
            if (fabrication.length > 0) {
                innerHtml += '<tr><td class="section-spacer"></td></tr>';
            }
            const usageTotal = calculateTotal(usage);
            innerHtml +=
                '<tr><td class="section-header">USAGE: <span class="section-total">' +
                usageTotal.toFixed(2) +
                " t CO₂-eq</span></td></tr>";
            usage.forEach((item) => {
                const colors = item.dataset.backgroundColor;
                const label = item.dataset.label;
                const value = item.parsed.y.toFixed(2);

                innerHtml += "<tr><td>";
                innerHtml += '<span class="tooltip-color-box" style="background:' + colors + '"></span>';
                innerHtml += label + ": " + value + " t CO₂-eq";
                innerHtml += "</td></tr>";
            });
        }

        // Add total if both categories exist
        if (fabrication.length > 0 && usage.length > 0) {
            const fabricationTotal = calculateTotal(fabrication);
            const usageTotal = calculateTotal(usage);
            const grandTotal = fabricationTotal + usageTotal;

            innerHtml += '<tr><td class="section-spacer"></td></tr>';
            innerHtml += '<tr><td class="total-row">Total: ' + grandTotal.toFixed(2) + " t CO₂-eq</td></tr>";
        }

        innerHtml += "</tbody>";

        const tableRoot = tooltipEl.querySelector("table");
        tableRoot.innerHTML = innerHtml;
    }

    const position = context.chart.canvas.getBoundingClientRect();

    // Display, position, and set styles for font
    tooltipEl.style.opacity = 1;
    tooltipEl.style.position = "absolute";
    tooltipEl.style.pointerEvents = "none";
    tooltipEl.style.backgroundColor = CHART_COLORS.tooltipBackground;
    tooltipEl.style.borderRadius = "8px";
    tooltipEl.style.color = "#fff";
    tooltipEl.style.fontFamily = CHART_FONT.family;
    tooltipEl.style.fontSize = CHART_FONT.size + "px";
    tooltipEl.style.zIndex = "1000";
    tooltipEl.style.font = tooltipModel.options.bodyFont.string;
    tooltipEl.style.padding = tooltipModel.options.padding + "px " + tooltipModel.options.padding + "px";

    // Calculate initial position
    let left = position.left + window.pageXOffset + tooltipModel.caretX;
    let top = position.top + window.pageYOffset + tooltipModel.caretY;

    // Get tooltip dimensions (need to briefly show it to measure)
    tooltipEl.style.left = left + "px";
    tooltipEl.style.top = top + "px";
    const tooltipRect = tooltipEl.getBoundingClientRect();

    // Adjust horizontal position if tooltip goes off-screen
    const viewportWidth = window.innerWidth;
    if (left + tooltipRect.width > viewportWidth) {
        // Position to the left of the cursor instead
        left = position.left + window.pageXOffset + tooltipModel.caretX - tooltipRect.width - 10;
    }
    // Make sure it doesn't go off the left edge
    if (left < 0) {
        left = 10;
    }

    // Adjust vertical position if tooltip goes off-screen
    const viewportHeight = window.innerHeight;
    if (top + tooltipRect.height > viewportHeight + window.pageYOffset) {
        // Position above the cursor instead
        top = position.top + window.pageYOffset + tooltipModel.caretY - tooltipRect.height - 10;
    }
    // Make sure it doesn't go off the top edge
    if (top < window.pageYOffset) {
        top = window.pageYOffset + 10;
    }

    // Apply final position
    tooltipEl.style.left = left + "px";
    tooltipEl.style.top = top + "px";
}

/**
 * Complete tooltip configuration object with external custom handler
 */
export const TOOLTIP_CONFIG = {
    enabled: false, // Disable default tooltip
    external: customTooltipHandler,
    mode: "index",
    intersect: false,
};

/**
 * Add tooltip styles to document head
 */
export function injectTooltipStyles() {
    if (document.getElementById("chartjs-tooltip-styles")) {
        return; // Already injected
    }

    const style = document.createElement("style");
    style.id = "chartjs-tooltip-styles";
    style.innerHTML = `
        #chartjs-tooltip {
            opacity: 0;
            transition: opacity 0.15s ease;
        }
        
        #chartjs-tooltip table {
            margin: 0;
            border-spacing: 0;
        }
        
        #chartjs-tooltip thead tr th {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        #chartjs-tooltip tbody tr td {
            padding: 4px 0;
            font-size: 12px;
        }
        
        #chartjs-tooltip .section-header {
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: rgba(255, 255, 255, 0.7);
            padding-top: 4px;
            padding-bottom: 2px;
        }
        
        #chartjs-tooltip .section-total {
            font-weight: 700;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.95);
            text-transform: none;
            letter-spacing: normal;
        }
        
        #chartjs-tooltip .section-spacer {
            height: 8px;
        }
        
        #chartjs-tooltip .total-row {
            font-weight: 600;
            padding-top: 4px;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        #chartjs-tooltip .tooltip-color-box {
            display: inline-block;
            width: 10px;
            height: 10px;
            margin-right: 6px;
            border-radius: 2px;
        }
    `;
    document.head.appendChild(style);
}
