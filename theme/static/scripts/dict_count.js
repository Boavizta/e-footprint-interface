(function () {
    "use strict";

    function state(fieldId) { return document.getElementById("selected_data_" + fieldId); }
    function selected(fieldId) { return convertStringLikeJsonToRealJsonFromElementWeb("selected_data_" + fieldId); }
    function options(fieldId) { return convertStringLikeJsonToRealJsonFromElementWeb("available_data_" + fieldId); }
    function write(fieldId, value) { state(fieldId).dataset.json = convertJsonToStringLikeDjango(value); }
    function minimum(fieldId, name) { return Number(state(fieldId).dataset[name] || 0); }

    function button(label, action, fieldId, objectId, direction, text) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "btn btn-white border-0 rounded-2 fs-xl p-2";
        element.setAttribute("aria-label", label);
        Object.assign(element.dataset, {action, fieldId});
        if (objectId !== undefined) element.dataset.objectId = objectId;
        if (direction !== undefined) element.dataset.direction = direction;
        element.textContent = text;
        return element;
    }

    function moveDictCountEntry(fieldId, objectId, direction) {
        const value = selected(fieldId);
        const keys = Object.keys(value);
        const index = keys.indexOf(objectId);
        const target = direction === "up" ? index - 1 : index + 1;
        if (index === -1 || target < 0 || target >= keys.length) return;
        [keys[index], keys[target]] = [keys[target], keys[index]];
        const reordered = {};
        keys.forEach((key) => { reordered[key] = value[key]; });
        write(fieldId, reordered);
        refreshDictCountField(fieldId);
        tagFormAsModified();
    }

    function addDictCountEntry(fieldId) {
        const objectId = document.getElementById("select-new-object-" + fieldId)?.value;
        if (!objectId) return;
        const value = selected(fieldId);
        if (value[objectId] === undefined) {
            value[objectId] = 1;
            write(fieldId, value);
            tagFormAsModified();
        }
        refreshDictCountField(fieldId);
    }

    function removeDictCountEntry(fieldId, objectId) {
        const value = selected(fieldId);
        if (Object.keys(value).length <= minimum(fieldId, "minItems")) return;
        delete value[objectId];
        write(fieldId, value);
        refreshDictCountField(fieldId);
        tagFormAsModified();
    }

    function updateDictCountEntry(fieldId, objectId, rawValue) {
        const parsed = Number(rawValue);
        const invalid = rawValue === "" || !Number.isFinite(parsed) || parsed < minimum(fieldId, "minCount")
            || (state(fieldId).dataset.strictlyPositive === "true" && parsed <= 0);
        if (invalid) {
            refreshDictCountField(fieldId);
            return;
        }
        const value = selected(fieldId);
        value[objectId] = parsed;
        write(fieldId, value);
        refreshDictCountField(fieldId);
        tagFormAsModified();
    }

    function emptyRow(message) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 3;
        const span = document.createElement("span");
        span.className = "text-muted";
        span.textContent = message;
        cell.appendChild(span);
        row.appendChild(cell);
        return row;
    }

    function refreshDictCountField(fieldId) {
        const value = selected(fieldId);
        const available = options(fieldId);
        const table = document.getElementById("objects-already-selected-for-" + fieldId);
        const select = document.getElementById("select-new-object-" + fieldId);
        const hidden = document.getElementById(fieldId);
        const add = document.getElementById("add-btn-" + fieldId);
        if (!table || !select || !hidden || !add) return;

        const pendingSelection = select.value;
        const unselected = available.filter((item) => value[item.value] === undefined);
        select.replaceChildren(...unselected.map((item) => {
            const option = document.createElement("option");
            option.value = item.value;
            option.textContent = item.label;
            return option;
        }));
        if (unselected.some((item) => String(item.value) === String(pendingSelection))) {
            select.value = pendingSelection;
        }

        const labels = new Map(available.map((item) => [item.value, item.label]));
        const entries = Object.keys(value).filter((id) => labels.has(id)).map((id) => ({id, label: labels.get(id)}));
        if (!entries.length) {
            table.replaceChildren(emptyRow("No values selected"));
        } else {
            const ordered = state(fieldId).dataset.ordered === "true";
            table.replaceChildren(...entries.map((entry, index) => {
                const row = document.createElement("tr");
                const label = document.createElement("td");
                label.className = "width-70";
                label.textContent = entry.label;
                const count = document.createElement("td");
                count.className = "width-20";
                const input = document.createElement("input");
                input.type = "number";
                input.min = String(minimum(fieldId, "minCount"));
                input.step = "any";
                input.className = "form-control";
                input.value = value[entry.id];
                Object.assign(input.dataset, {action: "update-dict-count", fieldId, objectId: entry.id});
                count.appendChild(input);
                const actions = document.createElement("td");
                actions.className = "width-10 text-end text-nowrap";
                if (ordered && index > 0) actions.appendChild(button("Move up", "move-dict-count", fieldId, entry.id, "up", "↑"));
                if (ordered && index < entries.length - 1) actions.appendChild(button("Move down", "move-dict-count", fieldId, entry.id, "down", "↓"));
                const remove = button("Remove", "remove-dict-count", fieldId, entry.id, undefined, "×");
                remove.disabled = entries.length <= minimum(fieldId, "minItems");
                actions.appendChild(remove);
                row.append(label, count, actions);
                return row;
            }));
        }
        add.disabled = unselected.length === 0;
        select.disabled = unselected.length === 0;
        hidden.value = JSON.stringify(value);
    }

    function initializeIn(container) {
        const nodes = [];
        if (container?.matches?.("[data-dict-count-field]")) nodes.push(container);
        if (container?.querySelectorAll) nodes.push(...container.querySelectorAll("[data-dict-count-field]"));
        nodes.forEach((node) => refreshDictCountField(node.dataset.dictCountField));
    }

    if (document.documentElement.dataset.dictCountListenersBound !== "true") {
        document.documentElement.dataset.dictCountListenersBound = "true";
        document.addEventListener("click", function (event) {
            const control = event.target.closest?.("[data-action]");
            if (!control) return;
            const {action, fieldId, objectId, direction} = control.dataset;
            if (action === "add-dict-count") addDictCountEntry(fieldId);
            else if (action === "remove-dict-count") removeDictCountEntry(fieldId, objectId);
            else if (action === "move-dict-count") moveDictCountEntry(fieldId, objectId, direction);
        });
        document.addEventListener("change", function (event) {
            const input = event.target.closest?.("[data-action='update-dict-count']");
            if (input) updateDictCountEntry(input.dataset.fieldId, input.dataset.objectId, input.value);
        });
        document.addEventListener("DOMContentLoaded", () => initializeIn(document));
        document.addEventListener("htmx:load", (event) => initializeIn(event.detail?.elt || event.target));
    }

    if (typeof module !== "undefined") {
        module.exports = {addDictCountEntry, moveDictCountEntry, removeDictCountEntry, refreshDictCountField, updateDictCountEntry};
    }
}());
