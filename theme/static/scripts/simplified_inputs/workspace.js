"use strict";

const { refreshSelection } = require("./configuration.js");

// Each Simplified-input slot carries its model's last base view as data-view, so switching
// models restores each view and a builder re-render brings the server's defaults. Reads switch
// the view on click and let HTMX replace them (hx-sync on the slot). A dirty Configure draft
// blocks every shared exit behind Save/Discard/Stay; the user then repeats the navigation.
function createWorkspace() {
    function targetForActiveModel() {
        const slot = document.getElementById("model-tab-strip")?.dataset.activeSlot || "0";
        return document.querySelector(`[data-simplified-target="${slot}"]`);
    }
    function activeWorkspace() {
        return targetForActiveModel()?.querySelector("[data-simplified-workspace]");
    }
    function configureForm() {
        return activeWorkspace()?.querySelector("[data-configure-form]");
    }
    function dialog() { return document.getElementById("simplified-exit-dialog"); }
    function setBaseView(mode) {
        const target = targetForActiveModel();
        if (!target) return;
        const previousMode = document.body.dataset.baseView;
        target.dataset.view = mode;
        document.body.dataset.baseView = mode;
        document.getElementById("model-canva-scrollable-area")?.classList.toggle("d-none", mode === "simplified");
        document.querySelectorAll("[data-simplified-target]").forEach(item => {
            item.classList.toggle("d-none", item !== target || mode !== "simplified");
        });
        const button = document.querySelector('[data-action="simplified-mode"]');
        if (button) button.textContent = mode === "simplified" ? "Modeling" : "Simplified inputs";
        if (mode === "simplified" && typeof window.removeAllLines === "function") window.removeAllLines();
        if (mode === "modeling" && previousMode === "simplified" && typeof window.initModelBuilderMain === "function") window.initModelBuilderMain();
    }
    function loadView(configure) {
        const target = targetForActiveModel();
        if (!target) return;
        window.runAfterSidePanelDiscardConfirmation(() => {
            window.closeAndEmptySidePanel();
            setBaseView("simplified");
            window.htmx.ajax("GET", `/model_builder/simplified-inputs/${configure ? "?configure=1" : ""}`,
                { source: target, target, swap: "innerHTML" });
        });
    }
    function initialize() {
        document.querySelectorAll("[data-simplified-target]").forEach(target => {
            const workspace = target.querySelector("[data-simplified-workspace]");
            if (workspace && !workspace.dataset.initialized) {
                workspace.dataset.initialized = "true";
                refreshSelection(workspace);
            }
        });
        const target = targetForActiveModel();
        if (target) setBaseView(target.dataset.view || "modeling");
    }
    function blockWhileDirty(event) {
        if (configureForm()?.dataset.dirty !== "true") return;
        event.preventDefault();
        event.stopImmediatePropagation();
        dialog().showModal();
    }

    function registerWorkspace() {
        // Capture before HTMX or other delegated navigation can alter the visible workspace.
        document.addEventListener("click", event => {
            const element = event.target.closest("a, button, [hx-get], [hx-post], [data-action]");
            if (!element || element.closest("[data-workspace-export], [data-simplified-workspace], "
                + "#simplified-exit-dialog, #modal-container")) return;
            if (!element.matches("a[href], [hx-get], [hx-post], [data-workspace-control], [data-action]")) return;
            blockWhileDirty(event);
        }, true);
        // Covers programmatic HTMX entry points as well as ordinary clicks.
        document.body.addEventListener("htmx:confirm", event => {
            if (event.target.closest("[data-configure-form]") || event.detail.elt?.matches("[data-simplified-target]")) return;
            blockWhileDirty(event);
        });
        document.addEventListener("click", event => {
            const button = event.target.closest("[data-action]");
            if (!button) return;
            switch (button.dataset.action) {
            case "simplified-mode":
                if (typeof window.collapseNavbarIfShown === "function") window.collapseNavbarIfShown();
                if (document.body.dataset.baseView === "simplified") setBaseView("modeling");
                else loadView(false);
                break;
            case "simplified-configure": loadView(true); break;
            case "simplified-cancel":
                if (configureForm()?.dataset.dirty === "true") dialog().showModal();
                else loadView(false);
                break;
            case "simplified-exit-save": dialog().close(); configureForm().requestSubmit(); break;
            case "simplified-exit-discard": dialog().close(); loadView(false); break;
            case "simplified-exit-stay": dialog().close(); break;
            }
        });
        window.addEventListener("beforeunload", event => {
            if (configureForm()?.dataset.dirty === "true") { event.preventDefault(); event.returnValue = ""; }
        });
        document.body.addEventListener("switchModelCanvas", initialize);
        document.body.addEventListener("htmx:afterSettle", initialize);
        document.addEventListener("DOMContentLoaded", initialize);
    }

    return { activeWorkspace, configureForm, initialize, registerWorkspace };
}

module.exports = { createWorkspace };
