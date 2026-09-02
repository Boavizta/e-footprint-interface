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
