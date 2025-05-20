function initSortableObjectCards() {
    const upList = new Sortable(document.getElementById("up-list"), {
        animation: 150,
        onEnd: updateLines
    });

    const ujList = new Sortable(document.getElementById("uj-list"), {
        animation: 150,
        onEnd: updateLines
    });

    const serverList = new Sortable(document.getElementById("server-list"), {
        animation: 150,
        onEnd: updateLines
    });
}

function initModelBuilderMain() {
    initLeaderLines();
    initSortableObjectCards();
    initHammer();
    resizeSystemNameHeader();
}

function reverseIconAccordion(objectId){
    let icon = document.getElementById("icon_accordion_"+objectId);
    if (icon.classList.contains("chevron-rotate")) {
        icon.classList.remove("chevron-rotate");
    }
    else {
        icon.classList.add("chevron-rotate");
    }
    updateLines();
}


function resizeSystemNameHeader() {
    let systemNameHeader = document.getElementById("SystemNameHeader");

    let span = document.createElement("span");
    span.style.visibility = "hidden";
    span.style.position = "absolute";
    span.style.whiteSpace = "pre";
    span.style.font = window.getComputedStyle(systemNameHeader).font;
    document.body.appendChild(span);
    span.textContent = systemNameHeader.value;
    systemNameHeader.style.width = `${span.offsetWidth + 5}px`;
    document.body.removeChild(span);
}


function removeAllOpenedObjectsHighlights(){
    let objectsActivated = document.querySelectorAll(".model-builder-card-opened");
    objectsActivated.forEach(function (object) {
        object.classList.remove("model-builder-card-opened");
    });
}


function highlightObjectAfterAddOrEdit(modelObjectId){
    let element = document.getElementById(modelObjectId);
    if (element) {
        element.classList.add("border-pulse-after-add-edit-object");
        setTimeout(() => {
            element.classList.remove("border-pulse-after-add-edit-object");
            updateLines();
        }, 1000);
    }
}

document.body.addEventListener("highlightOpenedObjects", function (event) {
    let elements = event.detail.value;
    elements.forEach(function (element) {
        if (document.getElementById(element).classList.contains("model-builder-card-opened") === false) {
            document.getElementById(element).classList.add("model-builder-card-opened");
        }
    })
})

document.body.addEventListener("displayToastAndHighlightObjects", function (event) {
    let toastElement = document.getElementById("toast-push-notification");
    let toastBody = document.getElementById("toast-content");
    let toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastElement);

    let actionType = event.detail["action_type"];
    let modelObjectName = event.detail["name"];
    if (actionType === "delete_object"){
        toastBody.innerHTML = `${modelObjectName} has been deleted!`;
    }else if( actionType === "edit_object") {
        toastBody.innerHTML = `${modelObjectName} has been updated!`;
    }else if( actionType === "add_new_object"){
        toastBody.innerHTML = `${modelObjectName} has been saved!`;
    }

    event.detail["ids"].forEach((mirrorObjetWebId, index) => {
        if(index === 0){
            document.getElementById(`button-${mirrorObjetWebId}`).scrollIntoView(
                { behavior: "smooth", block: "center" });
        }
        highlightObjectAfterAddOrEdit(`button-${mirrorObjetWebId}`);
    })

    toastBootstrap.show();
});
