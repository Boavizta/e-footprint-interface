// ============================================================================
// Legend Plugin Utilities & Plugin
// ============================================================================

import { LEGEND_STYLES, LEGEND_CATEGORIES } from "./config.js";

/**
 * Apply styles from config object to an element
 * @param {HTMLElement} element - Element to style
 * @param {Object} styleConfig - Style configuration object
 */
export function applyStyles(element, styleConfig) {
    Object.entries(styleConfig).forEach(([property, value]) => {
        element.style[property] = value;
    });
}

/**
 * Update a legend capsule's visual state based on hidden status
 * @param {HTMLButtonElement} capsule - The capsule button element
 * @param {boolean} isHidden - Whether the item is hidden
 * @param {string} fillStyle - The color of the item
 */
function updateCapsuleVisualState(capsule, isHidden, fillStyle) {
    const styles = isHidden ? LEGEND_STYLES.capsule.hidden : LEGEND_STYLES.capsule.active;

    capsule.setAttribute("aria-pressed", !isHidden);
    capsule.style.borderColor = fillStyle;
    capsule.style.backgroundColor = isHidden ? "transparent" : fillStyle;
    capsule.style.color = isHidden ? fillStyle : styles.color;
    capsule.style.boxShadow = styles.boxShadow;
    capsule.style.opacity = styles.opacity;
}

/**
 * Show only one specific dataset and hide all others
 * @param {Chart} chart - Chart.js instance
 * @param {number} targetIndex - Dataset index to show
 * @param {HTMLElement} legendContainer - Legend container element
 */
function showOnlyDataset(chart, targetIndex, legendContainer) {
    chart.data.datasets.forEach((dataset, index) => {
        const meta = chart.getDatasetMeta(index);
        meta.hidden = index !== targetIndex;

        // Update capsule visual state
        const capsule = legendContainer.querySelector(`[data-dataset-index="${index}"]`);
        if (capsule) {
            updateCapsuleVisualState(capsule, meta.hidden, dataset.backgroundColor);
        }
    });
    chart.update();
    updateAllOnlyButtons(chart, legendContainer);
}

/**
 * Show all datasets
 * @param {Chart} chart - Chart.js instance
 * @param {HTMLElement} legendContainer - Legend container element
 */
function showAllDatasets(chart, legendContainer) {
    chart.data.datasets.forEach((dataset, index) => {
        const meta = chart.getDatasetMeta(index);
        meta.hidden = false;

        // Update capsule visual state
        const capsule = legendContainer.querySelector(`[data-dataset-index="${index}"]`);
        if (capsule) {
            updateCapsuleVisualState(capsule, false, dataset.backgroundColor);
        }
    });

    chart.update();
    updateAllOnlyButtons(chart, legendContainer);
}

/**
 * Count how many datasets are currently visible
 * @param {Chart} chart - Chart.js instance
 * @returns {number} Number of visible datasets
 */
function countVisibleDatasets(chart) {
    return chart.data.datasets.filter((_, index) => {
        const meta = chart.getDatasetMeta(index);
        return !meta.hidden;
    }).length;
}

/**
 * Update all "only" buttons to show "only" or "all" based on current state
 * @param {Chart} chart - Chart.js instance
 * @param {HTMLElement} legendContainer - Legend container element
 */
function updateAllOnlyButtons(chart, legendContainer) {
    const visibleCount = countVisibleDatasets(chart);
    const shouldShowAll = visibleCount === 1;

    legendContainer.querySelectorAll("[data-dataset-index]").forEach((capsule) => {
        const onlyBtn = capsule.querySelector("button");
        if (onlyBtn) {
            onlyBtn.textContent = shouldShowAll ? "all" : "only";
            onlyBtn.setAttribute("title", shouldShowAll ? "Show all datasets" : "Show only this dataset");
        }
    });
}

/**
 * Create a legend capsule button for a chart item
 * @param {Object} item - Legend item from Chart.js
 * @param {Chart} chart - Chart.js instance
 * @param {HTMLElement} legendContainer - Legend container element
 * @returns {HTMLButtonElement} Capsule button element
 */
