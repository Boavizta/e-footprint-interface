// ============================================================================
// Configuration Objects
// ============================================================================

/**
 * Style configuration for legend elements
 */
export const LEGEND_STYLES = {
    container: {
        display: "flex",
        flexDirection: "row",
        flexWrap: "wrap",
        gap: "12px",
        marginTop: "24px",
        marginBottom: "24px",
        paddingLeft: "0px",
        paddingRight: "0px",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    sectionsContainer: {
        display: "flex",
        flexDirection: "row",
        flexWrap: "wrap",
        gap: "20px",
        alignItems: "flex-start",
    },
    section: {
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        flex: "1 1 calc(50% - 10px)",
        minWidth: "300px",
        padding: "12px",
        borderRadius: "8px",
        backgroundColor: "#ffffffff",
        border: "1px solid rgba(248, 249, 250, 1)",
    },
    categoryLabel: {
        fontWeight: "600",
        fontSize: "12px",
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        color: "#495057",
        marginBottom: "4px",
    },
    itemsContainer: {
        display: "flex",
        flexDirection: "row",
        gap: "6px",
        flexWrap: "wrap",
    },
    capsule: {
        base: `
            display: inline-flex;
            align-items: center;
            justify-content: space-between;
            padding: 5px 10px;
            border-radius: 12px;
            border-width: 1.5px;
            border-style: solid;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
            gap: 6px;
        `,
        active: {
            backgroundColor: (color) => color,
            color: "#ffffff",
            boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
            opacity: "1",
        },
        hidden: {
            backgroundColor: "transparent",
            boxShadow: "none",
            opacity: "0.4",
        },
        hover: {
            transform: "translateY(-1px)",
            boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
        },
    },
    onlyButton: {
        base: `
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 2px 6px;
            min-width: 32px;
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.2);
            color: currentColor;
            font-size: 9px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            opacity: 0;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            border: none;
        `,
        hover: {
            backgroundColor: "rgba(255, 255, 255, 0.3)",
            opacity: "1",
        },
    },
};

/**
 * Categories for splitting legend items
 */
export const LEGEND_CATEGORIES = {
    FABRICATION: { key: "fabrication", title: "Fabrication" },
    USAGE: { key: "usage", title: "Usage" },
};

/**
 * Font configuration used across charts
 */
export const CHART_FONT = {
    family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    size: 12,
};

/**
 * Color palette for chart elements
 */
export const CHART_COLORS = {
    gridLine: "rgba(0, 0, 0, 0.05)",
    tickLabel: "#6b7280",
    tooltipBackground: "rgba(0, 0, 0, 0.85)",
};

/**
 * Base Chart.js options configuration
 */
export const RESULT_CHART_OPTIONS = {
    locale: "en-EN",
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 2,
    scales: {
        x: {
            offset: true,
            stacked: true,
            type: "time",
            time: {
                tooltipFormat: "yyyy",
                unit: "year",
            },
            title: { display: false },
            grid: {
                display: true,
                color: CHART_COLORS.gridLine,
                drawBorder: false,
            },
            ticks: {
                font: CHART_FONT,
                color: CHART_COLORS.tickLabel,
            },
        },
        y: {
            stacked: true,
            title: { display: false },
            beginAtZero: true,
            grid: {
                color: CHART_COLORS.gridLine,
                drawBorder: false,
            },
            ticks: {
                font: CHART_FONT,
                color: CHART_COLORS.tickLabel,
            },
        },
    },
    plugins: {
        legend: { display: false }, // Use custom legend
        title: { display: false },
        // Tooltip configuration imported from tooltip.js
        tooltip: null, // Will be set dynamically from TOOLTIP_CONFIG
    },
};

/**
 * Hardware type configurations with colors and labels
 */
export const HARDWARE_TYPE_CONFIG = {
    Servers_and_storage_energy: {
        label: "Servers and storage usage",
        backgroundColor: "#80E5DE",
    },
    Edge_devices_energy: {
        label: "Edge devices and storage usage",
        backgroundColor: "#2DC9BF",
    },
    Devices_energy: {
        label: "Devices usage",
        backgroundColor: "#00A19E",
    },
    Network_energy: {
        label: "Network usage",
        backgroundColor: "#006B6B",
    },
    Servers_and_storage_fabrication: {
        label: "Servers and storage fabrication",
        backgroundColor: "#9DC4E6",
    },
    Edge_devices_fabrication: {
        label: "Edge devices and storage fabrication",
        backgroundColor: "#5B9BD5",
    },
    Devices_fabrication: {
        label: "Devices fabrication",
        backgroundColor: "#2E75B6",
    },
};

/**
 * Chart type specific configurations
 */
export const CHART_TYPE_CONFIG = {
    line: {
        borderWidth: 2,
        fill: true,
        tension: 0.4, // Smooth curves
    },
    bar: {
        borderSkipped: false,
    },
};

/**
 * Temporal granularity time unit mappings
 */
export const TEMPORAL_UNIT_CONFIG = {
    month: {
        unit: "month",
        tooltipFormat: "MMM yyyy",
    },
    year: {
        unit: "year",
        tooltipFormat: "yyyy",
    },
};
