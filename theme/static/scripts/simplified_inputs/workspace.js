"use strict";

const { refreshSelection } = require("./configuration.js");

// Own view memory, pending reads and Configure exit continuations together so a
// late response cannot replace a draft or resume navigation in another model.
function createWorkspace() {
    const viewBySystemId = new Map();
    let pendingExit = null;
    let savingForm = null;
    let replaying = false;
    let pendingRead = null;
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
        viewBySystemId.set(target.dataset.systemId, mode);
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
    function cancelPendingRead() {
        if (!pendingRead) return;
        const read = pendingRead;
        read.cleanup();
        read.xhr?.abort();
    }
    function loadView(configure, then) {
        const target = targetForActiveModel();
        if (!target || pendingRead) return;
        window.runAfterSidePanelDiscardConfirmation(() => {
            const read = { target, xhr: null, cleanup };
            pendingRead = read;
            const started = event => {
                if (event.detail.elt === target) read.xhr = event.detail.xhr;
            };
            function cleanup() {
                target.removeEventListener("htmx:beforeRequest", started);
                target.removeEventListener("htmx:beforeSwap", beforeSwap);
                target.removeEventListener("htmx:afterRequest", completed);
                target.removeEventListener("htmx:onLoadError", cleanup);
                target.removeEventListener("htmx:afterSettle", settled);
                if (pendingRead === read) pendingRead = null;
            }
            const beforeSwap = event => {
                if (event.detail.xhr !== read.xhr) return;
                if (target !== targetForActiveModel()) {
                    event.preventDefault();
                    cleanup();
                }
            };
            const completed = event => {
                if (event.detail.xhr === read.xhr && event.detail.successful !== true) cleanup();
            };
            const settled = event => {
                if (event.target !== target || event.detail.xhr !== read.xhr) return;
                cleanup();
                if (target !== targetForActiveModel()) return;
                window.closeAndEmptySidePanel();
                setBaseView("simplified");
                if (then) then();
            };
            target.addEventListener("htmx:beforeRequest", started);
            target.addEventListener("htmx:beforeSwap", beforeSwap);
            target.addEventListener("htmx:afterRequest", completed);
            target.addEventListener("htmx:onLoadError", cleanup);
            target.addEventListener("htmx:afterSettle", settled);
            window.htmx.ajax("GET", `/model_builder/simplified-inputs/${configure ? "?configure=1" : ""}`, {
                source: target, target, swap: "innerHTML"
            });
        });
    }

    function initialize() {
        if (pendingRead && pendingRead.target !== targetForActiveModel()) cancelPendingRead();
        document.querySelectorAll("[data-simplified-target]").forEach(target => {
            if (target.dataset.openingDefault) {
                viewBySystemId.set(target.dataset.systemId, target.dataset.openingDefault);
                delete target.dataset.openingDefault;
            }
            const workspace = target.querySelector("[data-simplified-workspace]");
            if (workspace && !workspace.dataset.initialized) {
                workspace.dataset.initialized = "true";
                refreshSelection(workspace);
            }
        });
        const target = targetForActiveModel();
        if (!target) return;
        const mode = viewBySystemId.get(target.dataset.systemId) || "modeling";
        if (mode === "simplified" && !target.querySelector("[data-simplified-workspace]")) loadView(false);
        else setBaseView(mode);
    }
    function deferExit(action) {
        const form = configureForm();
        if (form?.dataset.dirty === "true") {
            pendingExit = action;
            dialog().showModal();
        } else if (form) loadView(false, action);
        else action();
    }
    function replayClick(element) {
        replaying = true;
        try { element.click(); } finally { replaying = false; }
    }

    function registerWorkspace() {
        // Capture before HTMX or other delegated navigation can alter the visible workspace.
        document.addEventListener("click", event => {
            if (replaying || document.body.dataset.workspaceMutation === "updating") return;
            const element = event.target.closest("a, button, [hx-get], [hx-post], [data-action]");
            if (!element || element.closest("[data-workspace-export], [data-simplified-workspace], "
                + "#simplified-exit-dialog, #modal-container")) return;
            if (!element.matches("a[href], [hx-get], [hx-post], [data-workspace-control], [data-action]")) return;
            // A pending entry must not land after the user has chosen another destination.
            // Repeated Modeling → Simplified clicks instead share the first pending read.
            if (element.dataset.action !== "simplified-mode" || document.body.dataset.baseView === "simplified") {
                cancelPendingRead();
            }
            if (!configureForm()) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            deferExit(() => replayClick(element));
        }, true);
        // Covers programmatic HTMX entry points as well as ordinary clicks.
        document.body.addEventListener("htmx:confirm", event => {
            const form = configureForm();
            if (replaying || !form || event.target.closest("[data-configure-form]")
                || event.detail.elt?.matches("[data-simplified-target]")) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            deferExit(() => event.detail.issueRequest(true));
        });
        document.addEventListener("click", event => {
            const button = event.target.closest("[data-action]");
            if (!button) return;
            switch (button.dataset.action) {
            case "simplified-mode":
                if (typeof window.collapseNavbarIfShown === "function") window.collapseNavbarIfShown();
                deferExit(() => document.body.dataset.baseView === "simplified" ? setBaseView("modeling") : loadView(false));
                break;
            case "simplified-configure": loadView(true); break;
            case "simplified-cancel": deferExit(() => {}); break;
            case "simplified-exit-stay": dialog().close(); pendingExit = null; break;
            case "simplified-exit-discard": {
                dialog().close();
                const action = pendingExit;
                pendingExit = null;
                loadView(false, action);
                break;
            }
            case "simplified-exit-save": dialog().close(); configureForm().requestSubmit(); break;
            }
        });
        document.body.addEventListener("workspace-mutation:started", event => {
            cancelPendingRead();
            if (event.detail.elt.matches("[data-configure-form]")) savingForm = event.detail.elt;
        });
        document.body.addEventListener("workspace-mutation:finished", event => {
            if (!savingForm || event.detail.elt !== savingForm) return;
            savingForm = null;
            const action = pendingExit;
            pendingExit = null;
            if (event.detail.successful && action) action();
        });
        document.addEventListener("cancel", event => {
            if (event.target.id === "simplified-exit-dialog") pendingExit = null;
        }, true);
        window.addEventListener("beforeunload", event => {
            if (configureForm()?.dataset.dirty === "true") { event.preventDefault(); event.returnValue = ""; }
        });
        document.body.addEventListener("switchModelCanvas", initialize);
        document.body.addEventListener("htmx:afterSettle", initialize);
        document.addEventListener("DOMContentLoaded", initialize);
    }

    return { activeWorkspace, configureForm, initialize, setBaseView, loadView, deferExit, registerWorkspace };
}

module.exports = { createWorkspace };