export function createLegendCapsule(item, chart, legendContainer) {
    const capsule = document.createElement("div");
    capsule.style.cssText = LEGEND_STYLES.capsule.base;
    capsule.setAttribute("data-dataset-index", item.datasetIndex);

    // Label span - use full text
    const labelSpan = document.createElement("span");
    labelSpan.textContent = item.text;
    labelSpan.style.flex = "1";

    // "Only" button
    const onlyBtn = document.createElement("button");
    onlyBtn.textContent = "only";
    onlyBtn.setAttribute("type", "button");
    onlyBtn.style.cssText = LEGEND_STYLES.onlyButton.base;
    onlyBtn.setAttribute("title", "Show only this dataset");

    capsule.appendChild(labelSpan);
    capsule.appendChild(onlyBtn);

    // Set initial visual state
    updateCapsuleVisualState(capsule, item.hidden, item.fillStyle);

    // Hover effect on capsule
    capsule.addEventListener("mouseenter", () => {
        const meta = chart.getDatasetMeta(item.datasetIndex);
        if (!meta.hidden) {
            capsule.style.transform = "translateY(-1px)";
            capsule.style.boxShadow = "0 2px 4px rgba(0,0,0,0.15)";
        }
        // Show "only" button on hover
        onlyBtn.style.opacity = "1";
        onlyBtn.style.backgroundColor = "rgba(255, 255, 255, 0.3)";
    });

    capsule.addEventListener("mouseleave", () => {
        const meta = chart.getDatasetMeta(item.datasetIndex);
        capsule.style.transform = "translateY(0)";
        capsule.style.boxShadow = meta.hidden ? "none" : "0 1px 2px rgba(0,0,0,0.1)";
        // Hide "only" button when not hovering
        onlyBtn.style.opacity = "0";
    });

    // Click on label: Toggle this dataset
    labelSpan.style.cursor = "pointer";
    labelSpan.addEventListener("click", (e) => {
        e.stopPropagation();
        const meta = chart.getDatasetMeta(item.datasetIndex);
        meta.hidden = !meta.hidden;
        updateCapsuleVisualState(capsule, meta.hidden, item.fillStyle);
        chart.update();
        updateAllOnlyButtons(chart, legendContainer);
    });

    // Click on "only/all" button
    onlyBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const visibleCount = countVisibleDatasets(chart);

        if (visibleCount === 1) {
            // If only one is visible, clicking "all" shows everything
            showAllDatasets(chart, legendContainer);
        } else {
            // Otherwise, clicking "only" shows only this dataset
            showOnlyDataset(chart, item.datasetIndex, legendContainer);
        }
    });

    onlyBtn.addEventListener("mouseenter", () => {
        onlyBtn.style.backgroundColor = "rgba(255, 255, 255, 0.4)";
    });

    onlyBtn.addEventListener("mouseleave", () => {
        onlyBtn.style.backgroundColor = "rgba(255, 255, 255, 0.3)";
    });

    return capsule;
}

/**
 * Create a compact legend section with inline title and items
 * @param {string} title - Section title
 * @param {string} categoryKey - Category key
 * @param {Array} items - Legend items for this section
 * @param {Chart} chart - Chart.js instance
 * @param {HTMLElement} legendContainer - Legend container element
 * @returns {HTMLDivElement} Section element
 */
export function createLegendSection(title, categoryKey, items, chart, legendContainer) {
    const section = document.createElement("div");
    applyStyles(section, LEGEND_STYLES.section);
    section.setAttribute("data-category", categoryKey);

    // Category label
    const label = document.createElement("div");
    label.textContent = title;
    applyStyles(label, LEGEND_STYLES.categoryLabel);
    section.appendChild(label);

    const itemsContainer = document.createElement("div");
    applyStyles(itemsContainer, LEGEND_STYLES.itemsContainer);

    items.forEach((item) => {
        itemsContainer.appendChild(createLegendCapsule(item, chart, legendContainer));
    });

    section.appendChild(itemsContainer);
    return section;
}

/**
 * Get or create legend container for a chart
 * Place it inside the canvas's parent div (the content-result-chart container)
 * @param {Chart} chart - Chart.js instance
 * @returns {HTMLElement|null} Legend container element
 */
export function getLegendContainer(chart) {
    const legendId = `${chart.canvas.id}-legend`;
    let container = document.getElementById(legendId);

    if (!container) {
        container = document.createElement("div");
        container.id = legendId;

        // Insert legend inside the canvas parent container (after the canvas)
        chart.canvas.parentNode.appendChild(container);
    }

    return container;
}

/**
 * Filter legend items by category
 * @param {Array} items - Legend items to filter
 * @param {string} categoryKey - Category key to filter by
 * @returns {Array} Filtered items
 */
export function filterItemsByCategory(items, categoryKey) {
    return items.filter((item) => item.text.toLowerCase().includes(categoryKey));
}

/**
 * Custom legend plugin to create capsule-style split legend
 */
export const splitCapsuleLegendPlugin = {
    id: "splitCapsuleLegend",
    afterUpdate(chart) {
        const { legend } = chart;
        if (!legend?.legendItems) return;

        const legendContainer = getLegendContainer(chart);
        if (!legendContainer) return;

        // Only rebuild legend if it's empty or explicitly marked for rebuild
        const needsRebuild = legendContainer.children.length === 0 || chart._legendNeedsRebuild === true;

        if (!needsRebuild) return;

        chart._legendNeedsRebuild = false;

        // Clear and style container
        legendContainer.innerHTML = "";
        applyStyles(legendContainer, LEGEND_STYLES.container);

        // Create sections container
        const sectionsContainer = document.createElement("div");
        applyStyles(sectionsContainer, LEGEND_STYLES.sectionsContainer);

        // Split and render legend items by category
        const usageItems = filterItemsByCategory(legend.legendItems, LEGEND_CATEGORIES.USAGE.key).reverse();
        const fabricationItems = filterItemsByCategory(legend.legendItems, LEGEND_CATEGORIES.FABRICATION.key).reverse();

        if (fabricationItems.length > 0) {
            sectionsContainer.appendChild(
                createLegendSection(
                    LEGEND_CATEGORIES.FABRICATION.title,
                    LEGEND_CATEGORIES.FABRICATION.key,
                    fabricationItems,
                    chart,
                    legendContainer
                )
            );
        }

        if (usageItems.length > 0) {
            sectionsContainer.appendChild(
                createLegendSection(
                    LEGEND_CATEGORIES.USAGE.title,
                    LEGEND_CATEGORIES.USAGE.key,
                    usageItems,
                    chart,
                    legendContainer
                )
            );
        }

        legendContainer.appendChild(sectionsContainer);
    },
};
