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
