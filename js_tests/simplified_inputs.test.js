const fs = require("fs");
const path = require("path");
if (typeof global.CSS === "undefined") {
    global.CSS = {escape: value => String(value).replace(/[^a-zA-Z0-9_-]/g, char => "\\" + char)};
}
const { refreshSelection, refreshFilter, definitionFromForm } = require("../theme/static/scripts/simplified_inputs/configuration.js");
const { workspace: { initialize, deferExit } } = require("../theme/static/scripts/simplified_inputs/index.js");
require("../theme/static/scripts/source_metadata.js");
require("../theme/static/scripts/model_builder_main.js");

function mount(fixture = "simplified_configure") {
    document.body.innerHTML = fs.readFileSync(path.join(__dirname, `fixtures/${fixture}.html`), "utf8");
    const workspace = document.querySelector("[data-simplified-workspace]");
    const target = document.createElement("div");
    target.dataset.simplifiedTarget = "0";
    target.dataset.systemId = "test";
    workspace.replaceWith(target);
    target.appendChild(workspace);
    const dialog = document.querySelector("dialog");
    dialog.showModal = jest.fn();
    dialog.close = jest.fn();
    Element.prototype.scrollIntoView = jest.fn();
    window.runAfterSidePanelDiscardConfirmation = action => action();
    window.closeAndEmptySidePanel = jest.fn();
    window.htmx = { ajax: jest.fn(() => Promise.resolve()) };
    window.confirm = jest.fn(() => true);
    initialize();
    return workspace;
}
function include(attribute, checked = true) {
    const input = document.querySelector(`[data-attribute="${attribute}"] [data-include-input]`);
    input.checked = checked;
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return input;
}

test("recursive companions lock across owners and unlock without removing saved help", () => {
    mount();
    include("provider");
    const model = document.querySelector('[data-attribute="model"] [data-include-input]');
    const count = document.querySelector('[data-attribute="count"] [data-include-input]');
    expect(model.checked).toBe(true);
    expect(count.checked).toBe(true);
    expect(model.disabled).toBe(true);
    expect(count.disabled).toBe(true);
    expect(definitionFromForm(document.querySelector("form"))).toEqual({
        title: "Title", guidance: "Guidance", fields: {
            api: { provider: { included: true, help: "Retained Help" }, model: { included: true, help: "Retained Help" } },
            job: { count: { included: true, help: "Retained Help" } },
            other: { lifespan: { included: false, help: "Retained Help" } },
        },
    });
    include("provider", false);
    expect(model.disabled).toBe(false);
    expect(model.checked).toBe(true);
    expect(document.querySelector('[data-attribute="provider"] textarea').value).toBe("Retained Help");
});

test("filter changes navigation and content only and restores focus when last inclusion disappears", () => {
    const workspace = mount();
    const input = include("lifespan");
    const filter = workspace.querySelector("[data-selected-object-filter]");
    filter.checked = true;
    refreshFilter(workspace);
    expect(workspace.querySelector('[data-owner-id="api"][data-simplified-object]').hidden).toBe(true);
    expect(workspace.querySelector('[data-navigation-object="si-test-object-api"]').hidden).toBe(true);
    input.focus();
    include("lifespan", false);
    expect(document.activeElement).toBe(filter);
    expect(workspace.querySelector("[data-filter-empty]").hidden).toBe(false);
    expect(workspace.querySelector('[data-attribute="lifespan"] textarea').value).toBe("Retained Help");
});

test("Clear confirmation removes field settings but preserves title and guidance", () => {
    mount();
    include("provider");
    window.confirm.mockReturnValueOnce(false);
    document.querySelector('[data-action="simplified-clear"]').click();
    expect(document.querySelector('[data-attribute="provider"] [data-include-input]').checked).toBe(true);
    document.querySelector('[data-action="simplified-clear"]').click();
    expect([...document.querySelectorAll("[data-include-input]")].every(input => !input.checked)).toBe(true);
    expect([...document.querySelectorAll("[data-field-help]")].every(input => input.value === "")).toBe(true);
    expect(document.querySelector('[name="title"]').value).toBe("Title");
    expect(document.querySelector('[name="guidance"]').value).toBe("Guidance");
    expect(definitionFromForm(document.querySelector("form"))).toEqual({ title: "Title", guidance: "Guidance", fields: {} });
});

