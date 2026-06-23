// Jest coverage for the comparison dashboard chart builders.
//
// The builders are pure (DOM-free): given the ComparisonService payload they return a Chart.js config.
// These tests pin the magnitude-honesty contract that the builders must not break — a single
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
            { label: "A usage", data: [200, 30], backgroundColor: "#4878a8", stack: "A", valueLabels: ["200 kg", "30 kg"] },
            { label: "A fabrication", data: [40, 130], backgroundColor: "#9db9d8", stack: "A", valueLabels: ["40 kg", "130 kg"] },
            { label: "B usage", data: [60, null], backgroundColor: "#e09f3e", stack: "B", valueLabels: ["60 kg", null] },
            { label: "B fabrication", data: [40, null], backgroundColor: "#f0cf94", stack: "B", valueLabels: ["40 kg", null] },
        ],
    };
}

function cumulativePayload() {
    return {
        labels: ["2026", "2027"],
        datasets: [
            { label: "A", data: [150, 310], borderColor: "#4878a8", backgroundColor: "#4878a8", valueLabels: ["150 kg", "310 kg"] },
            { label: "B", data: [100, 200], borderColor: "#e09f3e", backgroundColor: "#e09f3e", valueLabels: ["100 kg", "200 kg"] },
        ],
    };
}

function decompositionPayload() {
    return {
        labels: ["Servers & storage usage", "Edge devices fabrication"],
        axisUnit: "kg",
        axisScale: 1,
        datasets: [{
            label: "Δ",
            data: [-660, 90],
            backgroundColor: ["#2e7d32", "#c62828"],
            valueLabels: ["−660 kg", "+90 kg"],
        }],
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

    test("tooltip prints the adapter's pre-formatted figure, not the raw number", () => {
        const config = buildPairedChartConfig(pairedPayload());
        const label = config.options.plugins.tooltip.callbacks.label;
        const context = { dataset: config.data.datasets[0], dataIndex: 0, formattedValue: "200" };
        expect(label(context)).toBe("A usage: 200 kg");
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

    test("gap colour tracks Δ: red when B is above A (more), green when below (a reduction)", () => {
        const config = buildCumulativeChartConfig(cumulativePayload());
        const { above, below } = config.data.datasets[1].fill;
        expect(above).toBe("rgba(198,40,40,0.12)"); // B above A ⇒ emits more ⇒ red
        expect(below).toBe("rgba(46,125,50,0.12)"); // B below A ⇒ a reduction ⇒ green
    });

    test("keeps the model identity colours on the curves", () => {
        const config = buildCumulativeChartConfig(cumulativePayload());
        expect(config.data.datasets[0].borderColor).toBe("#4878a8");
        expect(config.data.datasets[1].borderColor).toBe("#e09f3e");
    });

    test("tooltip prints the adapter's pre-formatted figure, not the raw number", () => {
        const config = buildCumulativeChartConfig(cumulativePayload());
        const label = config.options.plugins.tooltip.callbacks.label;
        const context = { dataset: config.data.datasets[1], dataIndex: 1, formattedValue: "200" };
        expect(label(context)).toBe("B: 200 kg");
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
        // No tooltip — the tip labels already print each Δ, so a hover would only repeat them.
        expect(config.options.plugins.tooltip.enabled).toBe(false);
    });

    test("registers the value-labels plugin so each bar prints its Δ at the tip", () => {
        const config = buildDecompositionChartConfig(decompositionPayload());
        expect(config.plugins.map((p) => p.id)).toContain("decompositionValueLabels");
        // The display strings the plugin prints ride along on the dataset, untouched by the builder.
        expect(config.data.datasets[0].valueLabels).toEqual(["−660 kg", "+90 kg"]);
    });
});

describe("adaptive value-axis unit", () => {
    // The data rides in kg; the adapter ships axisUnit (axis-title label) + axisScale (kg → unit
    // factor) so a tonne-scale comparison reads on a tonne axis instead of a six-figure kg one.
    const valueAxis = {
        decomposition: (p) => buildDecompositionChartConfig(p).options.scales.x,
        paired: (p) => buildPairedChartConfig(p).options.scales.y,
        cumulative: (p) => buildCumulativeChartConfig(p).options.scales.y,
    };
    const tonne = (payload) => ({ ...payload, axisUnit: "t", axisScale: 0.001 });

    test("axis title carries the payload's unit, defaulting to kg when none is shipped", () => {
        expect(valueAxis.paired(pairedPayload()).title.text).toBe("kg CO₂e");
        expect(valueAxis.cumulative(tonne(cumulativePayload())).title.text).toBe("t CO₂e");
        expect(valueAxis.decomposition(tonne(decompositionPayload())).title.text).toBe("t CO₂e difference (B − A)");
        // A payload with no axisUnit (older shape) still reads kg rather than "undefined".
        const legacy = { ...decompositionPayload() };
        delete legacy.axisUnit;
        expect(valueAxis.decomposition(legacy).title.text).toBe("kg CO₂e difference (B − A)");
    });

    test("tick callback scales the kg value into the axis unit (660000 kg → 660 on a t axis)", () => {
        const tick = valueAxis.decomposition(tonne(decompositionPayload())).ticks.callback;
        expect(tick(-660000)).toBe("-660");
        expect(tick(1000000)).toBe("1,000");
        // No scale shipped ⇒ the kg value passes through unchanged.
        expect(valueAxis.paired(pairedPayload()).ticks.callback(200)).toBe("200");
    });
});
