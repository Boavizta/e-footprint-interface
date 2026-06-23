// Model-comparison workspace UI: client-side model switching across two resident canvases.
//
// Both canvases live in the DOM at once; switching is a visibility toggle (no canvas re-render), so it
// is instant and preserves each canvas's transient state. The catch: the active canvas must carry the
// canonical structural ids (`server-list`, `btn-add-server`, the tour targets…) so every existing
// add/edit flow, Sortable, the tour and the E2E selectors keep working unchanged, while the parked
// canvas carries `-{slot}`-suffixed ids so nothing collides. On switch we migrate those canonical ids
// (and tour targets) from the old active canvas to the new one. Object-card ids are already namespaced
// by the system-id web_id prefix, so they are never touched here.
//
// IIFE + data-action dispatch per conventions.md (keeps window clean, survives HTMX swaps).
(function () {
    "use strict";

    function canvasFor(slot) {
        return document.querySelector(`[data-model-canvas="${slot}"]`);
    }

    function activeCanvas() {
        const strip = document.getElementById("model-tab-strip");
        return strip ? canvasFor(strip.dataset.activeSlot) : null;
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

    function switchToSlot(slot) {
        const strip = document.getElementById("model-tab-strip");
        if (!strip) return;

        // On the Compare dashboard there are no resident canvases — clicking a model tab means "leave
        // the comparison and edit this model". The switch-model POST already persisted the active slot,
        // so reload the builder (which opens on that slot). Guard on canvas presence, not a flag, so the
        // shared tab strip stays unchanged. No URL to reconcile: Compare deliberately does not push
        // /compare/ (see model_tab_strip.html), so the bar already reads /model_builder/.
        if (!document.querySelector("[data-model-canvas]")) {
            if (window.htmx) {
                window.htmx.ajax("GET", "/model_builder/", { target: "#main-content-block", swap: "innerHTML" });
            }
            return;
        }

        const previousSlot = strip.dataset.activeSlot;
        if (String(previousSlot) === String(slot)) return;

        // Hand the canonical ids from the outgoing canvas back to suffixed form, then promote the
        // incoming canvas to canonical — order matters so the canonical ids never momentarily collide.
        rekeyCanvas(canvasFor(previousSlot), previousSlot, false);
        rekeyCanvas(canvasFor(slot), slot, true);

        document.querySelectorAll("[data-model-canvas]").forEach(canvas => {
            const isTarget = String(canvas.dataset.modelCanvas) === String(slot);
            canvas.classList.toggle("d-none", !isTarget);
        });
        document.querySelectorAll("[data-model-tab]").forEach(label => {
            const isTarget = String(label.dataset.modelTab) === String(slot);
            // The active styling (background, border, weight) lives on the tab wrapper so it spans both
            // the label and the ✕; fall back to the label itself if a future tab has no wrapper.
            const tab = label.closest(".model-tab") || label;
            tab.classList.toggle("fw-bold", isTarget);
            tab.classList.toggle("bg-white", isTarget);
            tab.classList.toggle("border", isTarget);
            tab.classList.toggle("border-bottom-0", isTarget);
            tab.classList.toggle("text-muted", !isTarget);
        });
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

    // Leaving the builder for a canvas-less layout (the ⇄Compare dashboard) tears down the builder's
    // leader lines. The lines' SVGs live on <body>, outside #main-content-block, so the dashboard swap
    // does not remove them — and each LeaderLine keeps its own resize/scroll listeners that would then
    // recompute against now-disconnected anchors and throw ("disconnected element" / "Cannot read
    // properties of null"). Removing them on the swap into a no-canvas layout is the only reliable fix
    // (our updateLines guard can't stop the library's internal listeners). Builder→builder swaps keep
    // their canvases, so this never strips lines that initModelBuilderMain is about to reuse.
    document.body.addEventListener("htmx:afterSwap", function (event) {
        if (event.target && event.target.id !== "main-content-block") return;
        if (!document.querySelector("[data-model-canvas]") && typeof window.removeAllLines === "function") {
            window.removeAllLines();
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
        module.exports = { rekeyCanvas, switchToSlot };
    }
})();
