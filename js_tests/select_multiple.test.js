const fs = require("fs");
const path = require("path");

const {
    refreshSelectMultipleFields,
    removeValueFromSelectMultiple,
} = require("../theme/static/scripts/select_multiple.js");

global.convertJsonToStringLikeDjango = JSON.stringify;
global.convertStringLikeJsonToRealJsonFromElementWeb = (elementId) => (
    JSON.parse(document.getElementById(elementId).dataset.json)
);
global.tagFormAsModified = jest.fn();

test("a required edge bundle cannot be removed", () => {
    const fixture = path.join(__dirname, "fixtures", "select_multiple_required_bundle.html");
    document.body.innerHTML = fs.readFileSync(fixture, "utf8");
    const fieldId = "EdgeUsagePattern_edge_usage_journeys";

    refreshSelectMultipleFields(fieldId);
    removeValueFromSelectMultiple(fieldId, "bundle-1");

    expect(document.getElementById(fieldId).value).toBe("bundle-1");
    expect(document.getElementById("remove-bundle-1").disabled).toBe(true);
});

test("template actions use the delegated data-action handler", () => {
    const fixture = path.join(__dirname, "fixtures", "select_multiple_required_bundle.html");
    document.body.innerHTML = fs.readFileSync(fixture, "utf8");
    const fieldId = "EdgeUsagePattern_edge_usage_journeys";
    refreshSelectMultipleFields(fieldId);
    const addButton = document.getElementById(`add-btn-${fieldId}`);

    expect(addButton.getAttribute("onclick")).toBeNull();
    addButton.click();

    expect(document.getElementById(fieldId).value).toBe("bundle-1;bundle-2");
    expect(document.querySelector("[data-action='remove-select-multiple']").getAttribute("onclick")).toBeNull();
});

test("late HTMX initialization preserves a selection already made by the user", () => {
    const fixture = path.join(__dirname, "fixtures", "select_multiple_required_bundle.html");
    document.body.innerHTML = fs.readFileSync(fixture, "utf8");
    const fieldId = "EdgeUsagePattern_edge_usage_journeys";
    const select = document.getElementById(`select-new-object-${fieldId}`);
    select.value = "bundle-2";

    document.getElementById(`selected_data_${fieldId}`).dispatchEvent(
        new CustomEvent("htmx:load", {bubbles: true})
    );

    expect(select.value).toBe("bundle-2");
});

test("renders selected labels as text, never markup", () => {
    const fixture = path.join(__dirname, "fixtures", "select_multiple_untrusted_label.html");
    document.body.innerHTML = fs.readFileSync(fixture, "utf8");

    refreshSelectMultipleFields("Test_values");

    expect(document.querySelector("#objects-already-selected-for-Test_values img")).toBeNull();
    expect(document.querySelector("#objects-already-selected-for-Test_values td").textContent)
        .toBe('<img src=x onerror="alert(1)">');
});
