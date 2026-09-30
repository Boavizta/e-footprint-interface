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
