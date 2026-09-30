(function () {
    "use strict";
    const viewBySystemId = new Map();
    let pendingExit = null;
    let savingForm = null;
    let replaying = false;
    let pendingReadCleanup = null;

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
    function loadView(configure, then) {
        const target = targetForActiveModel();
        if (!target) return;
        window.runAfterSidePanelDiscardConfirmation(() => {
            // Keep navigation behind actual settlement, and match the source request's XHR.
            if (pendingReadCleanup) pendingReadCleanup();
            let requestXhr = null;
            const started = event => {
                if (event.detail.elt === target) requestXhr = event.detail.xhr;
            };
            const cleanup = () => {
                target.removeEventListener("htmx:beforeRequest", started);
                target.removeEventListener("htmx:afterSettle", settled);
            };
            const settled = event => {
                if (event.target !== target || !requestXhr || event.detail.xhr !== requestXhr) return;
                cleanup();
                pendingReadCleanup = null;
                if (target !== targetForActiveModel()) return;
                window.closeAndEmptySidePanel();
                setBaseView("simplified");
                if (then) then();
            };
            target.addEventListener("htmx:beforeRequest", started);
            target.addEventListener("htmx:afterSettle", settled);
            pendingReadCleanup = cleanup;
            window.htmx.ajax("GET", `/model_builder/simplified-inputs/${configure ? "?configure=1" : ""}`, {
                source: target, target, swap: "innerHTML"
            });
        });
    }

    function navigate(workspace, objectId) {
        const object = document.getElementById(objectId);
        if (!object || object.hidden) return;
        object.closest("[data-simplified-group]").open = true;
        object.open = true;
        object.scrollIntoView({ block: "nearest" });
        object.querySelector("summary").focus({ preventScroll: true });
        workspace.querySelector("[data-object-selector]").value = objectId;
    }
    function refreshSelection(workspace) {
        const controls = [...workspace.querySelectorAll("[data-selection-controls]")];
        const byId = new Map(controls.map(control => [control.dataset.fieldId, control]));
        const required = new Set();
        const pending = controls.filter(control => control.querySelector("[data-include-input]").checked);
        for (let index = 0; index < pending.length; index++) {
            for (const id of pending[index].dataset.requiredInputs.split(" ").filter(Boolean)) {
                if (required.has(id)) continue;
                required.add(id);
                const dependent = byId.get(id);
                dependent.querySelector("[data-include-input]").checked = true;
                pending.push(dependent);
            }
        }
        controls.forEach(control => {
            const locked = required.has(control.dataset.fieldId);
            control.querySelector("[data-include-input]").disabled = locked;
            control.querySelector("[data-locked-include]").disabled = !locked;
            control.querySelector("[data-required-explanation]").hidden = !locked;
        });
        refreshFilter(workspace);
    }
    function refreshFilter(workspace) {
        const filtered = !!workspace.querySelector("[data-selected-object-filter]")?.checked;
        const focusedObject = document.activeElement.closest("[data-simplified-object]");
        let visibleCount = 0;
        workspace.querySelectorAll("[data-simplified-object]").forEach(object => {
            const count = workspace.dataset.mode === "configure"
                ? [...object.querySelectorAll("[data-include-input]")].filter(input => input.checked).length
                : object.querySelectorAll("[data-field-address]").length;
            object.querySelector("[data-object-count]").textContent = `(${count} selected)`;
            object.hidden = filtered && count === 0;
            if (!object.hidden) visibleCount++;
            const navigation = workspace.querySelector(`[data-navigation-object="${object.id}"]`);
            navigation.hidden = object.hidden;
            navigation.querySelector("[data-navigation-count]").textContent = `(${count})`;
            const option = workspace.querySelector(`option[value="${object.id}"]`);
            option.hidden = object.hidden;
            option.disabled = object.hidden;
        });
        workspace.querySelectorAll("[data-simplified-group]").forEach(group => {
            group.hidden = ![...group.querySelectorAll("[data-simplified-object]")].some(object => !object.hidden);
            workspace.querySelector(`[data-navigation-group="${group.id}"]`).hidden = group.hidden;
            workspace.querySelector(`[data-selector-group="${group.id}"]`).hidden = group.hidden;
        });
        workspace.querySelector("[data-filter-empty]").hidden = !filtered || visibleCount > 0;
        if (focusedObject?.hidden) {
            const next = [...workspace.querySelectorAll("[data-simplified-object]")].find(object => !object.hidden);
            if (next) navigate(workspace, next.id);
            else workspace.querySelector("[data-selected-object-filter]").focus();
        }
    }
    function initialize() {
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
    // Capture before HTMX or other delegated navigation can alter the visible workspace.
    document.addEventListener("click", event => {
        if (replaying || !configureForm() || document.body.dataset.workspaceMutation === "updating") return;
        const element = event.target.closest("a, button, [hx-get], [hx-post], [data-action]");
        if (!element || element.closest("[data-simplified-workspace], #simplified-exit-dialog, #modal-container")) return;
        if (!element.matches("a[href], [hx-get], [hx-post], [data-workspace-control], [data-action]")) return;
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
    document.addEventListener("input", event => {
        const form = event.target.closest("[data-configure-form]");
        if (form && !event.target.matches("[data-selected-object-filter]")) form.dataset.dirty = "true";
    });
    document.addEventListener("change", event => {
        const workspace = event.target.closest("[data-simplified-workspace]");
        if (!workspace) return;
        if (event.target.matches("[data-include-input]")) {
            configureForm().dataset.dirty = "true";
            refreshSelection(workspace);
        }
        if (event.target.matches("[data-selected-object-filter]")) refreshFilter(workspace);
        if (event.target.matches("[data-object-selector]")) navigate(workspace, event.target.value);
    });
    document.addEventListener("click", event => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const workspace = activeWorkspace();
        switch (button.dataset.action) {
        case "simplified-mode":
            if (typeof window.collapseNavbarIfShown === "function") window.collapseNavbarIfShown();
            deferExit(() => document.body.dataset.baseView === "simplified" ? setBaseView("modeling") : loadView(false));
            break;
        case "simplified-configure": loadView(true); break;
        case "simplified-cancel": deferExit(() => {}); break;
        case "simplified-clear":
            if (window.confirm("Remove all selected inputs and all per-field help, including help retained on deselected inputs? Modeling values and sources stay unchanged.")) {
                workspace.querySelectorAll("[data-include-input]").forEach(input => { input.checked = false; });
                workspace.querySelectorAll("[data-field-help]").forEach(input => { input.value = ""; });
                configureForm().dataset.dirty = "true";
                refreshSelection(workspace);
            }
            break;
        case "simplified-navigate": navigate(workspace, button.dataset.navigationObject); break;
        case "simplified-expand":
        case "simplified-collapse":
            workspace.querySelectorAll("details").forEach(item => { item.open = button.dataset.action === "simplified-expand"; });
            break;
        case "simplified-show-all":
            workspace.querySelector("[data-selected-object-filter]").checked = false;
            refreshFilter(workspace);
            break;
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
    if (typeof module !== "undefined" && module.exports) {
        module.exports = { refreshSelection, refreshFilter, initialize, setBaseView, deferExit };
    }
})();
