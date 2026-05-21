/* Help drawer overlay — open/close the #helpDrawer layer and route entry points to it.
   Templates declare intent with `data-action="open-help-drawer"` / `data-action="close-help-drawer"`;
   a single delegated dispatcher does the work. Nothing escapes to `window`.
   See conventions.md → JavaScript. */
(function () {
    /* Bootstrap's default sanitizer strips <button> and data-* attributes from rendered
       popover/tooltip content. {class:X} placeholders render as <button data-action=...
       data-help-class=...>, so popovers (which inject content into a DOM subtree HTMX
       never processed) would otherwise lose both the tag and the dispatch attributes. */
    const allowList = bootstrap.Tooltip.Default.allowList;
    allowList.button = [...(allowList.button || []), "type", "data-action", "data-help-class"];

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

    /* Bootstrap puts popover/tooltip content inside a `.popover` / `.tooltip` wrapper whose
       id is referenced by the trigger element's `aria-describedby`. Walk that chain to dismiss
       only the popover the user actually clicked through. */
    function dismissEnclosingPopover(triggerEl) {
        const wrapper = triggerEl.closest(".popover, .tooltip");
        if (!wrapper?.id) return;
        const popoverTrigger = document.querySelector(`[aria-describedby="${wrapper.id}"]`);
        if (!popoverTrigger) return;
        const inst = bootstrap.Popover.getInstance(popoverTrigger)
            || bootstrap.Tooltip.getInstance(popoverTrigger);
        if (inst) inst.hide();
    }

    function openHelpForClass(className) {
        htmx.ajax(
            "GET",
            `/model_builder/open-help-drawer/${className}/`,
            { target: "#helpDrawer", swap: "innerHTML" }
        );
    }

    /* ===== Delegated dispatcher ===== */

    document.body.addEventListener("click", function (event) {
        const target = event.target.closest("[data-action]");
        if (!target) return;
        switch (target.dataset.action) {
            case "open-help-drawer":
                event.preventDefault();
                dismissEnclosingPopover(target);
                openHelpForClass(target.dataset.helpClass);
                break;
            case "close-help-drawer":
                event.preventDefault();
                closeHelpDrawer();
                break;
        }
    });

    /* React to swaps into either drawer. Help-drawer swap auto-opens the layer and inits
       its popovers (the inline script that used to live in help_drawer_structure.html);
       side-panel swap auto-closes the help drawer so the side panel takes over. */
    document.body.addEventListener("htmx:afterSwap", function (event) {
        const swapTarget = event.detail.target;
        if (!swapTarget) return;
        if (swapTarget.id === "helpDrawer") {
            openHelpDrawer();
            swapTarget.querySelectorAll('[data-bs-toggle="popover"][data-location="help_drawer"]')
                .forEach(el => bootstrap.Popover.getOrCreateInstance(el));
        } else if (swapTarget.id === "sidePanel") {
            closeHelpDrawer();
        }
    });
})();
