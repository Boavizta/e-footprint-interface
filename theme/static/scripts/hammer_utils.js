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

    var scrollableArea = document.getElementById("model-canva-scrollable-area");
    if (scrollableArea) {
        scrollableArea.classList.remove("overflow-x-auto");
        scrollableArea.classList.add("overflow-x-hidden");
    }
}

// OOB button replacement restores server attributes during settlement, after the panel's
// inline initialization ran. Reapply the open panel's layout once those swaps have settled.
document.body.addEventListener("htmx:afterSettle", () => {
    const panel = document.getElementById("panel-result-btn");
    const results = document.getElementById("result-block");
    if (panel?.style.height === "100%" && results?.style.display !== "none" && results?.innerHTML.trim()) {
        displayPanelResult();
    }
});

function hidePanelResult() {
    exitResultFullscreen();
    var panel = document.getElementById("panel-result-btn");
    var resultDiv = document.getElementById("result-block");

    panel.style.height = "";
    resultDiv.style.height = "";

    if (document.getElementById("sidePanel").classList.contains("d-none")) {
        resultDiv.classList.remove("w-100");
    } else {
        resultDiv.classList.remove("result-width");
    }
    var scrollableArea = document.getElementById("model-canva-scrollable-area");
    if (scrollableArea) {
        scrollableArea.classList.remove("overflow-x-hidden");
        scrollableArea.classList.add("overflow-x-auto");
    }

    function emptyResultPanel() {
        // A refresh arriving while we close can initialize the open-panel layout again.
        panel.style.height = "";
        resultDiv.style.height = "";
        resultDiv.innerHTML = "";
        resultDiv.style.display = "";
        document.getElementById("btn-open-panel-result").style.display = "block";
    }

    function hasPendingResponse() {
        var pending = ".htmx-request, .htmx-settling, .htmx-added";
        return resultDiv.matches(pending) || resultDiv.querySelector(pending);
    }
    if (hasPendingResponse()) {
        resultDiv.style.display = "none";
        // Keep response targets attached until their own requests and swaps finish.
        function finishClosing() {
            if (hasPendingResponse()) return;
            resultDiv.removeEventListener("htmx:afterRequest", finishClosing);
            resultDiv.removeEventListener("htmx:afterSettle", finishClosing);
            emptyResultPanel();
        }
        resultDiv.addEventListener("htmx:afterRequest", finishClosing);
        resultDiv.addEventListener("htmx:afterSettle", finishClosing);
        return;
    }

    emptyResultPanel();
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
