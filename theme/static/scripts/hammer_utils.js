function enterResultFullscreen() {
    if (window.innerWidth >= 1200) return;
    var navbar = document.querySelector("nav.navbar");
    var toolbar = document.getElementById("toolbar-nav");
    if (navbar) navbar.style.display = "none";
    if (toolbar) toolbar.style.display = "none";
    document.documentElement.style.setProperty("--navbar-height", "0px");
    document.documentElement.style.setProperty("--toolbar-height", "0px");
}

function exitResultFullscreen() {
    var navbar = document.querySelector("nav.navbar");
    var toolbar = document.getElementById("toolbar-nav");
    if (navbar) navbar.style.display = "";
    if (toolbar) toolbar.style.display = "";
    document.documentElement.style.setProperty("--navbar-height", "50px");
    document.documentElement.style.setProperty("--toolbar-height", "48px");
}


function displayPanelResult(){
    enterResultFullscreen();
    let panel = document.getElementById("panel-result-btn");
    let btn = document.getElementById("btn-open-panel-result");
    let resultDiv = document.getElementById("result-block");
    panel.style.transition = "height 0.2s ease-in-out";
    panel.style.minHeight = getComputedStyle(document.documentElement).getPropertyValue("--result-panel-opened");
    resultDiv.style.minHeight = getComputedStyle(document.documentElement).getPropertyValue("--result-panel-opened");

    if(document.getElementById("sidePanel").classList.contains("d-none")){
        panel.classList.add("w-100");
    }else{
        panel.classList.remove("w-100");
        panel.classList.add("result-width");
    }
    btn.style.display = "none";
}

function hidePanelResult(){
    exitResultFullscreen();
    let panel = document.getElementById("panel-result-btn");
    let btn = document.getElementById("btn-open-panel-result");
    let resultDiv = document.getElementById("result-block");
    panel.style.transition = "height 0.2s ease-in-out";
    panel.style.minHeight = getComputedStyle(document.documentElement).getPropertyValue("--open-result-btn");
    btn.style.display = "block";
    resultDiv.innerHTML = "";
    resultDiv.style.height = "0px";
    if(document.getElementById("sidePanel").classList.contains("d-none")){
        resultDiv.classList.remove("w-100");
    }else{
        resultDiv.classList.remove("result-width");
    }
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
