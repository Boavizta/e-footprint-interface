"use strict";

// Configure controls and the object navigation shared with the saved-input view.
// Draft settings remain in the DOM; serialization happens only when the form submits.
function definitionFromForm(form) {
    const fields = {};
    form.querySelectorAll("[data-field-address]").forEach(field => {
        const included = field.querySelector("[data-include-input]").checked;
        const help = field.querySelector("[data-field-help]").value;
        if (included || help) {
            fields[field.dataset.ownerId] ??= {};
            fields[field.dataset.ownerId][field.dataset.attribute] = { included, help };
        }
    });
    return { title: form.elements.title.value, guidance: form.elements.guidance.value, fields };
}

function navigate(workspace, objectId) {
    const object = document.getElementById(objectId);
    if (!object || object.hidden) return;
    workspace.querySelectorAll("[data-navigation-object][aria-current]").forEach(button => button.removeAttribute("aria-current"));
    workspace.querySelector(`[data-navigation-object="${objectId}"]`)?.setAttribute("aria-current", "true");
    object.closest("[data-simplified-group]").open = true;
    object.open = true;
    object.scrollIntoView({ block: "nearest" });
    object.querySelector("summary").focus({ preventScroll: true });
    workspace.querySelector("[data-object-selector]").value = objectId;
}
function refreshSelection(workspace) {
    const controls = [...workspace.querySelectorAll("[data-selection-controls]")];
    const byId = new Map(controls.map(control => [control.dataset.fieldId, control]));
    const required = new Set();
    const pending = controls.filter(control => control.querySelector("[data-include-input]").checked);
    for (let index = 0; index < pending.length; index++) {
        for (const id of pending[index].dataset.requiredInputs.split(" ").filter(Boolean)) {
            if (required.has(id)) continue;
            required.add(id);
            const dependent = byId.get(id);
            dependent.querySelector("[data-include-input]").checked = true;
            pending.push(dependent);
        }
    }
    controls.forEach(control => {
        const locked = required.has(control.dataset.fieldId);
        control.querySelector("[data-include-input]").disabled = locked;
        control.querySelector("[data-required-explanation]").hidden = !locked;
    });
    refreshFilter(workspace);
}
function refreshFilter(workspace) {
    const filtered = !!workspace.querySelector("[data-selected-object-filter]")?.checked;
    const focusedObject = document.activeElement.closest("[data-simplified-object]");
    let visibleCount = 0;
    workspace.querySelectorAll("[data-simplified-object]").forEach(object => {
        const count = workspace.dataset.mode === "configure"
            ? [...object.querySelectorAll("[data-include-input]")].filter(input => input.checked).length
            : object.querySelectorAll("[data-field-address]").length;
        object.querySelector("[data-object-count]").textContent = `${count} input${count === 1 ? "" : "s"}`;
        object.hidden = filtered && count === 0;
        if (!object.hidden) visibleCount++;
        const navigation = workspace.querySelector(`[data-navigation-object="${object.id}"]`);
        navigation.hidden = object.hidden;
        navigation.querySelector("[data-navigation-count]").textContent = `(${count})`;
        const option = workspace.querySelector(`option[value="${object.id}"]`);
        option.hidden = object.hidden;
        option.disabled = object.hidden;
    });
    workspace.querySelectorAll("[data-simplified-group]").forEach(group => {
        const visibleObjects = [...group.querySelectorAll("[data-simplified-object]")].filter(object => !object.hidden);
        group.hidden = visibleObjects.length === 0;
        group.querySelector("[data-group-count]").textContent = `${visibleObjects.length} object${visibleObjects.length === 1 ? "" : "s"}`;
        workspace.querySelector(`[data-navigation-group="${group.id}"]`).hidden = group.hidden;
        workspace.querySelector(`[data-selector-group="${group.id}"]`).hidden = group.hidden;
    });
    workspace.querySelector("[data-filter-empty]").hidden = !filtered || visibleCount > 0;
    if (focusedObject?.hidden) {
        const next = [...workspace.querySelectorAll("[data-simplified-object]")].find(object => !object.hidden);
        if (next) navigate(workspace, next.id);
        else workspace.querySelector("[data-selected-object-filter]").focus();
    }
}

function registerConfiguration({ activeWorkspace, configureForm }) {
    document.addEventListener("input", event => {
        const form = event.target.closest("[data-configure-form]");
        if (form && event.target.matches('[name="title"], [name="guidance"], [data-field-help], [data-include-input]')) {
            form.dataset.dirty = "true";
        }
    });
    document.body.addEventListener("htmx:configRequest", event => {
        if (event.detail.elt.matches("[data-configure-form]")) {
            event.detail.parameters.definition = JSON.stringify(definitionFromForm(event.detail.elt));
        }
    });
    document.addEventListener("change", event => {
        const workspace = event.target.closest("[data-simplified-workspace]");
        if (!workspace) return;
        if (event.target.matches("[data-include-input]")) {
            configureForm().dataset.dirty = "true";
            refreshSelection(workspace);
        }
        if (event.target.matches("[data-selected-object-filter]")) refreshFilter(workspace);
        if (event.target.matches("[data-object-selector]")) navigate(workspace, event.target.value);
    });
    document.addEventListener("click", event => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const workspace = activeWorkspace();
        switch (button.dataset.action) {
        case "simplified-clear":
            if (window.confirm("Remove all selected inputs and all per-field help, including help retained on deselected inputs? Modeling values and sources stay unchanged.")) {
                workspace.querySelectorAll("[data-include-input]").forEach(input => { input.checked = false; });
                workspace.querySelectorAll("[data-field-help]").forEach(input => { input.value = ""; });
                configureForm().dataset.dirty = "true";
                refreshSelection(workspace);
            }
            break;
        case "simplified-navigate": navigate(workspace, button.dataset.navigationObject); break;
        case "simplified-expand":
        case "simplified-collapse":
            workspace.querySelectorAll("details").forEach(item => { item.open = button.dataset.action === "simplified-expand"; });
            break;
        case "simplified-show-all":
            workspace.querySelector("[data-selected-object-filter]").checked = false;
            refreshFilter(workspace);
            break;
        }
    });
}

module.exports = { definitionFromForm, navigate, refreshSelection, refreshFilter, registerConfiguration };
