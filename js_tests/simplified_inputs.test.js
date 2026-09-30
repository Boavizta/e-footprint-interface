const fs = require("fs");
const path = require("path");
const { refreshSelection, refreshFilter, initialize, deferExit, definitionFromForm } = require("../theme/static/scripts/simplified_inputs.js");

function mount() {
    document.body.innerHTML = fs.readFileSync(path.join(__dirname, "fixtures/simplified_configure.html"), "utf8");
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
    delete document.body.dataset.workspaceMutation;
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

test("Stay keeps the draft and Save resumes an exit only after successful mutation settlement", () => {
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
    document.body.dispatchEvent(new CustomEvent("workspace-mutation:started", { detail: { elt: form } }));
    document.body.dispatchEvent(new CustomEvent("workspace-mutation:finished", { detail: { elt: form, successful: false } }));
    expect(action).not.toHaveBeenCalled();
    expect(form.dataset.dirty).toBe("true");
    deferExit(action);
    document.body.dispatchEvent(new CustomEvent("workspace-mutation:started", { detail: { elt: form } }));
    document.body.dispatchEvent(new CustomEvent("workspace-mutation:finished", { detail: { elt: form, successful: true } }));
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
        elt: element, successful: true, xhr: {responseText: JSON.stringify(result),
            getResponseHeader: () => failed ? "openModalDialog" : null}
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
    const {refreshCreationBookmarks, pendingCreationSettings} = require("../theme/static/scripts/simplified_inputs.js");
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

function mountEditor() {
    mount();
    document.querySelector('[data-simplified-workspace]').innerHTML = fs.readFileSync(path.join(__dirname, 'fixtures/simplified_editor.html'), 'utf8');
    window.htmx.trigger = jest.fn();
    require('../theme/static/scripts/simplified_inputs.js').initializeEdits();
    return document.querySelector('[data-simplified-editor]');
}

test('Enter followed by blur saves once and failure keeps draft retryable with accepted totals', () => {
    const form = mountEditor();
    const input = form.querySelector('input');
    input.value = '8';
    input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
    input.dispatchEvent(new FocusEvent('focusout', {bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledTimes(1);
    document.body.dispatchEvent(new CustomEvent('workspace-mutation:finished', {
        detail: {elt: form, successful: false},
    }));
    expect(input.value).toBe('8');
    expect(form.querySelector('[data-simplified-save-status]').textContent).toBe('Not saved');
    expect([...document.querySelectorAll('[data-quick-total]')].map(item => item.textContent)).toEqual(['20 kg', '20 kg']);
    form.querySelector('[data-action="simplified-retry"]').click();
    expect(window.htmx.trigger).toHaveBeenCalledTimes(2);
});

test('unchanged blur does not save and an in-flight workspace mutation rejects new saves', () => {
    const form = mountEditor();
    const input = form.querySelector('input');
    input.dispatchEvent(new FocusEvent('focusout', {bubbles: true}));
    expect(window.htmx.trigger).not.toHaveBeenCalled();
    document.body.dataset.workspaceMutation = 'updating';
    input.value = '9';
    input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
    expect(window.htmx.trigger).not.toHaveBeenCalled();
});

test("value saves omit unchanged provenance and confidence saves preserve omitted source and comment", () => {
    const form = mountEditor();
    const parameters = Object.fromEntries(new FormData(form));
    const prefix = form.dataset.valuePrefix;
    parameters[prefix] = "8";
    parameters[prefix + "__confidence"] = "high";
    document.body.dispatchEvent(new CustomEvent("htmx:configRequest", {detail: {elt: form, parameters}}));
    expect(parameters[prefix + "__confidence"]).toBe("high");
    expect(parameters[prefix + "__comment"]).toBeUndefined();
    expect(parameters[prefix + "__source_id"]).toBeUndefined();
    expect(parameters[prefix + "__source_name"]).toBeUndefined();
    expect(parameters[prefix + "__source_link"]).toBeUndefined();
});

test("accepted replacement baselines wait for the workspace guard to restore form controls", () => {
    const form = mountEditor();
    // Match base.html: the simplified module registers its settlement listener before the guard.
    require("../theme/static/scripts/model_builder_main.js");
    const xhr = {getResponseHeader: () => ""};
    const emit = (name, detail) => document.body.dispatchEvent(new CustomEvent(name, {detail}));
    form.querySelector("input").value = "8";
    form.querySelector("input").dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledTimes(1);
    emit("htmx:beforeRequest", {xhr, elt: form, requestConfig: {verb: "post"}});
    expect(form.querySelector("input").disabled).toBe(true);
    emit("htmx:beforeSwap", {xhr, shouldSwap: true});
    const fragment = document.createElement("template");
    fragment.innerHTML = fs.readFileSync(path.join(__dirname, "fixtures/simplified_editor.html"), "utf8");
    const replacement = fragment.content.querySelector("form");
    replacement.querySelector("input").value = "8";
    form.replaceWith(replacement);
    emit("htmx:afterSwap", {xhr, elt: replacement});
    expect(replacement.querySelector("input").disabled).toBe(true);
    emit("htmx:afterRequest", {xhr, successful: true});
    emit("htmx:afterSettle", {xhr, elt: replacement});
    expect(replacement.querySelector("input").disabled).toBe(false);

    const input = replacement.querySelector("input");
    input.dispatchEvent(new FocusEvent("focusout", {bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledTimes(1);
    const parameters = Object.fromEntries(new FormData(replacement));
    emit("htmx:configRequest", {elt: replacement, parameters});
    expect(parameters).toEqual({[replacement.dataset.valuePrefix]: "8",
        [replacement.dataset.valuePrefix + "__unit"]: "year"});
    input.value = "9";
    input.dispatchEvent(new FocusEvent("focusout", {bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledTimes(2);
});
