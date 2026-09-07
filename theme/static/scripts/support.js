(() => {
    let pendingFeedbackLink = null;

    function followOrdinaryLink(link) {
        pendingFeedbackLink = null;
        link.removeAttribute("aria-busy");
        link.dataset.feedbackNavigationFallback = "true";
        link.click();
    }

    function loadFeedbackPanel(link) {
        pendingFeedbackLink = link;
        link.setAttribute("aria-busy", "true");
        let request;
        try {
            request = htmx.ajax("GET", link.dataset.panelUrl || link.href, {
                target: "#sidePanel",
                swap: "innerHTML",
                source: link,
            });
        } catch (error) {
            followOrdinaryLink(link);
            return;
        }

        Promise.resolve(request).then(() => {
            if (pendingFeedbackLink !== link) return;
            pendingFeedbackLink = null;
            openSidePanel();
            document.getElementById("sidePanelTitle").focus();
        }).catch(() => {
            if (pendingFeedbackLink === link) followOrdinaryLink(link);
        }).finally(() => link.removeAttribute("aria-busy"));
    }

    function openFeedbackPanel(link) {
        const sidePanel = document.getElementById("sidePanel");
        if (!sidePanel) {
            return false;
        }

        runAfterSidePanelDiscardConfirmation(() => loadFeedbackPanel(link));
        return true;
    }

    document.addEventListener("click", (event) => {
        const link = event.target.closest?.('[data-action="open-feedback"]');
        if (!link) return;
        if (link.dataset.feedbackNavigationFallback === "true") {
            delete link.dataset.feedbackNavigationFallback;
            return;
        }
        if (openFeedbackPanel(link)) event.preventDefault();
    });

    document.body.addEventListener("htmx:responseError", (event) => {
        if (pendingFeedbackLink && event.detail?.elt === pendingFeedbackLink) {
            followOrdinaryLink(pendingFeedbackLink);
        }
    });

    document.addEventListener("change", (event) => {
        const selector = event.target.closest?.('[data-action="select-feedback-kind"]');
        if (!selector) return;
        const container = selector.closest("#sidePanelContent, section");
        container?.querySelectorAll("[data-feedback-destination]").forEach((link) => {
            link.href = selector.value === "feedback" ? link.dataset.urlFeedback : link.dataset.urlBug;
        });
    });
})();
