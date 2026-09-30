const fs = require("fs");
const path = require("path");

// Match base.html: field initialization and bookmark handlers precede the workspace guard.
require("../theme/static/scripts/dynamic_forms.js");
require("../theme/static/scripts/simplified_inputs.js");
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

function finishBookmarkRequest(bookmark, fields, inverse = {}, successful = true) {
    const xhr = {getResponseHeader: () => null, responseText: JSON.stringify({fields, inverse: {fields: inverse}})};
    dispatch("htmx:beforeRequest", {xhr, elt: bookmark, requestConfig: {verb: "post"}});
    expect(bookmark.querySelector("[data-bookmark-status]").textContent).toBe("Saving…");
    dispatch("htmx:beforeSwap", {xhr, shouldSwap: true});
    dispatch("htmx:afterRequest", {xhr, elt: bookmark, successful});
    dispatch("htmx:afterSettle", {xhr, elt: document.body});
    expect(document.body.dataset.workspaceMutation).toBeUndefined();
}

function field(attribute, included, requiredBy = null, help = "Old saved help") {
    return {object_id: "api", attribute, setting: {included, help}, required_by: requiredBy};
}

test("saved companion locks remain authoritative after the workspace guard restores controls", () => {
    mount("simplified_bookmarks");
    const provider = document.querySelector('[data-attribute="provider"]');
    const model = document.querySelector('[data-attribute="model_name"] [data-include-input]');
    for (const included of [true, false]) {
        include(provider, included);
        finishBookmarkRequest(provider, [field("provider", included),
            field("model_name", true, included ? {label: "API Provider"} : null)]);
        expect({checked: model.checked, disabled: model.disabled}).toEqual({checked: true, disabled: included});
        expect(provider.querySelector("summary").title).toBe(`${included ? "Included" : "Not included"} in Simplified inputs. Open settings.`);
        expect(model.closest("[data-bookmark]").querySelector("summary").title).toBe(
            `Included in Simplified inputs.${included ? " Required by API Provider." : ""} Open settings.`);
    }
});

test("a failed help draft survives same-bookmark membership and Undo until its own save succeeds", () => {
    mount("simplified_bookmarks");
    const bookmark = document.querySelector('[data-attribute="provider"]');
    const help = bookmark.querySelector("textarea");
    const status = bookmark.querySelector("[data-bookmark-status]");
    help.value = "Help to retry";
    help.dispatchEvent(new Event("change", {bubbles: true}));
    finishBookmarkRequest(bookmark, [], {}, false);
    include(bookmark, true);
    finishBookmarkRequest(bookmark, [field("provider", true)], {api: {provider: {included: false}}});
    expect({help: help.value, savedHelp: help.defaultValue, status: status.textContent}).toEqual({
        help: "Help to retry", savedHelp: "Old saved help", status: "Not saved"});
    bookmark.querySelector('[data-action="bookmark-undo"]').click();
    expect(JSON.parse(bookmark.dataset.pendingPatch)).toEqual({fields: {api: {provider: {included: false}}}});
    finishBookmarkRequest(bookmark, [field("provider", false)]);
    expect({help: help.value, savedHelp: help.defaultValue, status: status.textContent}).toEqual({
        help: "Help to retry", savedHelp: "Old saved help", status: "Not saved"});
    help.value = "Retried help";
    help.dispatchEvent(new Event("change", {bubbles: true}));
    finishBookmarkRequest(bookmark, [field("provider", false, null, "Retried help")]);
    expect({help: help.value, savedHelp: help.defaultValue, status: status.textContent}).toEqual({
        help: "Retried help", savedHelp: "Retried help", status: "Saved"});
});
