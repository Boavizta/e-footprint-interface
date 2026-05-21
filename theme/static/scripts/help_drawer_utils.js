// Bootstrap's default popover sanitizer strips data-* attributes from rendered HTML, which would
// drop the data-help-class hook on {class:X} placeholder links injected via data-bs-content.
// Extend the global allow-list once at script load so every popover preserves the attribute.
if (window.bootstrap && bootstrap.Tooltip && bootstrap.Tooltip.Default.allowList) {
    const allowList = bootstrap.Tooltip.Default.allowList;
    allowList.a = [...(allowList.a || []), "data-help-class"];
}

function openHelpDrawer() {
    const helpDrawer = document.getElementById("helpDrawer");
    helpDrawer.classList.remove("d-none");
    expandRightColumn();
    const scrollTarget = document.getElementById("helpDrawerTitle");
    if (scrollTarget) {
        helpDrawer.scrollTo({ top: scrollTarget.offsetTop, behavior: "smooth" });
    }
}

function closeHelpDrawer() {
    const helpDrawer = document.getElementById("helpDrawer");
    helpDrawer.classList.add("d-none");
    helpDrawer.innerHTML = "";
    const sidePanel = document.getElementById("sidePanel");
    if (sidePanel.classList.contains("d-none")) {
        collapseRightColumn();
    }
}

document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "sidePanel") {
        closeHelpDrawer();
    }
});

// Delegated handler for {class:X} placeholder links emitted by handle_class.
// Gating on [data-help-class] avoids double-firing on the canvas "?" button, which
// shares the .help-drawer-trigger class but drives its own hx-get/hx-target.
document.body.addEventListener("click", function (event) {
    const trigger = event.target.closest(".help-drawer-trigger[data-help-class]");
    if (!trigger) return;
    event.preventDefault();

    // Dismiss any popover/tooltip the trigger lives inside so the help drawer surfaces cleanly.
    document.querySelectorAll('[aria-describedby^="popover"], [aria-describedby^="tooltip"]').forEach(el => {
        const popInst = bootstrap.Popover.getInstance(el);
        if (popInst) popInst.hide();
        const tipInst = bootstrap.Tooltip.getInstance(el);
        if (tipInst) tipInst.hide();
    });

    const className = trigger.dataset.helpClass;
    htmx.ajax(
        "GET",
        `/model_builder/open-help-drawer/${className}/`,
        { target: "#helpDrawer", swap: "innerHTML" }
    );
});