test("compact object navigation does not author a configuration change", () => {
    const workspace = mount();
    const selector = workspace.querySelector("[data-object-selector]");
    selector.value = "si-test-object-job";
    selector.dispatchEvent(new Event("input", { bubbles: true }));
    selector.dispatchEvent(new Event("change", { bubbles: true }));
    expect(workspace.querySelector("form").dataset.dirty).toBeUndefined();
    expect(document.activeElement).toBe(workspace.querySelector("#si-test-object-job summary"));
});

test("configuration transport is one snapshot taken when HTMX sends the form", () => {
    const workspace = mount();
    const form = workspace.querySelector("form");
    include("provider");
    form.elements.title.value = "Latest title";
    const parameters = { csrfmiddlewaretoken: "token" };
    form.dispatchEvent(new CustomEvent("htmx:configRequest", { bubbles: true, detail: { elt: form, parameters } }));
    expect(Object.keys(parameters)).toEqual(["csrfmiddlewaretoken", "definition"]);
    expect(JSON.parse(parameters.definition)).toEqual(definitionFromForm(form));
    expect(form.getAttribute("hx-params")).toBe("csrfmiddlewaretoken");
});

test("duplicate pending reads are suppressed and failed reads can be retried", () => {
    mount();
    deferExit(() => {});
    deferExit(() => {});
    expect(window.htmx.ajax).toHaveBeenCalledTimes(1);
    const target = document.querySelector("[data-simplified-target]");
    const xhr = { abort: jest.fn() };
    target.dispatchEvent(new CustomEvent("htmx:beforeRequest", { detail: { elt: target, xhr } }));
    target.dispatchEvent(new CustomEvent("htmx:afterRequest", { detail: { xhr, successful: false } }));
    deferExit(() => {});
    expect(window.htmx.ajax).toHaveBeenCalledTimes(2);
});

test("Stay keeps the draft and Save resumes an exit only after its successful response settles", () => {
    mount();
    include("lifespan");
    const action = jest.fn();
    deferExit(action);
    expect(document.querySelector("dialog").showModal).toHaveBeenCalled();
    document.querySelector('[data-action="simplified-exit-stay"]').click();
    expect(action).not.toHaveBeenCalled();
    const form = document.querySelector("form");
    form.requestSubmit = jest.fn();
    deferExit(action);
    document.querySelector('[data-action="simplified-exit-save"]').click();
    expect(form.requestSubmit).toHaveBeenCalled();
    finishMutation(startMutation(form), false);
    expect(action).not.toHaveBeenCalled();
    expect(form.dataset.dirty).toBe("true");
    deferExit(action);
    const xhr = startMutation(form);
    mutationEvent("htmx:beforeSwap", {xhr, shouldSwap: true});
    mutationEvent("htmx:afterRequest", {xhr, successful: true});
    mutationEvent("htmx:afterSettle", {xhr: {}});
    expect(action).not.toHaveBeenCalled();
    mutationEvent("htmx:afterSettle", {xhr});
    expect(action).toHaveBeenCalledTimes(1);
});

test("internal saved-view reads bypass exit interception, using the resident settlement source", async () => {
    mount();
    const target = document.querySelector("[data-simplified-target]");
    const issueRequest = jest.fn();
    const event = new CustomEvent("htmx:confirm", { bubbles: true, cancelable: true,
        detail: { elt: target, issueRequest } });
    target.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
    const action = jest.fn();
    deferExit(action);
    await Promise.resolve();
    expect(action).not.toHaveBeenCalled();
    const xhr = {};
    target.dispatchEvent(new CustomEvent("htmx:beforeRequest", { detail: { elt: target, xhr } }));
    target.dispatchEvent(new CustomEvent("htmx:afterSettle", { detail: { xhr: {} } }));
    expect(action).not.toHaveBeenCalled();
    target.dispatchEvent(new CustomEvent("htmx:afterSettle", { detail: { xhr } }));
    expect(window.htmx.ajax).toHaveBeenCalledWith("GET", "/model_builder/simplified-inputs/",
        expect.objectContaining({ source: target, target }));
    expect(action).toHaveBeenCalled();
});

