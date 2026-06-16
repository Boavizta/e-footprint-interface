// Jest coverage for the comparison dashboard chart builders (model-comparison Task 4).
//
// The builders are pure (DOM-free): given the ComparisonService payload they return a Chart.js config.
// These tests pin the magnitude-honesty contract (§4.3) that the builders must not break — a single
// shared y-axis and one legend per chart — and the shaping each variant does on the payload.

const {
    buildPairedChartConfig,
    buildCumulativeChartConfig,
    buildDecompositionChartConfig,
} = require("../theme/static/scripts/result_charts/comparison_charts.js");

function pairedPayload() {
    // A's usage/fabrication mix differs per year (usage-heavy 2026, fabrication-heavy 2027): the
    // adapter ships the EXACT per-year split (from the library per-phase series), so the builder must
    // carry the distinct per-year values through verbatim — never collapse them to one global ratio.
    return {
        labels: ["2026", "2027"],
        datasets: [
            { label: "A usage", data: [200, 30], backgroundColor: "#4878a8", stack: "A" },
            { label: "A fabrication", data: [40, 130], backgroundColor: "#9db9d8", stack: "A" },
            { label: "B usage", data: [60, null], backgroundColor: "#e09f3e", stack: "B" },
            { label: "B fabrication", data: [40, null], backgroundColor: "#f0cf94", stack: "B" },
        ],
    };
}

function cumulativePayload() {
    return {
        labels: ["2026", "2027"],
        datasets: [
            { label: "A", data: [150, 310], borderColor: "#4878a8", backgroundColor: "#4878a8" },
            { label: "B", data: [100, 200], borderColor: "#e09f3e", backgroundColor: "#e09f3e" },
        ],
    };
}

function decompositionPayload() {
    return {
        labels: ["Servers & storage usage", "Edge devices fabrication"],
        datasets: [{ label: "Δ", data: [-660, 90], backgroundColor: ["#2e7d32", "#c62828"] }],
    };
}

describe("buildPairedChartConfig", () => {
    test("keeps the four series, two stacks, and the constant model colours", () => {
        const config = buildPairedChartConfig(pairedPayload());
        expect(config.type).toBe("bar");
        expect(config.data.datasets.map((d) => d.stack)).toEqual(["A", "A", "B", "B"]);
        expect(config.data.datasets[0].backgroundColor).toBe("#4878a8");
        expect(config.data.datasets[2].backgroundColor).toBe("#e09f3e");
    });

    test("uses a single shared stacked y-axis and one legend (magnitude honesty)", () => {
        const config = buildPairedChartConfig(pairedPayload());
        expect(config.options.scales.y.stacked).toBe(true);
        expect(config.options.scales.y.beginAtZero).toBe(true);
        expect(config.options.scales.x.stacked).toBe(true);
        // Exactly one y scale; no per-model secondary axis that would break comparability.
        expect(Object.keys(config.options.scales)).toEqual(["x", "y"]);
        expect(config.options.plugins.legend.display).toBe(true);
    });

    test("passes blank (null) buckets through unchanged so non-covered years stay empty", () => {
        const config = buildPairedChartConfig(pairedPayload());
        expect(config.data.datasets[2].data).toEqual([60, null]);
    });

    test("carries the exact per-year usage/fab split through verbatim (no global-ratio flattening)", () => {
        const config = buildPairedChartConfig(pairedPayload());
        // A is usage-heavy in 2026 and fabrication-heavy in 2027 — the builder must keep each year's
        // own split, not redistribute it by one period-wide ratio.
        expect(config.data.datasets[0].data).toEqual([200, 30]); // A usage per year
        expect(config.data.datasets[1].data).toEqual([40, 130]); // A fabrication per year
    });
});

describe("buildCumulativeChartConfig", () => {
    test("overlays two curves on one shared y-axis with one legend", () => {
        const config = buildCumulativeChartConfig(cumulativePayload());
        expect(config.type).toBe("line");
        expect(config.data.datasets).toHaveLength(2);
        expect(Object.keys(config.options.scales)).toEqual(["x", "y"]);
        expect(config.options.scales.y.beginAtZero).toBe(true);
        expect(config.options.plugins.legend.display).toBe(true);
    });

    test("shades the band between the curves (second fills to the first)", () => {
        const config = buildCumulativeChartConfig(cumulativePayload());
        expect(config.data.datasets[0].fill).toBe(false);
        expect(config.data.datasets[1].fill).toMatchObject({ target: 0 });
    });

    test("keeps the model identity colours on the curves", () => {
        const config = buildCumulativeChartConfig(cumulativePayload());
        expect(config.data.datasets[0].borderColor).toBe("#4878a8");
        expect(config.data.datasets[1].borderColor).toBe("#e09f3e");
    });
});

describe("buildDecompositionChartConfig", () => {
    test("renders horizontal bars on a single value axis, per-bar signed colours", () => {
        const config = buildDecompositionChartConfig(decompositionPayload());
        expect(config.type).toBe("bar");
        expect(config.options.indexAxis).toBe("y");
        expect(config.data.datasets[0].data).toEqual([-660, 90]);
        expect(config.data.datasets[0].backgroundColor).toEqual(["#2e7d32", "#c62828"]);
        // No legend (the colour itself reads the direction); one shared value axis.
        expect(config.options.plugins.legend.display).toBe(false);
    });
});
