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
    let icon = document.getElementById('icon_accordion_'+objectId);
    if (icon.classList.contains('chevron-rotate')) {
        icon.classList.remove('chevron-rotate');
    }
    else {
        icon.classList.add('chevron-rotate');
    }
    updateLines();
}


function resizeSystemNameHeader() {
    let systemNameHeader = document.getElementById('SystemNameHeader');

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
        element.classList.add('highlight-border');
        setTimeout(() => {
            element.classList.remove('highlight-border');
        }, 2000);
    }
}

document.body.addEventListener('highlightObject', function (event) {
    let toastElement = document.getElementById('toast-push-notification');
    let toastBody = document.getElementById('toast-content');
    let toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastElement);
    let toastMessage;
    let actionOnModel = event.detail['actionOnModel'];

    let modelObjectName = event.detail['name'];

    if (actionOnModel === 'delete_object'){
        toastMessage = `${modelObjectName} has been deleted!`;
    }else{
         if( actionOnModel === 'edit_object') {
             toastMessage = `${modelObjectName} has been updated!`;
         }else if( actionOnModel === 'add_new_object'){
            toastMessage = `${modelObjectName} has been saved!`;
        }
         if(event.detail['mirroredCardIds']){
            let mirrorObjetWebIds = event.detail['mirroredCardIds'];
            mirrorObjetWebIds.forEach((mirrorObjetWebId, index) => {
                if(index === 0){
                    document.getElementById(`button-${mirrorObjetWebId}`).scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                highlightObject(`button-${mirrorObjetWebId}`);
            })
        }else{
            let mirrorObjetsId = event.detail['id'];
            document.getElementById(mirrorObjetsId).scrollIntoView({ behavior: 'smooth', block: 'center' });
            highlightObject(mirrorObjetsId);
        }
    }

    toastBody.innerHTML = toastMessage;
    toastBootstrap.show();
});

