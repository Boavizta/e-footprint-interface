(function () {
    "use strict";

    function read(fieldId, prefix) { return convertStringLikeJsonToRealJsonFromElementWeb(prefix + fieldId); }
    function write(fieldId, prefix, value) {
        document.getElementById(prefix + fieldId).dataset.json = convertJsonToStringLikeDjango(value);
    }
    function button(label, action, fieldId, selectedValue, text) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "btn btn-white border-0 rounded-2 fs-xl p-2";
        element.setAttribute("aria-label", label);
        Object.assign(element.dataset, {action, fieldId, selectedValue});
        element.textContent = text;
        return element;
    }

    function sortSelectMultipleFields(fieldId, selectedValue, direction) {
        const selected = read(fieldId, "selected_data_");
        const index = selected.findIndex((item) => String(item.value) === String(selectedValue));
        const target = direction === "up" ? index - 1 : index + 1;
        if (index === -1 || target < 0 || target >= selected.length) return;
        [selected[index], selected[target]] = [selected[target], selected[index]];
        write(fieldId, "selected_data_", selected);
        refreshSelectMultipleFields(fieldId);
        tagFormAsModified();
    }

    function removeValueFromSelectMultiple(fieldId, selectedValue) {
        const selected = read(fieldId, "selected_data_");
        const state = document.getElementById("selected_data_" + fieldId);
        if (selected.length <= Number(state.dataset.minItems || 0)) return;
        const unselected = read(fieldId, "unselected_data_");
        const index = selected.findIndex((item) => String(item.value) === String(selectedValue));
        if (index === -1) return;
        unselected.push(selected.splice(index, 1)[0]);
        write(fieldId, "selected_data_", selected);
        write(fieldId, "unselected_data_", unselected);
        refreshSelectMultipleFields(fieldId);
        tagFormAsModified();
    }

    function addValueToSelectMultiple(fieldId) {
        const select = document.getElementById("select-new-object-" + fieldId);
        if (!select?.value) return;
        const selected = read(fieldId, "selected_data_");
        const unselected = read(fieldId, "unselected_data_");
        const index = unselected.findIndex((item) => String(item.value) === String(select.value));
        if (index === -1) return;
        selected.push(unselected.splice(index, 1)[0]);
        write(fieldId, "selected_data_", selected);
        write(fieldId, "unselected_data_", unselected);
        refreshSelectMultipleFields(fieldId);
        tagFormAsModified();
    }

    function emptyRow(message) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 4;
        const span = document.createElement("span");
        span.className = "text-muted";
        span.textContent = message;
        cell.appendChild(span);
        row.appendChild(cell);
        return row;
    }

    function refreshSelectMultipleFields(fieldId) {
        const table = document.getElementById("objects-already-selected-for-" + fieldId);
        const select = document.getElementById("select-new-object-" + fieldId);
        const add = document.getElementById("add-btn-" + fieldId);
        const state = document.getElementById("selected_data_" + fieldId);
        const hidden = document.getElementById(fieldId);
        if (!table || !select || !add || !state || !hidden) return;
        const selected = read(fieldId, "selected_data_") || [];
        const unselected = read(fieldId, "unselected_data_") || [];
        const pendingSelection = select.value;
        select.replaceChildren(...unselected.map((item) => {
            const option = document.createElement("option");
            option.value = item.value;
            option.textContent = item.label;
            return option;
        }));
        if (unselected.some((item) => String(item.value) === String(pendingSelection))) {
            select.value = pendingSelection;
        }
        if (!selected.length) {
            table.replaceChildren(emptyRow(unselected.length ? "No values selected" : "No available options"));
        } else {
            const ordered = state.dataset.ordered === "true";
            const minItems = Number(state.dataset.minItems || 0);
            table.replaceChildren(...selected.map((item, index) => {
                const row = document.createElement("tr");
                const label = document.createElement("td");
                label.className = "width-70";
                label.textContent = item.label;
                const up = document.createElement("td");
                up.className = "width-10";
                if (ordered && index > 0) up.appendChild(button("Move up", "move-select-multiple-up", fieldId, item.value, "↑"));
                const down = document.createElement("td");
                down.className = "width-10";
                if (ordered && index < selected.length - 1) down.appendChild(button("Move down", "move-select-multiple-down", fieldId, item.value, "↓"));
                const removeCell = document.createElement("td");
                removeCell.className = "width-10";
                const remove = button("Remove", "remove-select-multiple", fieldId, item.value, "×");
                remove.id = "remove-" + item.value;
                remove.disabled = selected.length <= minItems;
                removeCell.appendChild(remove);
                row.append(label, up, down, removeCell);
                return row;
            }));
        }
        add.disabled = unselected.length === 0;
        select.disabled = unselected.length === 0;
        hidden.value = selected.map((item) => item.value).join(";");
    }

    function initializeIn(container) {
        const nodes = [];
        if (container?.matches?.("[data-select-multiple-field]")) nodes.push(container);
        if (container?.querySelectorAll) nodes.push(...container.querySelectorAll("[data-select-multiple-field]"));
        nodes.forEach((node) => refreshSelectMultipleFields(node.dataset.selectMultipleField));
    }

    if (document.documentElement.dataset.selectMultipleListenersBound !== "true") {
        document.documentElement.dataset.selectMultipleListenersBound = "true";
        document.addEventListener("click", function (event) {
            const control = event.target.closest?.("[data-action]");
            if (!control) return;
            const {action, fieldId, selectedValue} = control.dataset;
            if (action === "add-select-multiple") addValueToSelectMultiple(fieldId);
            else if (action === "remove-select-multiple") removeValueFromSelectMultiple(fieldId, selectedValue);
            else if (action === "move-select-multiple-up") sortSelectMultipleFields(fieldId, selectedValue, "up");
            else if (action === "move-select-multiple-down") sortSelectMultipleFields(fieldId, selectedValue, "down");
        });
        document.addEventListener("DOMContentLoaded", () => initializeIn(document));
        document.addEventListener("htmx:load", (event) => initializeIn(event.detail?.elt || event.target));
    }

    if (typeof module !== "undefined") {
        module.exports = {addValueToSelectMultiple, refreshSelectMultipleFields, removeValueFromSelectMultiple, sortSelectMultipleFields};
    }
}());
