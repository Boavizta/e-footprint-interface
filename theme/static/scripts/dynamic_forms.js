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

function updateSource(input){
    let divSource = document.getElementById("source-"+input.id);
    if(input.value && parseFloat(input.value.length) > 0){
        if(parseFloat(input.value) !== parseFloat(input.dataset.defaultvalue)){
            divSource.innerHTML = `source : user data`;
        }else{
            if(input.dataset.sourcelink && input.dataset.sourcelink !== '' && input.dataset.sourcelink !== 'None'){
                divSource.innerHTML = `source : <a target="_blank" class="sources-label" href="${input.dataset.sourcelink}">${input.dataset.sourcename}</a>`
            }else{
                divSource.innerHTML = `source : ${input.dataset.sourcename}`
            }
        }
    }
}
