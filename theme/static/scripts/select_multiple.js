function sortSelectMultipleFields(fieldId, selectedValue, direction) {
    let selectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("selected_data");
    let index = selectedOptions.findIndex(option => String(option.value) === String(selectedValue));
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
    tagFormAsModified();
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
    tagFormAsModified();
}

function addValueToSelectMultiple(fieldId) {
    const selectElement = document.getElementById("select-new-object-" + fieldId);
    if (!selectElement.value) return;
    const selectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("selected_data");
    const unselectedOptions = convertStringLikeJsonToRealJsonFromElementWeb("unselected_data");

    const idx = unselectedOptions.findIndex(o => String(o.value) === String(selectElement.value));
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
            document.getElementById("add-btn-" + fieldId).setAttribute("disabled", "true");
            selectNewObjectElement.setAttribute("disabled", "true");
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
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chevron-down" viewBox="0 0 16 16">
                  <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708"/>
                </svg>
            </button>`
        }else{
            ctaSortDown.innerHTML = '';
        }
        if(index !== 0){
            ctaSortUp.innerHTML = `
            <button type="button" class="btn btn-white border-0 rounded-2 fs-xl p-2" onclick="sortSelectMultipleFields('${fieldId}', '${selectedValue.value}','up')">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chevron-up" viewBox="0 0 16 16">
                  <path fill-rule="evenodd" d="M7.646 4.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1-.708.708L8 5.707l-5.646 5.647a.5.5 0 0 1-.708-.708z"/>
                </svg>
            </button>`
        }else{
            ctaSortUp.innerHTML = '';
        }
        removeSelectedValue.innerHTML = `<button type="button" class="btn btn-white border-0 rounded-2 fs-xl p-2"
            onclick="deleteValueFromSelectMultiple('${fieldId}','${selectedValue.value}')"
        >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x" viewBox="0 0 16 16">
                <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>
            </svg>
        </button>`
        newSelectedValue.appendChild(nameSelectedValue);
        newSelectedValue.appendChild(ctaSortUp);
        newSelectedValue.appendChild(ctaSortDown);
        newSelectedValue.appendChild(removeSelectedValue);

        objectsAlreadySelectedElement.appendChild(newSelectedValue);
    });

    if(selectNewObjectElement.options.length === 0){
        document.getElementById("add-btn-" + fieldId).setAttribute("disabled", "true");
        selectNewObjectElement.setAttribute("disabled", "true");
    }

    document.getElementById(fieldId).value = selectedOptions.map(option => option.value).join(";");
}
