const { filterEdgeAwareItems } = require("../theme/static/scripts/result_charts/legend_utils.js");

function item(datasetIndex, text) {
    return { datasetIndex, text };
}

function dataset(label, isEdge = false) {
    return { label, ...(isEdge ? { isEdge: true } : {}) };
}

const edgeEnergyItem = item(0, "Edge devices and storage usage");
const edgeFabItem    = item(1, "Edge devices and storage fabrication");
const serverItem     = item(2, "Servers and storage usage");
const networkItem    = item(3, "Network usage");

const mixedDatasets = [
    dataset("Edge_devices_energy", true),
    dataset("Edge_devices_fabrication", true),
    dataset("Servers_and_storage_energy"),
    dataset("Network_energy"),
];

test("edge items are absent from the legend when edge modeling is off", () => {
    const items = [edgeEnergyItem, edgeFabItem, serverItem, networkItem];
    const result = filterEdgeAwareItems(items, mixedDatasets, false);
    expect(result).toHaveLength(2);
    expect(result.map((i) => i.datasetIndex)).toEqual([2, 3]);
});

test("edge items are present when edge modeling is on", () => {
    const items = [edgeEnergyItem, edgeFabItem, serverItem, networkItem];
    const result = filterEdgeAwareItems(items, mixedDatasets, true);
    expect(result).toHaveLength(4);
});

test("non-edge items are unaffected when edge modeling is off", () => {
    const items = [serverItem, networkItem];
    const nonEdgeDatasets = [
        dataset("Servers_and_storage_energy"),
        dataset("Network_energy"),
    ];
    const result = filterEdgeAwareItems(items, nonEdgeDatasets, false);
    expect(result).toHaveLength(2);
    expect(result).toEqual(items);
});

test("handles a dataset entry without isEdge flag as non-edge (not filtered)", () => {
    const items = [item(0, "Some item")];
    const datasetsNoFlag = [dataset("something")]; // no isEdge property at all
    const result = filterEdgeAwareItems(items, datasetsNoFlag, false);
    expect(result).toHaveLength(1);
});

test("handles an out-of-range dataset index gracefully (optional chaining)", () => {
    const items = [item(99, "Ghost item")];
    const result = filterEdgeAwareItems(items, mixedDatasets, false);
    // datasets[99] is undefined — optional chain returns undefined, !undefined is true → kept
    expect(result).toHaveLength(1);
});