function bookmark(owner, attribute, provisional = false) {
    const fixture = document.createElement("div");
    fixture.innerHTML = fs.readFileSync(path.join(__dirname, "fixtures/simplified_bookmark_empty.html"), "utf8");
    const element = fixture.querySelector("[data-bookmark]");
    element.dataset.ownerId = owner;
    element.dataset.attribute = attribute;
    element.dataset.pendingPatch = JSON.stringify({fields: {[owner]: {[attribute]: {included: true}}}});
    if (provisional) {
        element.dataset.provisionalOwner = owner;
        element.dataset.inputId = `Job_${attribute}`;
    }
    return element;
}
function bookmarkResponse(element, result, failed = false) {
    document.body.dispatchEvent(new CustomEvent("htmx:afterRequest", {bubbles: true, detail: {
        elt: element, successful: !failed, xhr: {responseText: JSON.stringify(result),
            status: failed ? 422 : 200}
    }}));
}

test("inline settings payload excludes the surrounding value draft and failed saves preserve controls", () => {
    mount().remove();
    window.htmx.trigger = jest.fn();
    const form = document.createElement("form");
    form.innerHTML = '<input name="Storage_storage_capacity" value="9999">';
    const element = bookmark("storage", "storage_capacity");
    form.appendChild(element);
    document.body.appendChild(form);
    element.querySelector("[data-include-input]").checked = true;
    element.querySelector("[data-include-input]").dispatchEvent(new Event("change", {bubbles: true}));
    const parameters = {};
    document.body.dispatchEvent(new CustomEvent("htmx:configRequest", {detail: {elt: element, parameters}}));
    expect(JSON.parse(parameters.patch)).toEqual({fields: {storage: {storage_capacity: {included: true}}}});
    expect(Object.keys(parameters)).toEqual(["patch"]);
    bookmarkResponse(element, {}, true);
    expect(form.querySelector("[name]").value).toBe("9999");
    expect(element.querySelector("[data-include-input]").checked).toBe(true);
    expect(element.querySelector("[data-bookmark-status]").textContent).toBe("Not saved");
});

test("bookmark success updates visible membership only, preserves independent help draft and offers inverse Undo", () => {
    mount().remove();
    window.htmx.trigger = jest.fn();
    const first = bookmark("storage", "storage_capacity");
    const second = bookmark("storage", "storage_capacity");
    second.querySelector("textarea").value = "Unsaved help";
    document.body.append(first, second);
    const inverse = {fields: {storage: {storage_capacity: {included: false}}}};
    bookmarkResponse(first, {fields: [{object_id: "storage", attribute: "storage_capacity",
        setting: {included: true, help: ""}, required_by: null}], inverse});
    expect(first.querySelector("[data-include-input]").checked).toBe(true);
    expect(second.querySelector("[data-include-input]").checked).toBe(true);
    expect(second.querySelector("textarea").value).toBe("Unsaved help");
    expect(first.querySelector("button").hidden).toBe(false);
    first.querySelector("button").click();
    expect(JSON.parse(first.dataset.pendingPatch)).toEqual(inverse);
    expect(window.htmx.trigger).toHaveBeenCalledWith(first, "bookmark-save");
});

test("creation requirements follow candidates, release forced membership and retain help", () => {
    mount();
    const {refreshCreationBookmarks, pendingCreationSettings} = require("../theme/static/scripts/simplified_inputs/bookmarks.js");
    const form = document.createElement("form");
    form.id = "sidePanelForm";
    form.innerHTML = '<select id="service_or_external_api"><option value="a">A</option><option value="b">B</option></select>';
    const resolution = bookmark("object", "resolution", true);
    form.appendChild(resolution);
    const panel = document.createElement("div");
    panel.id = "sidePanelContent";
    panel.appendChild(form);
    document.body.appendChild(panel);
    const script = document.createElement("script");
    script.id = "dynamic-form-data";
    script.type = "application/json";
    script.textContent = JSON.stringify({dynamic_lists: [{input_id: "Job_resolution", filter_by: "service_or_external_api",
        simplified_required_by: {a: {label: "Video API A · Model"}, b: null}}]});
    document.body.appendChild(script);
    resolution.querySelector("textarea").value = "Retained help";
    refreshCreationBookmarks();
    expect(resolution.querySelector("[data-include-input]").checked).toBe(true);
    expect(resolution.querySelector("[data-include-input]").disabled).toBe(true);
    expect(resolution.querySelector("textarea").disabled).toBe(false);
    form.querySelector("select").value = "b";
    refreshCreationBookmarks();
    expect(resolution.querySelector("[data-include-input]").checked).toBe(false);
    expect(resolution.querySelector("[data-include-input]").disabled).toBe(false);
    expect(pendingCreationSettings(form)).toEqual([{owner: "object", attribute: "resolution", included: false, help: "Retained help"}]);
    const parameters = {};
    document.body.dispatchEvent(new CustomEvent("htmx:configRequest", {detail: {elt: form, parameters}}));
    expect(JSON.parse(parameters.simplified_settings)).toEqual(pendingCreationSettings(form));
});

