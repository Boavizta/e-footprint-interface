document.addEventListener("initDynamicForm", function () {
    const dynamicFormData = JSON.parse(document.getElementById('dynamic-form-data').textContent);
    /**
     * 1) SWITCH ELEMENT LOGIC
     */
    function switchForms(switchValues, switchElement){
        // Hide the other groups
        switchValues.forEach(function(switchValue) {
            if (switchValue !== switchElement.value) {
                const itemToHide = document.getElementById("item-" + switchValue);
                itemToHide.classList.add('d-none');
                itemToHide.querySelectorAll('input, select').forEach(function(input) {
                    input.required = false;
                    input.disabled = true;
                });
            }
        });

        // Show the newly selected group
        const itemToShow = document.getElementById("item-" + switchElement.value);
        itemToShow.classList.remove('d-none');
        itemToShow.querySelectorAll('input, select').forEach(function(input) {
            input.required = true;
            input.disabled = false;
        });
    }

    if (dynamicFormData.switch_item) {
        const switchElementId = dynamicFormData.switch_item;
        const switchElement = document.getElementById(switchElementId);
        const switchValues = dynamicFormData.switch_values;
        switchForms(switchValues, switchElement);

        switchElement.addEventListener("change", function () {
            switchForms(switchValues, switchElement);
        });
    }

    /**
     * Reusable function that populates a target element (either <datalist> or <select>)
     * depending on 'type' ('datalist' vs 'select').
     * - listValue: an object keyed by filterKey, yielding an array of items
     * - filterId: the ID of the filter element (e.g. "type_object_available")
     * - targetId: the ID of the datalist/select to be populated
     * - type: either 'datalist' or 'select'
     */
    function fillData(type, listValue, filterId, targetId) {
        const filterElem = document.getElementById(filterId);
        const targetElem = document.getElementById(targetId);

        if (!filterElem || !targetElem) return;

        const filterKey = filterElem.value;
        const items = listValue[filterKey] || []; // fallback to empty array

        // Check if options are already present
        const existingOptions = Array.from(targetElem.options).map(opt => opt.value);
        const newOptions = items.map(item => (type === "datalist" ? item : item.value));

        if (existingOptions.length === newOptions.length && existingOptions.every((val, idx) => val === newOptions[idx])) {
            return; // If options are the same, don't update
        }

        // Preserve the selected value if possible
        const selectedValue = targetElem.value;

        // Clear existing options
        targetElem.innerHTML = "";

        if (type === "datalist") {
            // items are simple strings
            items.forEach((item) => {
                const option = document.createElement("option");
                option.value = item;
                targetElem.appendChild(option);
            });
        } else if (type === "select") {
            // items are objects with {label, value}
            items.forEach(({ label, value }) => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = label;
                targetElem.appendChild(option);
            });

            // Restore selected value if it still exists
            if (newOptions.includes(selectedValue)) {
                targetElem.value = selectedValue;
            }

            if (items.length === 1 && targetElem.closest('#item-efootprint_classes_available')) {
                targetElem.closest('#item-efootprint_classes_available').classList.add('d-none');
            }
            else {
                if (targetElem.closest('#item-efootprint_classes_available')) {
                    targetElem.closest('#item-efootprint_classes_available').classList.remove('d-none');
                }
            }
            targetElem.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }


    /**
     * 2) Handle DYNAMIC LISTS (for <datalist>)
     */
    if (dynamicFormData.dynamic_lists) {
        dynamicFormData.dynamic_lists.forEach((dynamicList) => {
            const filterId = dynamicList.filter_by;
            const listId = "datalist_" + dynamicList.input_id;

            // Fill once initially
            fillData("datalist", dynamicList.list_value, filterId, listId);

            document.getElementById(filterId)?.addEventListener("change", function () {
                fillData("datalist", dynamicList.list_value, filterId, listId);
                document.getElementById(dynamicList.input_id).value = "";
            });
        });
    }

    /**
     * 3) Handle DYNAMIC SELECTS (for <select>)
     */
    if (dynamicFormData.dynamic_selects) {
        dynamicFormData.dynamic_selects.forEach((dynamicSelect) => {
            const filterId = dynamicSelect.filter_by;
            const selectId = dynamicSelect.input_id;

            // Fill once initially
            fillData("select", dynamicSelect.list_value, filterId, selectId);

            // Re-fill on change
            document.getElementById(filterId)?.addEventListener("change", function () {
                fillData("select", dynamicSelect.list_value, filterId, selectId);
            });
        });
    }
});


