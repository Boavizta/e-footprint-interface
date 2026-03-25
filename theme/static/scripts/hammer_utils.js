function enterResultFullscreen() {
    if (window.innerWidth >= 1200) return;
    var toolbar = document.getElementById("toolbar-nav");
    if (toolbar) toolbar.style.display = "none";
}

function exitResultFullscreen() {
    var toolbar = document.getElementById("toolbar-nav");
    if (toolbar) toolbar.style.display = "";
}

function displayPanelResult() {
    enterResultFullscreen();
    var panel = document.getElementById("panel-result-btn");
    var btn = document.getElementById("btn-open-panel-result");
    var resultDiv = document.getElementById("result-block");

    panel.style.height = "100%";
    resultDiv.style.height = "100%";

    if (document.getElementById("sidePanel").classList.contains("d-none")) {
        panel.classList.add("w-100");
    } else {
        panel.classList.remove("w-100");
        panel.classList.add("result-width");
    }
    btn.style.display = "none";
}

function hidePanelResult() {
    exitResultFullscreen();
    var panel = document.getElementById("panel-result-btn");
    var btn = document.getElementById("btn-open-panel-result");
    var resultDiv = document.getElementById("result-block");

    panel.style.height = "";
    resultDiv.innerHTML = "";
    resultDiv.style.height = "";

    if (document.getElementById("sidePanel").classList.contains("d-none")) {
        resultDiv.classList.remove("w-100");
    } else {
        resultDiv.classList.remove("result-width");
    }
    btn.style.display = "block";
}

function initHammer() {
    window.modalTrigger = new Hammer(document.getElementById('panel-result-btn'));
    window.modalTrigger.get('swipe').set({ direction: Hammer.DIRECTION_VERTICAL });
    window.modalTrigger.on("swipeup", function () {
        document.getElementById('btn-open-panel-result').click();
    });
    window.modalTrigger.on("swipedown", function () {
        hidePanelResult();
    });
}