function mountEditor(fixture = "simplified_editor") {
    mount();
    const workspace = document.querySelector('[data-simplified-workspace]');
    const group = workspace.querySelector('[data-simplified-group]').cloneNode(false);
    const object = workspace.querySelector('[data-simplified-object]').cloneNode(false);
    object.innerHTML = fs.readFileSync(path.join(__dirname, `fixtures/${fixture}.html`), 'utf8');
    group.appendChild(object);
    workspace.replaceChildren(group);
    return document.querySelector('[data-simplified-editor]');
}

test('simplified provenance follows the side-panel field layout', () => {
    const form = mountEditor();
    const row = form.querySelector('.simplified-input-row');
    expect(row.querySelector('.simplified-input-control input[type="number"]')).not.toBeNull();
    expect(row.querySelector(':scope > .confidence-wrap')).not.toBeNull();
    expect(form.querySelector('.source-comment')).toBe(row.nextElementSibling);
    expect(form.querySelector('.source-line[data-action="open-source-editor"]')).not.toBeNull();
    expect(form.querySelector('details.simplified-provenance')).toBeNull();
    expect(form.querySelector('[data-simplified-save-status]').textContent).toBe('');
});

test('a saved field fragment carries its server-rendered outcome', () => {
    const status = mountEditor('simplified_editor_saved').querySelector('[data-simplified-save-status]');
    expect(status.id).toBe('si-test-server-lifespan-save-status');
    expect(status.dataset.outcome).toBe('saved');
    expect(status.textContent).toBe('Saved');
    expect(status.hasAttribute('hx-preserve')).toBe(false);
});

function mutationEvent(name, detail, target = document.body) {
    target.dispatchEvent(new CustomEvent(name, {bubbles: true, detail}));
}
function startMutation(form) {
    const xhr = {getResponseHeader: () => null};
    mutationEvent("htmx:beforeRequest", {xhr, elt: form, requestConfig: {verb: "post"}});
    return xhr;
}
function finishMutation(xhr, successful = true) {
    mutationEvent("htmx:beforeSwap", {xhr, shouldSwap: false});
    mutationEvent("htmx:afterRequest", {xhr, successful});
}
function activate(control) {
    const event = new MouseEvent("click", {bubbles: true, cancelable: true});
    control.dispatchEvent(event);
    return event;
}
const CONFIGURE_EXPORT_FIXTURES = [
    ["simplified_configure_export", "download-model"],
    ["simplified_configure_workspace", "download-menu-toggle"],
    ["simplified_configure_workspace", "download-model"],
    ["simplified_configure_workspace", "download-workspace"],
];
test.each(CONFIGURE_EXPORT_FIXTURES)("%s %s exports from clean Configure without reads or exits", (fixture, id) => {
    const workspace = mount(fixture);
    const form = workspace.querySelector("[data-configure-form]");
    form.requestSubmit = jest.fn();
    const control = document.getElementById(id);
    const captured = jest.fn();
    document.addEventListener("click", captured, {capture: true, once: true});
    expect(activate(control.querySelector("i") || control).defaultPrevented).toBe(false);
    expect(captured).toHaveBeenCalledTimes(1);
    expect(form.isConnected).toBe(true);
    expect(window.htmx.ajax).not.toHaveBeenCalled();
    expect(form.requestSubmit).not.toHaveBeenCalled();
    expect(document.querySelector("dialog").showModal).not.toHaveBeenCalled();
});

