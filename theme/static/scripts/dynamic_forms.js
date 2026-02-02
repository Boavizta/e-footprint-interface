document.addEventListener("initDynamicForm", function () {
    const dynamicFormData = JSON.parse(document.getElementById('dynamic-form-data').textContent);
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
                itemToHide.querySelectorAll('input, select').forEach(function(input) {
                    input.required = false;
                    input.disabled = true;
                });
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
        itemToShow.querySelectorAll('input, select').forEach(function(input) {
            input.required = true;
            input.disabled = false;
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
    function updateDynamicDatalistOrSelect(type, listValue, filterId, targetId) {
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
     * Handle DYNAMIC LISTS (for <datalist>)
     */
    if (dynamicFormData.dynamic_lists) {
        dynamicFormData.dynamic_lists.forEach((dynamicList) => {
            const filterId = dynamicList.filter_by;
            const listId = "datalist_" + dynamicList.input_id;

            // Fill once initially
            updateDynamicDatalistOrSelect("datalist", dynamicList.list_value, filterId, listId);

            document.getElementById(filterId)?.addEventListener("change", function () {
                updateDynamicDatalistOrSelect("datalist", dynamicList.list_value, filterId, listId);
                document.getElementById(dynamicList.input_id).value = "";
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
            updateDynamicDatalistOrSelect("select", dynamicSelect.list_value, filterId, selectId);

            // Re-fill on change
            document.getElementById(filterId)?.addEventListener("change", function () {
                updateDynamicDatalistOrSelect("select", dynamicSelect.list_value, filterId, selectId);
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
    if (input.dataset.staticSource) {
        if(input.dataset.sourceUrl && input.dataset.sourceUrl !== '' && input.dataset.sourceUrl !== 'None'){
            sourceDiv.innerHTML = `Source: <a target="_blank" class="sources-label" href="${input.dataset.sourceUrl}">${input.dataset.defaultName}</a>`
        }else{
            sourceDiv.innerHTML = `Source: ${input.dataset.defaultName}`
        }
        return;
    }

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
