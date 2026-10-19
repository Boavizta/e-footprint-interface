const fs = require("fs");
const path = require("path");
if (typeof global.CSS === "undefined") {
    global.CSS = {escape: value => String(value).replace(/[^a-zA-Z0-9_-]/g, char => "\\" + char)};
}
const { refreshSelection, refreshFilter, definitionFromForm } = require("../theme/static/scripts/simplified_inputs/configuration.js");
const { workspace: { initialize } } = require("../theme/static/scripts/simplified_inputs/index.js");
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

function toolbarControl(html = '<button type="button" data-action="simplified-mode" data-workspace-control>Simplified inputs</button>') {
    const holder = document.createElement("div");
    holder.innerHTML = html;
    const control = holder.firstElementChild;
    document.body.prepend(control);
    return control;
}
function confirmRequest(elt) {
    const issueRequest = jest.fn();
    const event = new CustomEvent("htmx:confirm", {bubbles: true, cancelable: true, detail: {elt, issueRequest}});
    elt.dispatchEvent(event);
    return {event, issueRequest};
}

test("entering Simplified inputs switches the view before any response and sends one replaceable read", () => {
    mount().remove();
    const target = document.querySelector("[data-simplified-target]");
    expect(document.body.dataset.baseView).toBe("modeling");
    toolbarControl().click();
    expect(document.body.dataset.baseView).toBe("simplified");
    expect(target.dataset.view).toBe("simplified");
    expect(target.classList.contains("d-none")).toBe(false);
    expect(window.closeAndEmptySidePanel).toHaveBeenCalledTimes(1);
    expect(window.htmx.ajax).toHaveBeenCalledTimes(1);
    expect(window.htmx.ajax).toHaveBeenCalledWith("GET", "/model_builder/simplified-inputs/",
        {source: target, target, swap: "innerHTML"});
});

test("a dirty Configure blocks toolbar clicks and HTMX requests behind the dialog without issuing them", () => {
    mount();
    include("lifespan");
    const control = toolbarControl();
    const reached = jest.fn();
    control.addEventListener("click", reached);
    expect(activate(control).defaultPrevented).toBe(true);
    expect(reached).not.toHaveBeenCalled();
    const link = toolbarControl('<a href="#" hx-get="/model_builder/compare/">Compare</a>');
    const {event, issueRequest} = confirmRequest(link);
    expect(event.defaultPrevented).toBe(true);
    expect(issueRequest).not.toHaveBeenCalled();
    expect(document.querySelector("dialog").showModal).toHaveBeenCalledTimes(2);
    expect(window.htmx.ajax).not.toHaveBeenCalled();
});

test("Save submits, Discard reads the saved view once, Stay issues nothing, and none replays the exit", () => {
    mount();
    include("lifespan");
    const form = document.querySelector("[data-configure-form]");
    form.requestSubmit = jest.fn();
    const control = toolbarControl();
    const reached = jest.fn();
    control.addEventListener("click", reached);
    const target = document.querySelector("[data-simplified-target]");
    activate(control);
    document.querySelector('[data-action="simplified-exit-stay"]').click();
    expect(form.requestSubmit).not.toHaveBeenCalled();
    expect(window.htmx.ajax).not.toHaveBeenCalled();
    activate(control);
    document.querySelector('[data-action="simplified-exit-save"]').click();
    expect(form.requestSubmit).toHaveBeenCalledTimes(1);
    expect(window.htmx.ajax).not.toHaveBeenCalled();
    activate(control);
    document.querySelector('[data-action="simplified-exit-discard"]').click();
    expect(window.htmx.ajax).toHaveBeenCalledTimes(1);
    expect(window.htmx.ajax).toHaveBeenCalledWith("GET", "/model_builder/simplified-inputs/",
        expect.objectContaining({source: target, target}));
    expect(document.querySelector("dialog").close).toHaveBeenCalledTimes(3);
    expect(reached).not.toHaveBeenCalled();
    expect(form.requestSubmit).toHaveBeenCalledTimes(1);
});

test("a clean Configure exit is not intercepted", () => {
    mount();
    const link = toolbarControl('<a href="#" hx-get="/model_builder/compare/">Compare</a>');
    const reached = jest.fn(event => event.preventDefault());
    link.addEventListener("click", reached);
    activate(link);
    expect(reached).toHaveBeenCalledTimes(1);
    expect(confirmRequest(link).event.defaultPrevented).toBe(false);
    expect(document.querySelector("dialog").showModal).not.toHaveBeenCalled();
    expect(window.htmx.ajax).not.toHaveBeenCalled();
});

test("each slot restores its own view and an empty Simplified slot is never re-read", () => {
    const workspace = mount();
    const first = document.querySelector("[data-simplified-target]");
    const second = document.createElement("div");
    second.dataset.simplifiedTarget = "1";
    second.dataset.view = "simplified";
    first.after(second);
    const strip = document.createElement("div");
    strip.id = "model-tab-strip";
    strip.dataset.activeSlot = "0";
    document.body.prepend(strip);
    const toggle = toolbarControl();
    first.dataset.view = "simplified";
    initialize();
    expect(document.body.dataset.baseView).toBe("simplified");
    expect(first.classList.contains("d-none")).toBe(false);
    toggle.click();
    expect(first.dataset.view).toBe("modeling");
    strip.dataset.activeSlot = "1";
    document.body.dispatchEvent(new CustomEvent("switchModelCanvas"));
    expect(document.body.dataset.baseView).toBe("simplified");
    expect(second.classList.contains("d-none")).toBe(false);
    expect(first.classList.contains("d-none")).toBe(true);
    strip.dataset.activeSlot = "0";
    document.body.dispatchEvent(new CustomEvent("switchModelCanvas"));
    expect(document.body.dataset.baseView).toBe("modeling");
    expect(first.classList.contains("d-none")).toBe(true);
    expect(workspace.isConnected).toBe(true);
    expect(window.htmx.ajax).not.toHaveBeenCalled();
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

test("inline settings payload carries only the patch and mounted saved bookmark ids", () => {
    mount().remove();
    window.htmx.trigger = jest.fn();
    const form = document.createElement("form");
    form.innerHTML = '<input name="Storage_storage_capacity" value="9999">';
    const element = bookmark("storage", "storage_capacity");
    element.id = "bookmark-storage-storage_capacity-panel";
    const companion = bookmark("storage", "storage_capacity");
    companion.id = "bookmark-storage-storage_capacity-sources";
    const provisional = bookmark("object", "resolution", true);
    provisional.id = "bookmark-object-resolution-panel";
    form.append(element, provisional);
    document.body.append(form, companion);
    element.querySelector("[data-include-input]").checked = true;
    element.querySelector("[data-include-input]").dispatchEvent(new Event("change", {bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledWith(element, "bookmark-save");
    const parameters = {};
    document.body.dispatchEvent(new CustomEvent("htmx:configRequest", {detail: {elt: element, parameters}}));
    expect(Object.keys(parameters)).toEqual(["patch", "mounted"]);
    expect(JSON.parse(parameters.patch)).toEqual({fields: {storage: {storage_capacity: {included: true}}}});
    expect(JSON.parse(parameters.mounted)).toEqual([element.id, companion.id]);
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