test.each(CONFIGURE_EXPORT_FIXTURES)("%s %s blocks dirty Configure before document capture and writes its notice", (fixture, id) => {
    const workspace = mount(fixture);
    include("lifespan");
    const form = workspace.querySelector("form");
    form.requestSubmit = jest.fn();
    const control = document.getElementById(id);
    const captured = jest.fn();
    document.addEventListener("click", captured, true);
    try {
        expect(activate(control.querySelector("i") || control).defaultPrevented).toBe(true);
        const notice = workspace.querySelector("[data-simplified-notice]");
        expect(activate(control).defaultPrevented).toBe(true);
        expect(workspace.querySelector("[data-simplified-notice]")).toBe(notice);
        const notices = workspace.querySelectorAll("[data-simplified-notice]");
        expect(notices).toHaveLength(1);
        expect(notices[0].getAttribute("role")).toBe("status");
        expect(notices[0].previousElementSibling).toBe(workspace.querySelector(".simplified-header"));
        expect(notices[0].textContent).toBe("Save or discard Configure changes before exporting.");
        expect(captured).not.toHaveBeenCalled();
        expect(window.htmx.ajax).not.toHaveBeenCalled();
        expect(form.requestSubmit).not.toHaveBeenCalled();
        expect(document.querySelector("dialog").showModal).not.toHaveBeenCalled();
        expect(form.dataset.dirty).toBe("true");
    } finally {
        document.removeEventListener("click", captured, true);
    }
});

test.each(["save", "discard", "failed save"])("%s resolves Configure explicitly without continuing an export", async resolution => {
    const workspace = mount("simplified_configure_workspace");
    include("lifespan");
    const form = workspace.querySelector("form");
    const control = document.getElementById("download-menu-toggle");
    const activated = jest.fn();
    control.addEventListener("click", activated);
    const replaceWorkspace = () => {
        const template = document.createElement("template");
        template.innerHTML = fs.readFileSync(path.join(__dirname, "fixtures/simplified_saved.html"), "utf8");
        workspace.replaceWith(template.content.querySelector("[data-simplified-workspace]"));
    };
    expect(activate(control).defaultPrevented).toBe(true);
    if (resolution === "discard") {
        document.querySelector('[data-action="simplified-cancel"]').click();
        expect(document.querySelector("dialog").showModal).toHaveBeenCalledTimes(1);
        document.querySelector('[data-action="simplified-exit-discard"]').click();
        const target = document.querySelector("[data-simplified-target]");
        const xhr = {};
        mutationEvent("htmx:beforeRequest", {elt: target, xhr}, target);
        replaceWorkspace();
        mutationEvent("htmx:afterSettle", {xhr}, target);
    } else {
        const save = form.querySelector('button[type="submit"]');
        form.requestSubmit = jest.fn();
        expect(activate(save).defaultPrevented).toBe(false);
        const xhr = startMutation(form);
        if (resolution === "save") replaceWorkspace();
        finishMutation(xhr, resolution === "save");
    }
    await Promise.resolve();
    expect(activated).not.toHaveBeenCalled();
    if (resolution === "failed save") {
        expect(form.dataset.dirty).toBe("true");
        expect(workspace.querySelector("[data-simplified-notice]").textContent).toBe(
            "Save or discard Configure changes before exporting.");
        expect(activate(control).defaultPrevented).toBe(true);
    } else {
        expect(workspace.isConnected).toBe(false);
        expect(document.querySelector("[data-simplified-notice]").textContent).toBe("");
        expect(activate(control).defaultPrevented).toBe(false);
        expect(activated).toHaveBeenCalledTimes(1);
    }
});

test("clean Configure export does not cancel a pending saved-view read", () => {
    mount("simplified_configure_export");
    deferExit(() => {});
    const target = document.querySelector("[data-simplified-target]");
    const xhr = {abort: jest.fn()};
    mutationEvent("htmx:beforeRequest", {elt: target, xhr}, target);
    expect(activate(document.getElementById("download-model")).defaultPrevented).toBe(false);
    expect(xhr.abort).not.toHaveBeenCalled();
    mutationEvent("htmx:afterRequest", {xhr, successful: false}, target);
});
