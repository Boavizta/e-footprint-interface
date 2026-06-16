// Model-comparison workspace UI (Task 3): client-side model switching across two resident canvases.
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
        // shared tab strip stays unchanged.
        if (!document.querySelector("[data-model-canvas]")) {
            if (window.htmx) {
                window.htmx.ajax("GET", "/model_builder/", { target: "#main-content-block", swap: "innerHTML" });
                window.history.pushState({}, "", "/model_builder/");
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
        document.querySelectorAll("[data-model-tab]").forEach(tab => {
            const isTarget = String(tab.dataset.modelTab) === String(slot);
            tab.classList.toggle("fw-bold", isTarget);
            tab.classList.toggle("bg-white", isTarget);
            tab.classList.toggle("border", isTarget);
            tab.classList.toggle("border-bottom-0", isTarget);
            tab.classList.toggle("text-muted", !isTarget);
        });
        strip.dataset.activeSlot = slot;

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

    // Confirm before removing the second model (live-state confirm, body-delegated so it survives swaps).
    document.body.addEventListener("htmx:confirm", function (evt) {
        const elt = evt.target.closest("[data-confirm-remove-model]");
        if (!elt) return;
        evt.preventDefault();
        if (window.confirm(elt.getAttribute("data-confirm-remove-model"))) {
            evt.detail.issueRequest(true);
        }
    });

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
