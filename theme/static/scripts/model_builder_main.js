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


function addLongPressListener(selector, callback, delay = 300) {
    let timer = null;

    document.querySelectorAll(selector).forEach(element => {
        element.addEventListener('mousedown', e => {
            timer = setTimeout(() => {
                callback(e, element);
            }, delay);
        });

        ['mouseup', 'mouseleave'].forEach(event => {
            element.addEventListener(event, () => {
                clearTimeout(timer);
                timer = null;
            });
        });
    });
}

addLongPressListener('.grab', (e, el) => {
    el.classList.add('grabbing');
});

document.addEventListener('mouseup', () => {
    document.querySelectorAll('.grabbing').forEach(el => {
        el.classList.remove('grabbing');
    });
});

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

function scrollToRight() {
    const wrapper = document.getElementById("model-canva-wrapper");
    if (!wrapper) return;

    const scrollAmount = wrapper.clientWidth / 2;
    wrapper.scrollBy({
        left: scrollAmount,
        behavior: 'smooth'
    });
}

function scrollToLeft() {
    const wrapper = document.getElementById("model-canva-wrapper");
    if (!wrapper) return;

    const scrollAmount = wrapper.clientWidth / 2;
    wrapper.scrollBy({
        left: -scrollAmount,
        behavior: 'smooth'
    });
}


document.addEventListener("DOMContentLoaded", () => {
    const wrapper = document.getElementById("model-canva-wrapper");
    const btnRight = document.getElementById("model-scroll-to-right");
    const btnLeft = document.getElementById("model-scroll-to-left");

    if (!wrapper) return;

    const updateScrollButtons = () => {
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
    };

    wrapper.addEventListener("scroll", updateScrollButtons);

    // Appelle une première fois au chargement
    updateScrollButtons();
});


