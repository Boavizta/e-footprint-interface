const fs = require("fs");
const path = require("path");

// Match base.html: field initialization and bookmark handlers precede native-state restoration.
require("../theme/static/scripts/dynamic_forms.js");
require("../theme/static/scripts/simplified_inputs/index.js");
require("../theme/static/scripts/model_builder_main.js");

function mount(name) {
    document.body.innerHTML = fs.readFileSync(path.join(__dirname, "fixtures", `${name}.html`), "utf8");
    window.htmx = {trigger: jest.fn()};
    window.tagFormAsModified = jest.fn();
    Element.prototype.scrollIntoView = jest.fn();
}

function dispatch(type, detail) {
    document.body.dispatchEvent(new CustomEvent(type, {bubbles: true, cancelable: true, detail}));
}

function include(bookmark, included) {
    const checkbox = bookmark.querySelector("[data-include-input]");
    checkbox.checked = included;
    checkbox.dispatchEvent(new Event("change", {bubbles: true}));
}

test("bookmark checkbox names its simplified-input destination", () => {
    mount("simplified_bookmarks");
    const checkbox = document.querySelector('[data-bookmark] [data-include-input]');
    expect(checkbox.closest("label").textContent.trim()).toBe("Include in simplified inputs");
    mount("simplified_configure");
    const configureCheckbox = document.querySelector('[data-simplified-workspace] [data-include-input]');
    expect(configureCheckbox.closest("label").textContent.trim()).toBe("Include");
});

test.each([
    ["simplified_create_server", "Server", "Storage", "storage_capacity"],
    ["simplified_create_edge_device", "EdgeComputer", "EdgeStorage", "storage_capacity_per_unit"],
])("%s submits the main and sibling Storage drafts from the composite panel", (fixture, objectType, storageType, capacity) => {
    mount(fixture);
    const visibilityScript = [...document.querySelectorAll("script")]
        .find(script => script.textContent.includes("function updateStorageFormVisibility"));
    if (visibilityScript) window.eval(visibilityScript.textContent);
    document.dispatchEvent(new Event("initDynamicForm"));
    const selector = document.getElementById("type_object_available");
    selector.value = objectType;
    selector.dispatchEvent(new Event("change", {bubbles: true}));
    const main = document.querySelector(`#field-group-${objectType}_lifespan [data-bookmark]`);
    const storage = document.querySelector(`#field-group-${storageType}_${capacity} [data-bookmark]`);
    include(main, true);
    include(storage, true);
    storage.querySelector("textarea").value = "Nested storage help";
    const settings = () => {
        const parameters = {};
        dispatch("htmx:configRequest", {elt: document.getElementById("sidePanelForm"), parameters});
        return JSON.parse(parameters.simplified_settings);
    };
    const expected = [
        {owner: "object", attribute: "lifespan", included: true, help: ""},
        {owner: "storage", attribute: capacity, included: true, help: "Nested storage help"},
    ];
    expect(settings()).toEqual(expected);
    if (objectType === "EdgeComputer") {
        selector.value = "EdgeAppliance";
        selector.dispatchEvent(new Event("change", {bubbles: true}));
        expect(settings()).toEqual([]);
        selector.value = objectType;
        selector.dispatchEvent(new Event("change", {bubbles: true}));
        expect(settings()).toEqual(expected);
    }
});
