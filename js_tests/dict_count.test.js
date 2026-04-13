const {
    addDictCountEntry,
    removeDictCountEntry,
    refreshDictCountField,
    updateDictCountEntry,
} = require("../theme/static/scripts/dict_count.js");

global.convertJsonToStringLikeDjango = JSON.stringify;
global.convertStringLikeJsonToRealJsonFromElementWeb = (elementId) => {
    return JSON.parse(document.getElementById(elementId).dataset.json);
};
global.tagFormAsModified = jest.fn();

function renderField() {
    document.body.innerHTML = `
        <table id="objects-already-selected-for-EdgeDeviceGroup_edge_device_counts"></table>
        <select id="select-new-object-EdgeDeviceGroup_edge_device_counts">
            <option value="device-1">Device 1</option>
            <option value="device-2">Device 2</option>
        </select>
        <button id="add-btn-EdgeDeviceGroup_edge_device_counts" type="button"></button>
        <div id="selected_data_EdgeDeviceGroup_edge_device_counts" data-json="{}"></div>
        <div id="available_data_EdgeDeviceGroup_edge_device_counts"
             data-json='[{"value":"device-1","label":"Device 1"},{"value":"device-2","label":"Device 2"}]'></div>
        <input type="hidden" id="EdgeDeviceGroup_edge_device_counts" value="">
    `;
}

beforeEach(() => {
    renderField();
    global.tagFormAsModified.mockClear();
    refreshDictCountField("EdgeDeviceGroup_edge_device_counts");
});

test("adding an entry removes it from the dropdown and inserts a row with count 1", () => {
    document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").value = "device-1";

    addDictCountEntry("EdgeDeviceGroup_edge_device_counts");

    expect(document.getElementById("EdgeDeviceGroup_edge_device_counts").value).toBe('{"device-1":1}');
    expect(document.getElementById("objects-already-selected-for-EdgeDeviceGroup_edge_device_counts").textContent)
        .toContain("Device 1");
    expect([...document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").options].map((opt) => opt.value))
        .toEqual(["device-2"]);
});

test("editing a count updates the hidden JSON field", () => {
    document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").value = "device-1";
    addDictCountEntry("EdgeDeviceGroup_edge_device_counts");

    updateDictCountEntry("EdgeDeviceGroup_edge_device_counts", "device-1", "4");

    expect(document.getElementById("EdgeDeviceGroup_edge_device_counts").value).toBe('{"device-1":4}');
});

test("removing an entry adds it back to the dropdown", () => {
    document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").value = "device-1";
    addDictCountEntry("EdgeDeviceGroup_edge_device_counts");

    removeDictCountEntry("EdgeDeviceGroup_edge_device_counts", "device-1");

    expect(document.getElementById("EdgeDeviceGroup_edge_device_counts").value).toBe("{}");
    expect([...document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").options].map((opt) => opt.value))
        .toEqual(["device-1", "device-2"]);
});

test("duplicate entries cannot be added because selected entries disappear from the dropdown", () => {
    document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").value = "device-1";
    addDictCountEntry("EdgeDeviceGroup_edge_device_counts");

    expect([...document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").options].map((opt) => opt.value))
        .toEqual(["device-2"]);
});

test("the hidden JSON payload stays in sync after multiple add remove edit operations", () => {
    document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").value = "device-1";
    addDictCountEntry("EdgeDeviceGroup_edge_device_counts");
    document.getElementById("select-new-object-EdgeDeviceGroup_edge_device_counts").value = "device-2";
    addDictCountEntry("EdgeDeviceGroup_edge_device_counts");

    updateDictCountEntry("EdgeDeviceGroup_edge_device_counts", "device-2", "5");
    removeDictCountEntry("EdgeDeviceGroup_edge_device_counts", "device-1");

    expect(document.getElementById("EdgeDeviceGroup_edge_device_counts").value).toBe('{"device-2":5}');
});
