document.addEventListener("initDynamicForm", function () {
    const dynamicFormData = JSON.parse(document.getElementById('dynamic-form-data').textContent);

    function suspendFormControls(section) {
        section.querySelectorAll('input[name], select[name]').forEach(function(input) {
            if (!input.disabled) input.dataset.dynamicFormWasEnabled = "true";
            if (input.required) input.dataset.dynamicFormWasRequired = "true";
            input.required = false;
            input.disabled = true;
        });
    }

    function restoreFormControls(section) {
        section.querySelectorAll('input[name], select[name]').forEach(function(input) {
            if (input.dataset.dynamicFormWasEnabled === "true") input.disabled = false;
            if (input.dataset.dynamicFormWasRequired === "true") input.required = true;
            delete input.dataset.dynamicFormWasEnabled;
            delete input.dataset.dynamicFormWasRequired;
        });
    }

    function updateSelectionAttribution(selectElement) {
        const attributionElement = document.getElementById(`${selectElement.id}-attribution`);
        if (!attributionElement) return;

        const attribution = selectElement.selectedOptions[0]?.dataset.attribution || "";
        attributionElement.textContent = attribution;
        attributionElement.classList.toggle("d-none", !attribution);
    }

    document.querySelectorAll("select[data-selection-attribution]").forEach(function (selectElement) {
        updateSelectionAttribution(selectElement);
        selectElement.addEventListener("change", function () {
            updateSelectionAttribution(selectElement);
        });
    });

    /**
     * 1) SWITCH ELEMENT LOGIC
     */
    function displayOnlyActiveForm(switchValues, switchElement){
        // Helper to get all actual form section IDs in the DOM
        const getActualFormSectionIds = () => {
            const formSections = document.querySelectorAll('[id^="item-"]');
            return Array.from(formSections).map(el => el.id.replace('item-', ''));
        };
        const activeValue = switchElement.value;
        // Hide the other groups
        switchValues.forEach(function(switchValue) {
            if (switchValue !== activeValue) {
                const itemToHide = document.getElementById("item-" + switchValue);
                if (!itemToHide) {
                    const actualSections = getActualFormSectionIds();
                    throw new Error(
                        `Dynamic form error: Cannot find element with id "item-${switchValue}".\n\n` +
                        `Expected switch_values: [${switchValues.join(', ')}]\n` +
                        `Actual form sections in DOM: [${actualSections.join(', ')}]\n\n` +
                        `This mismatch means the switch_values in dynamic_form_data don't match the form sections rendered in the template.\n` +
                        `Check that form_sections in the Python code contains a section with category="${switchValue}".\n` +
                        `Common cause: using a different class name in dynamic_selects/dynamic_lists (e.g., "RecurrentEdgeProcess") ` +
                        `than in available_efootprint_classes (e.g., "RecurrentEdgeProcessFromForm").`
                    );
                }
                itemToHide.classList.add('d-none');
                suspendFormControls(itemToHide);
            }
        });

        // Show the newly selected group
        const itemToShow = document.getElementById("item-" + activeValue);
        if (!itemToShow) {
            const actualSections = getActualFormSectionIds();
            throw new Error(
                `Dynamic form error: Cannot find element with id "item-${activeValue}".\n\n` +
                `Switch element "${switchElement.id}" has value: "${activeValue}"\n` +
                `Expected switch_values: [${switchValues.join(', ')}]\n` +
                `Actual form sections in DOM: [${actualSections.join(', ')}]\n\n` +
                `The selected value "${activeValue}" does not have a corresponding form section in the DOM.\n` +
                `This often happens when dynamic_selects uses different class names than those used in generate_object_creation_structure().\n` +
                `Example: dynamic_selects might use "RecurrentEdgeProcess" while available_efootprint_classes uses "RecurrentEdgeProcessFromForm".`
            );
        }
        itemToShow.classList.remove('d-none');
        restoreFormControls(itemToShow);
    }

    /** Populate a select from the options associated with another control's value. */
    function updateDynamicSelect(listValue, filterId, targetId, restoreDefault = false, clearInvalid = false) {
        const filterElem = document.getElementById(filterId);
        const targetElem = document.getElementById(targetId);

        if (!filterElem || !targetElem) return;

        const filterKey = filterElem.value;
        const items = (listValue[filterKey] || []).map((item) => {
            if (typeof item === "object") {
                return {label: String(item.label), value: String(item.value)};
            }
            return {label: String(item), value: String(item)};
        });
        const selectedValue = restoreDefault ? targetElem.dataset.defaultValue : targetElem.value;

        // Check if options are already present
        const existingOptions = Array.from(targetElem.options).map(opt => opt.value);
        const newOptions = items.map(item => item.value);

        const optionsAreCurrent = existingOptions.length === newOptions.length
            && existingOptions.every((val, idx) => val === newOptions[idx]);
        if (optionsAreCurrent) {
            if (newOptions.includes(selectedValue)) targetElem.value = selectedValue;
            return;
        }

        targetElem.innerHTML = "";
        items.forEach(({ label, value }) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = label;
            targetElem.appendChild(option);
        });

        if (newOptions.includes(selectedValue)) {
            targetElem.value = selectedValue;
        } else if (clearInvalid) {
            targetElem.selectedIndex = -1;
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


    /**
     * Handle conditional catalog selects
     */
    if (dynamicFormData.dynamic_lists) {
        dynamicFormData.dynamic_lists.forEach((dynamicList) => {
            const filterId = dynamicList.filter_by;
            const selectId = dynamicList.input_id;

            updateDynamicSelect(dynamicList.list_value, filterId, selectId, true, true);

            document.getElementById(filterId)?.addEventListener("change", function () {
                updateDynamicSelect(dynamicList.list_value, filterId, selectId, false, true);
            });
        });
    }

    /**
     * Handle DYNAMIC SELECTS (for <select>)
     */
    if (dynamicFormData.dynamic_selects) {
        dynamicFormData.dynamic_selects.forEach((dynamicSelect) => {
            const filterId = dynamicSelect.filter_by;
            const selectId = dynamicSelect.input_id;

            // Fill once initially
            updateDynamicSelect(dynamicSelect.list_value, filterId, selectId);

            // Re-fill on change
            document.getElementById(filterId)?.addEventListener("change", function () {
                updateDynamicSelect(dynamicSelect.list_value, filterId, selectId);
            });
        });
    }

    /**
     * Show right form section based on SWITCH ELEMENT
     */
    if (dynamicFormData.switch_item) {
        const switchElementId = dynamicFormData.switch_item;
        const switchElement = document.getElementById(switchElementId);
        const switchValues = dynamicFormData.switch_values;
        displayOnlyActiveForm(switchValues, switchElement);

        switchElement.addEventListener("change", function () {
            displayOnlyActiveForm(switchValues, switchElement);
        });
    }
});


function checkCurrentValueVsDefaultValue(input) {
    let defaultValue = input.dataset.defaultValue;
    let fromDefaultValue = true;
    if ( (input.type === 'date' || input.type === 'text' || input.type === 'hidden'
            || input.tagName.toLowerCase() === 'select')
        && input.value !== defaultValue){
        fromDefaultValue = false;
    }
    if (input.type === 'number' && parseFloat(input.value) !== parseFloat(defaultValue)){
        fromDefaultValue = false;
    }
    return fromDefaultValue;
}


function onInputValueChange(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (checkCurrentValueVsDefaultValue(input)) return;
    input.dispatchEvent(new CustomEvent("source-metadata:value-changed", { bubbles: true }));
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
    return JSON.stringify(obj);
}

function convertStringLikeJsonToRealJsonFromElementWeb(str) {
    return JSON.parse(document.getElementById(str).dataset.json);
}
