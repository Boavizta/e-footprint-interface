// Pure filtering helpers for the chart legend. CommonJS so Jest can require them directly.

/**
 * Filter legend items based on edge-modeling state.
 *
 * Items whose backing dataset carries isEdge: true represent the edge-device modeling
 * dimension. When edge modeling is off that dimension is inactive, so its legend entries
 * are hidden to avoid showing categories with no data.
 *
 * @param {Array} legendItems - Chart.js legend items
 * @param {Array} datasets    - Chart.js dataset array (chart.data.datasets)
 * @param {boolean} edgeModelingOn - Whether edge modeling is currently active
 * @returns {Array} Filtered legend items
 */
function filterEdgeAwareItems(legendItems, datasets, edgeModelingOn) {
    if (edgeModelingOn) return legendItems;
    return legendItems.filter((item) => !datasets[item.datasetIndex]?.isEdge);
}

module.exports = { filterEdgeAwareItems };
