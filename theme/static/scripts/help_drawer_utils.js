function openHelpDrawer() {
    const helpDrawer = document.getElementById("helpDrawer");
    helpDrawer.classList.remove("d-none");
    const scrollTarget = document.getElementById("helpDrawerTitle");
    if (scrollTarget) {
        helpDrawer.scrollTo({ top: scrollTarget.offsetTop, behavior: "smooth" });
    }
}

function closeHelpDrawer() {
    const helpDrawer = document.getElementById("helpDrawer");
    helpDrawer.classList.add("d-none");
    helpDrawer.innerHTML = "";
}

document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "sidePanel") {
        closeHelpDrawer();
    }
});
