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

function highlightObject(modelObjectId){
    let element = document.getElementById(modelObjectId);
    if (element) {
        element.classList.add("highlight-border");
        setTimeout(() => {
            element.classList.remove("highlight-border");
        }, 2000);
    }
}

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
        highlightObject(`button-${mirrorObjetWebId}`);
    })

    toastBootstrap.show();
});

function displayEditIcon(modelObjectId) {
    let textElement = document.querySelector("#button-" + modelObjectId + " p");
    let editIcon = document.querySelector("#button-" + modelObjectId + " svg");

    if (!textElement) return;

    let previousHeight = textElement.offsetHeight;

    if (editIcon) {
        editIcon.classList.remove("d-none");
    }

    shave(textElement, previousHeight)
}

function hideEditIcon(modelObjectId) {
    let textElement = document.querySelector("#button-" + modelObjectId + " p");
    let editIcon = document.querySelector("#button-" + modelObjectId + " svg");

    if (editIcon) {
        editIcon.classList.add("d-none");
    }

    //replace ... with the full text
    //check if the textElement has a span with class js-shave
    //if it does, replace the textElement with the full text

    if (textElement) {
        let textElement = document.querySelector("#button-" + modelObjectId + " p");
        let shavedSpanChar = textElement.querySelector(".js-shave-char");
        let shavedSpan = textElement.querySelector(".js-shave");

        if (shavedSpan) {
            let shavedSpanContent = shavedSpan.textContent;
            shavedSpanChar.remove()
            shavedSpan.remove()
            textElement.innerHTML = textElement.textContent+" "+shavedSpanContent
        }

    }


}
