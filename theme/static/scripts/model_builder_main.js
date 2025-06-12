function initModelBuilderMain() {
    initLeaderLines();
    initSortableObjectCards();
    initGrabEffect();
    initHammer();
}

function initSortableObjectCards() {
    const options = {
        animation: 150,
        onStart: () => {
            document.querySelectorAll('.grabbing').forEach(el => {
                el.classList.remove('grabbing');
            });
        },
        onEnd: () =>{
            document.querySelectorAll('.grabbing').forEach(el => {
                el.classList.remove('grabbing');
            });
            updateLines();
        }
    };

    new Sortable(document.getElementById("up-list"), options);
    new Sortable(document.getElementById("uj-list"), options);
    new Sortable(document.getElementById("server-list"), options);
}

let timer = null;

function initGrabEffect() {
    document.querySelectorAll(".grab").forEach(element => {
        if (element.dataset.grabListenerAdded === "true") {
            return;
        }
        element.addEventListener("mousedown", e => {
            timer = setTimeout(() => {
                element.classList.add('grabbing');
            }, 200);
        });
        ["mouseup", "mouseleave"].forEach(event => {
            element.addEventListener(event, () => {
                element.classList.remove('grabbing');
                clearTimeout(timer);
                timer = null;
            });
        });
        element.dataset.grabListenerAdded = "true";
    });
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

function hideEditIcons(){
    let editIcons = document.querySelectorAll("[id^='edit-icon-']");
    editIcons.forEach(icon => {
        icon.classList.add("d-none");
    })
}

function removeAllOpenedObjectsHighlights(){
    hideEditIcons();
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
    const container = document.getElementById("model-canva-scrollable-area");

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
        if (index === 0) {
        const element = document.getElementById(`button-${mirrorObjetWebId}`);
        if (element) {
            const rect = element.getBoundingClientRect();
            if (rect.top < 0 || rect.bottom > window.innerHeight) {
                setTimeout(() => {
                    element.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }, 100);
            }
        }
    }
        highlightObjectAfterAddOrEdit(`button-${mirrorObjetWebId}`);
    })

    toastBootstrap.show();
});


function scrollToRight() {
    const wrapper = document.getElementById("model-canva-scrollable-area");
    if (!wrapper) return;

    const scrollAmount = wrapper.clientWidth / 2;
    wrapper.scrollBy({
        left: scrollAmount,
        behavior: 'smooth'
    });
}

function scrollToLeft() {
    const wrapper = document.getElementById("model-canva-scrollable-area");
    if (!wrapper) return;

    const scrollAmount = wrapper.clientWidth / 2;
    wrapper.scrollBy({
        left: -scrollAmount,
        behavior: 'smooth'
    });
}

function updateScrollButtons(){
        const wrapper = document.getElementById("model-canva-scrollable-area");
        const btnRight = document.getElementById("model-scroll-to-right");
        const btnLeft = document.getElementById("model-scroll-to-left");
        const maxScrollLeft = wrapper.scrollWidth - wrapper.clientWidth;
        const currentScroll = wrapper.scrollLeft;

        if (btnRight) {
            if (Math.ceil(currentScroll) >= maxScrollLeft) {
                btnRight.classList.remove("d-block");
                btnRight.classList.add("d-none");
            } else {
                btnRight.classList.remove("d-none");
                btnRight.classList.add("d-block");
            }
        }

        if (btnLeft) {
            if (Math.floor(currentScroll) <= 0) {
                btnLeft.classList.remove("d-block");
                btnLeft.classList.add("d-none");
            } else {
                btnLeft.classList.remove("d-none");
                btnLeft.classList.add("d-block");
            }
        }
    }

document.addEventListener("DOMContentLoaded", () => {
    const wrapper = document.getElementById("model-canva-scrollable-area");
    if (!wrapper) return;
    wrapper.addEventListener("scroll", updateScrollButtons);
    updateScrollButtons();
});