function checkCurrentValueVsDefaultValue(input) {
    let defaultValue = input.dataset.defaultValue;
    let fromDefaultValue = true;
    if ( (input.type === 'date' || input.type === 'text' || input.tagName.toLowerCase() === 'select')
        && input.value !== defaultValue){
        fromDefaultValue = false;
    }
    if (input.type === 'number' && parseFloat(input.value) !== parseFloat(defaultValue)){
        fromDefaultValue = false;
    }
    return fromDefaultValue;
}


function updateSource(inputId) {
    let input = document.getElementById(inputId);

    if (input.dataset.sourceAttributeToSkip && input.dataset.sourceAttributeToSkip !== '') {
        return;
    }

    let sourceDiv = document.getElementById("source-" + input.id);
    if(input.dataset.defaultValue === '' && input.value === ''){
        sourceDiv.innerHTML = "";
        return;
    }

    let isSameAsDefault = checkCurrentValueVsDefaultValue(input);
    let displayDefaultSource;

    let associatedUnitId = input.dataset.associatedUnitId;
    if (!associatedUnitId) {
        displayDefaultSource = isSameAsDefault;
    }else{
        let associatedUnit = document.getElementById(associatedUnitId);
        let associatedUnitIsSameAsDefault = checkCurrentValueVsDefaultValue(associatedUnit);
        displayDefaultSource = isSameAsDefault && associatedUnitIsSameAsDefault;
    }

    if (displayDefaultSource) {
        if(input.dataset.sourceUrl && input.dataset.sourceUrl !== '' && input.dataset.sourceUrl !== 'None'){
            sourceDiv.innerHTML = `Source: <a target="_blank" class="sources-label" href="${input.dataset.sourceUrl}">${input.dataset.defaultName}</a>`
        }else{
            sourceDiv.innerHTML = `Source: ${input.dataset.defaultName}`
        }
    }else{
        sourceDiv.innerHTML = "Source: user data";
    }
}

function addEmptyValueWhenSelectMultipleFieldsHaveNoSelectedOption(){
    const allMultipleSelects = document.querySelectorAll('select[multiple]');
    allMultipleSelects.forEach(multipleSelect => {
        if (multipleSelect && ![...multipleSelect.options].some(opt => opt.selected)) {
            let idMultipleSelect = multipleSelect.id;
            multipleSelect.remove();
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = idMultipleSelect;
            hiddenInput.id = idMultipleSelect;
            hiddenInput.value = '';
            const labelGroup = document.getElementById("field-group-"+idMultipleSelect);
            labelGroup.appendChild(hiddenInput);
        }
    })
}

function convertJsonToStringLikeDjango(obj) {
    const jsonStr = JSON.stringify(obj);
    return jsonStr.replace(/\"/g, "'").replace(/\\'/g, "'");
}

