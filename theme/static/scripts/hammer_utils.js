function displayPanelResult(){
    let panel = document.getElementById("panel-result-btn");
    let btn = document.getElementById("btn-open-panel-result");
    let resultDiv = document.getElementById("result-block");
    panel.style.transition = "height 0.2s ease-in-out";
    panel.style.height = getComputedStyle(document.documentElement).getPropertyValue("--result-panel-opened");
    resultDiv.style.height = getComputedStyle(document.documentElement).getPropertyValue("--result-panel-opened");
    btn.style.display = "none";
}

function hidePanelResult(){
    let panel = document.getElementById("panel-result-btn");
    let btn = document.getElementById("btn-open-panel-result");
    let resultDiv = document.getElementById("result-block");
    panel.style.transition = "height 0.2s ease-in-out";
    panel.style.height = getComputedStyle(document.documentElement).getPropertyValue("--open-result-btn");
    btn.style.display = "block";
    resultDiv.innerHTML = "";
    resultDiv.style.height = "0px";
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
