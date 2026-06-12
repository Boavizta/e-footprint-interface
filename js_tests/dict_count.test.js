const fs = require("fs");
const path = require("path");

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

const FIELD_ID = "EdgeDeviceGroup_edge_device_counts";
const FIXTURES_DIR = path.join(__dirname, "fixtures");

function loadFixture(name) {
    const file = path.join(FIXTURES_DIR, `${name}.html`);
    if (!fs.existsSync(file)) {
        throw new Error(
            `Fixture "${name}" not found at ${file}. Run \`poetry run python js_tests/build_fixtures.py\` (or \`npm run jest\` which chains it).`
        );
    }
    return fs.readFileSync(file, "utf8");
}

beforeEach(() => {
    document.body.innerHTML = loadFixture("dict_count_two_options_empty");
    global.tagFormAsModified.mockClear();
    refreshDictCountField(FIELD_ID);
});

test("adding an entry removes it from the dropdown and inserts a row with count 1", () => {
    document.getElementById(`select-new-object-${FIELD_ID}`).value = "device-1";

    addDictCountEntry(FIELD_ID);

    expect(document.getElementById(FIELD_ID).value).toBe('{"device-1":1}');
    expect(document.getElementById(`objects-already-selected-for-${FIELD_ID}`).textContent)
        .toContain("Device 1");
    expect([...document.getElementById(`select-new-object-${FIELD_ID}`).options].map((opt) => opt.value))
        .toEqual(["device-2"]);
});

test("editing a count updates the hidden JSON field", () => {
    document.getElementById(`select-new-object-${FIELD_ID}`).value = "device-1";
    addDictCountEntry(FIELD_ID);

    updateDictCountEntry(FIELD_ID, "device-1", "4");

    expect(document.getElementById(FIELD_ID).value).toBe('{"device-1":4}');
});

test("removing an entry adds it back to the dropdown", () => {
    document.getElementById(`select-new-object-${FIELD_ID}`).value = "device-1";
    addDictCountEntry(FIELD_ID);

    removeDictCountEntry(FIELD_ID, "device-1");

    expect(document.getElementById(FIELD_ID).value).toBe("{}");
    expect([...document.getElementById(`select-new-object-${FIELD_ID}`).options].map((opt) => opt.value))
        .toEqual(["device-1", "device-2"]);
});

test("duplicate entries cannot be added because selected entries disappear from the dropdown", () => {
    document.getElementById(`select-new-object-${FIELD_ID}`).value = "device-1";
    addDictCountEntry(FIELD_ID);

    expect([...document.getElementById(`select-new-object-${FIELD_ID}`).options].map((opt) => opt.value))
        .toEqual(["device-2"]);
});

test("the hidden JSON payload stays in sync after multiple add remove edit operations", () => {
    document.getElementById(`select-new-object-${FIELD_ID}`).value = "device-1";
    addDictCountEntry(FIELD_ID);
    document.getElementById(`select-new-object-${FIELD_ID}`).value = "device-2";
    addDictCountEntry(FIELD_ID);

    updateDictCountEntry(FIELD_ID, "device-2", "5");
    removeDictCountEntry(FIELD_ID, "device-1");

    expect(document.getElementById(FIELD_ID).value).toBe('{"device-2":5}');
});

describe("insertion-ordered rendering", () => {
    const STEPS_FIELD_ID = "UsageJourney_uj_steps";

    beforeEach(() => {
        document.body.innerHTML = loadFixture("dict_count_steps_preselected");
        refreshDictCountField(STEPS_FIELD_ID);
    });

    test("rows follow the selected map order, not the alphabetical options order", () => {
        const rowLabels = [...document.querySelectorAll(
            `#objects-already-selected-for-${STEPS_FIELD_ID} tr td:first-child`)]
            .map((cell) => cell.textContent.trim());

        expect(rowLabels).toEqual(["Search", "Browse", "Checkout"]);
    });

    test("editing a value keeps the order and updates the hidden JSON in place", () => {
        updateDictCountEntry(STEPS_FIELD_ID, "step-browse", "3.5");

        expect(document.getElementById(STEPS_FIELD_ID).value)
            .toBe('{"step-search":1,"step-browse":3.5,"step-checkout":0.5}');
        const rowLabels = [...document.querySelectorAll(
            `#objects-already-selected-for-${STEPS_FIELD_ID} tr td:first-child`)]
            .map((cell) => cell.textContent.trim());
        expect(rowLabels).toEqual(["Search", "Browse", "Checkout"]);
    });

    test("the count column header carries the relationship wording", () => {
        expect(document.querySelector("thead").textContent).toContain("Times per journey");
    });
});
