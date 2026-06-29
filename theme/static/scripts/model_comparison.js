// Model-comparison workspace UI: client-side model switching across two resident canvases, plus the
// resident comparison view.
//
// Both canvases live in the DOM at once; switching is a visibility toggle (no canvas re-render), so it
// is instant and preserves each canvas's transient state. The catch: the active canvas must carry the
// canonical structural ids (`server-list`, `btn-add-server`, the tour targets…) so every existing
// add/edit flow, Sortable, the tour and the E2E selectors keep working unchanged, while the parked
// canvas carries `-{slot}`-suffixed ids so nothing collides. On switch we migrate those canonical ids
// (and tour targets) from the old active canvas to the new one. Object-card ids are already namespaced
// by the system-id web_id prefix, so they are never touched here.
//
// The comparison dashboard is a third resident sibling: an empty `#comparison-view` block in normal
// flow below the tab strip. Opening Compare hides the toolbar + canvas region and shows that block
// (the same `display` toggle the canvases use); dismissing to a model hides it again and reveals the
// canvas — a client-side reveal, never a reload. The comparison fragment is fetched fresh each open and
// emptied (its three Chart.js instances destroyed) on leave, so results are never stale.
//
// Opening Compare is non-destructive: the side panel / help drawer / results all live inside the hidden
// builder page, so they survive behind the dashboard. A capture-phase model-tab handler dismisses the
// dashboard before HTMX's switch request runs — a same-slot click then resumes the preserved panel with
// no POST and no unsaved warning, while a cross-slot click lets the switch (and its unsaved guard) run
// over the now-revealed edited model.
//
// IIFE + data-action dispatch per conventions.md (keeps window clean, survives HTMX swaps).
(function () {
    "use strict";

    function canvasFor(slot) {
        return document.querySelector(`[data-model-canvas="${slot}"]`);
    }

    function comparisonView() {
        return document.getElementById("comparison-view");
    }

    function comparisonIsOpen() {
        const view = comparisonView();
        return !!view && !view.classList.contains("d-none");
    }

    // Re-key a canvas's structural elements. When `canonical`, restore the bare data-canvas-id (the
    // active canvas); otherwise suffix it with the slot (a parked canvas). Tour targets ride along: the
    // active canvas owns them so the tour and its replay anchor on the visible model.
    function rekeyCanvas(canvas, slot, canonical) {
        if (!canvas) return;
        canvas.querySelectorAll("[data-canvas-id]").forEach(el => {
            const base = el.dataset.canvasId;
            el.id = canonical ? base : `${base}-${slot}`;
        });
        const tourMap = {
            "usage-pattern-container": "usage-patterns",
            "usage-journey-container": "usage-journeys",
            "server-container": "infrastructure",
        };
        canvas.querySelectorAll("[data-canvas-id]").forEach(el => {
            const target = tourMap[el.dataset.canvasId];
            if (!target) return;
            if (canonical) {
                el.setAttribute("data-tour-target", target);
            } else {
                el.removeAttribute("data-tour-target");
            }
        });
    }

    // Toggle the active-tab styling (background, border, weight) on a tab wrapper. Shared by the model
    // tabs and the ⇄Compare tab so both wear the same active highlight.
    //
    // The visible bold/mute lives on the inner .model-tab__label button, NOT the wrapper: a Bootstrap
    // .btn pins its own font-weight, so the wrapper's fw-bold never reaches the label text. The server
    // bakes fw-bold/text-muted onto the label too, and switch-model never re-renders the strip — so
    // unless we sync the label here, the slot that was active at page-render time keeps its bold label
    // across every client-side switch (the Reference tab staying bold behind the comparison view on
    // mobile was this bug). Toggle the label in lock-step with the wrapper.
    function setTabActive(tab, active) {
        tab.classList.toggle("fw-bold", active);
        tab.classList.toggle("bg-white", active);
        tab.classList.toggle("border", active);
        tab.classList.toggle("border-bottom-0", active);
        tab.classList.toggle("text-muted", !active);

        const label = tab.querySelector(".model-tab__label");
        if (label) {
            label.classList.toggle("fw-bold", active);
            label.classList.toggle("text-muted", !active);
        }
    }

    // The ⇄Compare tab's wrapper (null-safe — the tab may be absent in a single-model session).
    function compareTabWrapper() {
        return document.getElementById("compare-tab")?.closest(".model-tab");
    }

    // Toggle the active-model styling on the tab whose slot matches (or clear it entirely when `slot` is
    // null — the state while the comparison view is open, since no model is being edited).
    function highlightActiveTab(slot) {
        document.querySelectorAll("[data-model-tab]").forEach(label => {
            const isTarget = slot !== null && String(label.dataset.modelTab) === String(slot);
            // The active styling (background, border, weight) lives on the tab wrapper so it spans both
            // the label and the ✕; fall back to the label itself if a future tab has no wrapper.
            setTabActive(label.closest(".model-tab") || label, isTarget);
        });
    }

    // Show/hide the builder chrome (toolbar + canvas region) opposite the comparison view, and flip the
    // `.comparing` body class the SCSS keys the mobile strip reveal on.
    function setBuilderHidden(hidden) {
        ["toolbar-nav", "model-builder-page"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.toggle("d-none", hidden);
        });
        document.body.classList.toggle("comparing", hidden);
    }

    // Open the comparison view (driven by the swap into #comparison-view). Hide the builder chrome, clear
    // the active-model highlight, mark the ⇄Compare tab active (it stays visible + highlighted on desktop
    // as the active destination; CSS hides it on mobile so the two model tabs fit), and tear down the
    // builder's leader lines (the canvas is now d-none; the lines' SVGs live on <body> and would otherwise
    // recompute against disconnected anchors). Opening Compare is now non-destructive: the side panel /
    // help drawer / results panel all live inside the (now d-none) builder page, so they ride along hidden
    // and survive intact — a same-slot return reveals them exactly as they were left, with no warning.
    function openCompareView() {
        setBuilderHidden(true);

        highlightActiveTab(null);

        const compareWrapper = compareTabWrapper();
        if (compareWrapper) setTabActive(compareWrapper, true);

        if (typeof window.removeAllLines === "function") {
            window.removeAllLines();
        }
    }

    // Dismiss the comparison view: reveal the builder, clear the ⇄Compare tab's active styling and restore
    // the active-model highlight, then empty #comparison-view (destroying its three charts so Chart.js
    // doesn't leak canvas registrations across reopen). The caller (switchToSlot) rebuilds the visible
    // canvas's lines.
    function dismissCompareView() {
        setBuilderHidden(false);

        const compareWrapper = compareTabWrapper();
        if (compareWrapper) setTabActive(compareWrapper, false);

        const strip = document.getElementById("model-tab-strip");
        if (strip) highlightActiveTab(strip.dataset.activeSlot);

        if (typeof window.destroyComparisonCharts === "function") {
            window.destroyComparisonCharts();
        }
        const view = comparisonView();
        if (view) {
            view.innerHTML = "";
            view.classList.add("d-none");
        }
    }

    function switchToSlot(slot) {
        const strip = document.getElementById("model-tab-strip");
        if (!strip) return;

        // switchToSlot only runs off the switchModelCanvas trigger, which fires from a /switch-model/ POST
        // — and the capture-phase tab handler below always dismisses the comparison view *before* that POST
        // is issued, so Compare is never open here. switchToSlot is therefore a plain client-side model
        // switch (the capture handler owns all Compare-dismiss).
        const previousSlot = strip.dataset.activeSlot;
        if (String(previousSlot) === String(slot)) {
            // Redundant same-slot click — a no-op. Re-initialising the whole builder on every such click
            // would needlessly re-wire Sortable and rebuild every leader line.
            return;
        }

        // Hand the canonical ids from the outgoing canvas back to suffixed form, then promote the
        // incoming canvas to canonical — order matters so the canonical ids never momentarily collide.
        rekeyCanvas(canvasFor(previousSlot), previousSlot, false);
        rekeyCanvas(canvasFor(slot), slot, true);

        document.querySelectorAll("[data-model-canvas]").forEach(canvas => {
            const isTarget = String(canvas.dataset.modelCanvas) === String(slot);
            canvas.classList.toggle("d-none", !isTarget);
        });
        highlightActiveTab(slot);
        strip.dataset.activeSlot = slot;

        // The side panel, help drawer and results panel are singletons bound to the active slot, so
        // their open content (an object's edit form, a class help page, a model's chart) belongs to the
        // model we are leaving — leaving them open strands stale content over the now-active canvas (and
        // a side-panel save would target the wrong model). Close them so the now-active model starts
        // clean. The help drawer self-closes from its own module on this same switch event.
        const sidePanel = document.getElementById("sidePanel");
        if (sidePanel && !sidePanel.classList.contains("d-none") && typeof window.closeAndEmptySidePanel === "function") {
            window.closeAndEmptySidePanel();
        }
        // Results: the switch OOB-rebinds the (newly visible) "Results" bar over the still-open panel,
        // leaving the bar mid-air above a blank canvas. A non-empty #result-block is the open signal
        // that survives that OOB clobber.
        const resultBlock = document.getElementById("result-block");
        if (resultBlock && resultBlock.innerHTML.trim() !== "" && typeof window.hidePanelResult === "function") {
            window.hidePanelResult();
        }

        // Sortable and leader lines were wired against the previously-visible canvas; re-init so the
        // now-active canvas's lists are draggable and only its (visible) lines are drawn.
        if (typeof window.initModelBuilderMain === "function") {
            window.initModelBuilderMain();
        }
    }

    document.body.addEventListener("switchModelCanvas", function (event) {
        const slot = event.detail && event.detail.slot;
        if (slot !== undefined && slot !== null) {
            switchToSlot(slot);
        }
    });

    // Capture-phase model-tab handler, active only while the comparison view is open. A model tab means
    // "leave Compare and edit this model", so dismiss the dashboard *first* — before HTMX's bubble-phase
    // switch-model POST and its unsaved-changes guard run. The dismiss reveals the previously-active
    // canvas, so we rebuild its leader lines here; then the two outcomes diverge:
    //   • Same slot  → the model we are returning to. No switch is needed (its canvas + open panel are
    //     simply revealed by the dismiss), so preventDefault the click: no /switch-model/ POST, hence no
    //     spurious unsaved warning about losing edits while returning to the model that keeps them.
    //   • Other slot → let the POST proceed. With the dashboard already torn down, the switch's unsaved
    //     modal lands over the now-revealed edited model (not over the comparison); switchToSlot then
    //     performs the actual cross-slot reveal on the resulting switchModelCanvas trigger (and rebuilds
    //     the now-active canvas's lines). If the user cancels that warning instead, they stay anchored on
    //     this revealed model — with its lines already rebuilt here.
    // Capture phase so it runs ahead of HTMX's document-level (bubble-phase) request handling.
    document.addEventListener("click", function (event) {
        if (!comparisonIsOpen()) return;
        const label = event.target.closest("[data-model-tab]");
        if (!label) return;

        const strip = document.getElementById("model-tab-strip");
        const previousSlot = strip ? strip.dataset.activeSlot : null;
        const isSameSlot = String(label.dataset.modelTab) === String(previousSlot);

        dismissCompareView();
        if (typeof window.initModelBuilderMain === "function") {
            window.initModelBuilderMain();
        }

        if (isSameSlot) {
            event.preventDefault();
            event.stopPropagation();
        }
    }, true);

    // The comparison fragment is swapped into the resident #comparison-view block; reveal it and hide
    // the builder around it (openCompareView). Builder→builder swaps and the OOB-only switch never hit
    // this block, so the toggle fires exactly when Compare opens.
    document.body.addEventListener("htmx:afterSwap", function (event) {
        if (event.target && event.target.id === "comparison-view") {
            event.target.classList.remove("d-none");
            openCompareView();
        }
    });

    // Confirm before removing the second model (live-state confirm, body-delegated so it survives swaps).
    // remove-model replaces the whole builder, discarding an open side panel. It has its own destructive
    // confirm (not the shared unsaved modal), so the two never stack; instead fold the unsaved-changes
    // warning into this single dialog when the open panel has pending edits.
    document.body.addEventListener("htmx:confirm", function (evt) {
        const elt = evt.target.closest("[data-confirm-remove-model]");
        if (!elt) return;
        evt.preventDefault();
        let message = elt.getAttribute("data-confirm-remove-model");
        if (typeof window.isSidePanelFormModified === "function" && window.isSidePanelFormModified()) {
            message += " You also have unsaved changes in the open panel that will be lost.";
        }
        if (window.confirm(message)) {
            evt.detail.issueRequest(true);
        }
    });

    // Open the "+Add → Import from file" side panel from its data-action (the dropdown item can't carry
    // hx-* and lives inside a Bootstrap menu that closes on click, so a delegated handler opens it).
    document.body.addEventListener("click", function (evt) {
        const trigger = evt.target.closest('[data-action="open-add-model-import"]');
        if (!trigger) return;
        evt.preventDefault();
        if (window.htmx) {
            window.htmx.ajax("GET", "/model_builder/open-add-model-import-panel/", { target: "#sidePanel", swap: "innerHTML" });
        }
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { rekeyCanvas, switchToSlot, openCompareView, dismissCompareView };
    }
})();
