function _getDictCountSelectedMap(fieldId) {
    return convertStringLikeJsonToRealJsonFromElementWeb("selected_data_" + fieldId);
}

function _getDictCountAvailableOptions(fieldId) {
    return convertStringLikeJsonToRealJsonFromElementWeb("available_data_" + fieldId);
}

function _setDictCountSelectedMap(fieldId, selectedMap) {
    document.getElementById("selected_data_" + fieldId).dataset.json = convertJsonToStringLikeDjango(selectedMap);
}

function addDictCountEntry(fieldId) {
    const selectElement = document.getElementById("select-new-object-" + fieldId);
    const objectId = selectElement.value;
    if (!objectId) {
        return;
    }

    const selectedMap = _getDictCountSelectedMap(fieldId);
    if (!selectedMap[objectId]) {
        selectedMap[objectId] = 1;
        _setDictCountSelectedMap(fieldId, selectedMap);
    }
    refreshDictCountField(fieldId);
}

function removeDictCountEntry(fieldId, objectId) {
    const selectedMap = _getDictCountSelectedMap(fieldId);
    delete selectedMap[objectId];
    _setDictCountSelectedMap(fieldId, selectedMap);
    refreshDictCountField(fieldId);
    tagFormAsModified();
}

function updateDictCountEntry(fieldId, objectId, rawValue) {
    const parsed = parseFloat(rawValue);
    const selectedMap = _getDictCountSelectedMap(fieldId);
    if (!Number.isFinite(parsed) || parsed < 0) {
        refreshDictCountField(fieldId);
        return;
    }
    selectedMap[objectId] = parsed;
    _setDictCountSelectedMap(fieldId, selectedMap);
    refreshDictCountField(fieldId);
    tagFormAsModified();
}

function refreshDictCountField(fieldId) {
    const selectedMap = _getDictCountSelectedMap(fieldId);
    const availableOptions = _getDictCountAvailableOptions(fieldId);
    const tableElement = document.getElementById("objects-already-selected-for-" + fieldId);
    const selectElement = document.getElementById("select-new-object-" + fieldId);
    const hiddenInput = document.getElementById(fieldId);
    const addButton = document.getElementById("add-btn-" + fieldId);

    const unselectedOptions = availableOptions.filter((option) => selectedMap[option.value] === undefined);
    selectElement.innerHTML = "";
    unselectedOptions.forEach((option) => {
        const newOption = document.createElement("option");
        newOption.value = option.value;
        newOption.textContent = option.label;
        selectElement.appendChild(newOption);
    });

    const selectedEntries = availableOptions.filter((option) => selectedMap[option.value] !== undefined);
    if (selectedEntries.length === 0) {
        tableElement.innerHTML = `
            <tr>
                <td colspan="3"><span class="text-muted">No values selected</span></td>
            </tr>`;
    } else {
        tableElement.innerHTML = selectedEntries.map((option) => `
            <tr>
                <td class="width-70">${option.label}</td>
                <td class="width-20">
                    <input type="number" min="0" step="any" class="form-control"
                        value="${selectedMap[option.value]}"
                        onchange="event.stopPropagation();updateDictCountEntry('${fieldId}', '${option.value}', this.value)">
                </td>
                <td class="width-10 text-end">
                    <button type="button" class="btn btn-white border-0 rounded-2 fs-xl p-2"
                        onclick="event.stopPropagation();removeDictCountEntry('${fieldId}', '${option.value}')">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x" viewBox="0 0 16 16">
                            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>
                        </svg>
                    </button>
                </td>
            </tr>`).join("");
    }

    const disabled = unselectedOptions.length === 0;
    if (disabled) {
        addButton.setAttribute("disabled", "true");
        selectElement.setAttribute("disabled", "true");
    } else {
        addButton.removeAttribute("disabled");
        selectElement.removeAttribute("disabled");
    }

    hiddenInput.value = JSON.stringify(selectedMap);
}

if (typeof module !== "undefined") {
    module.exports = {
        addDictCountEntry,
        removeDictCountEntry,
        refreshDictCountField,
        updateDictCountEntry,
    };
}