function convertStringLikeJsonToRealJsonFromElementWeb(str) {
    return JSON.parse(document.getElementById(str).dataset.json.replace(/'/g, '"'));
}

function sortSelectMultipleFields(fieldId, selectedValue, direction) {
    let selectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("selected_data");
    let index = selectedOptions.findIndex(option => option.value === selectedValue);
    if (index === -1) return;
    if (direction === "up" && index > 0) {
        [selectedOptions[index - 1], selectedOptions[index]] =
            [selectedOptions[index], selectedOptions[index - 1]];
    }
    if (direction === "down" && index < selectedOptions.length - 1) {
        [selectedOptions[index + 1], selectedOptions[index]] =
            [selectedOptions[index], selectedOptions[index + 1]];
    }
    document.getElementById("selected_data").dataset.json = convertJsonToStringLikeDjango(selectedOptions);
    refreshSelectMultipleFields(fieldId);
}

function deleteValueFromSelectMultiple(fieldId, selectedValue) {
    let selectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("selected_data");
    let unselectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("unselected_data");
    let index = selectedOptions.findIndex(option => option.value === selectedValue);
    if (index === -1) return;
    let removedItem = selectedOptions.splice(index, 1)[0];
    unselectedOptions.push(removedItem);
    let newOption = document.createElement("option");
    newOption.value = removedItem.value;
    newOption.textContent = removedItem.label;
    document.getElementById("select-new-object-"+fieldId).appendChild(newOption);
    document.getElementById("unselected_data").dataset.json = convertJsonToStringLikeDjango(unselectedOptions);
    document.getElementById("selected_data").dataset.json = convertJsonToStringLikeDjango(selectedOptions);
    document.getElementById("add-btn-" + fieldId).removeAttribute("disabled");
    document.getElementById("select-new-object-"+fieldId).removeAttribute("disabled");
    refreshSelectMultipleFields(fieldId);
}

function addValueToSelectMultiple(fieldId) {
    const selectElement = document.getElementById("select-new-object-" + fieldId);
    const selectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("selected_data");
    const unselectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("unselected_data");

    const idx = unselectedOptions.findIndex(o => o.value === selectElement.value);
    if (idx !== -1) {
        const [item] = unselectedOptions.splice(idx, 1);
        selectedOptions.push(item);
    }

    const opt = selectElement.querySelector(`option[value="${selectElement.value}"]`);
    if (opt) opt.remove();

    document.getElementById("selected_data").dataset.json   = convertJsonToStringLikeDjango(selectedOptions);
    document.getElementById("unselected_data").dataset.json = convertJsonToStringLikeDjango(unselectedOptions);

    refreshSelectMultipleFields(fieldId);
}

function refreshSelectMultipleFields(fieldId) {
    let objectsAlreadySelectedElement = document.getElementById("objects-already-selected-for-" + fieldId);
    objectsAlreadySelectedElement.innerHTML = "";
    let selectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("selected_data");
    let selectNewObjectElement = document.getElementById("select-new-object-" + fieldId);

    if(!selectedOptions || selectedOptions.length === 0) {
        let newSelectedValue = document.createElement("tr");
        let noValue = document.createElement("td");
        if(selectNewObjectElement.options.length === 0 ){
            noValue.setAttribute("colspan", "4");
            noValue.innerHTML = `<span class="text-muted">No available options</span>`;
        }else{
            noValue.setAttribute("colspan", "4");
            noValue.innerHTML = `<span class="text-muted">No values selected</span>`;
        }
        newSelectedValue.appendChild(noValue);
        objectsAlreadySelectedElement.appendChild(newSelectedValue);
        return;
    }

    selectedOptions.forEach((selectedValue, index) => {
        let newSelectedValue = document.createElement("tr");
        let nameSelectedValue = document.createElement("td");
        nameSelectedValue.innerHTML = `${selectedValue.label}`;
        let ctaSortUp = document.createElement("td");
        let ctaSortDown = document.createElement("td");
        let removeSelectedValue = document.createElement("td");

        nameSelectedValue.className = "width-70";
        ctaSortUp.className = "width-10";
        ctaSortDown.className = "width-10";
        removeSelectedValue.className = "width-10";

        if (index !== selectedOptions.length - 1) {
            ctaSortDown.innerHTML = `
            <button type="button" class="btn btn-white border-0 rounded-2 fs-xl p-2" onclick="sortSelectMultipleFields('${fieldId}', '${selectedValue.value}','down')">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-caret-down-fill" viewBox="0 0 16 16">
                  <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                </svg>
            </button>`
        }else{
            ctaSortDown.innerHTML = '';
        }
        if(index !== 0){
            ctaSortUp.innerHTML = `
            <button type="button" class="btn btn-white border-0 rounded-2 fs-xl p-2" onclick="sortSelectMultipleFields('${fieldId}', '${selectedValue.value}','up')">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-caret-up-fill" viewBox="0 0 16 16">
                  <path d="m7.247 4.86-4.796 5.481c-.566.647-.106 1.659.753 1.659h9.592a1 1 0 0 0 .753-1.659l-4.796-5.48a1 1 0 0 0-1.506 0z"/>
                </svg>
            </button>`
        }else{
            ctaSortUp.innerHTML = '';
        }
        removeSelectedValue.innerHTML = `<button type="button" class="btn btn-white border-0 rounded-2 fs-xl p-2"
            onclick="deleteValueFromSelectMultiple('${fieldId}','${selectedValue.value}')"
            _="on load remove .disabled from #add-btn-${fieldId}"
        >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x" viewBox="0 0 16 16">
                <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>
            </svg>
        </button>`
        newSelectedValue.innerHTML = nameSelectedValue.outerHTML + ctaSortUp.outerHTML + ctaSortDown.outerHTML + removeSelectedValue.outerHTML;
        objectsAlreadySelectedElement.appendChild(newSelectedValue);
    });

    if(selectNewObjectElement.options.length === 0){
        document.getElementById("add-btn-" + fieldId).setAttribute("disabled", "true");
        selectNewObjectElement.setAttribute("disabled", "true");
    }

    document.getElementById(fieldId).value = selectedOptions.map(option => option.value).join(";");
}
