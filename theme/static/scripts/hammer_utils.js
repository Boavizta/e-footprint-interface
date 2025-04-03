function displayPanelResult(){
    let panel = document.getElementById("panel-result-btn");
    let btn = document.getElementById("btn-open-panel-result");
    panel.style.transition = "height 0.2s ease-in-out";
    panel.style.height = "93vh";
    btn.style.display = "none";
}

function hidePanelResult(){
    let panel = document.getElementById("panel-result-btn");
    let btn = document.getElementById("btn-open-panel-result");
    let resultDiv = document.getElementById("result-block");
    panel.style.transition = "height 0.2s ease-in-out";
    panel.style.height = "5vh";
    btn.style.transition = "height 0.2s ease-in-out";
    btn.style.height = "5vh";
    btn.style.display = "block";
    resultDiv.innerHTML = "";
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
