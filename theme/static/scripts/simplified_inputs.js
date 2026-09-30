(function () {
    "use strict";
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

    function definitionFromForm(form) {
        const fields = {};
        form.querySelectorAll("[data-field-address]").forEach(field => {
            const included = field.querySelector("[data-include-input]").checked;
            const help = field.querySelector("[data-field-help]").value;
            if (included || help) {
                fields[field.dataset.ownerId] ??= {};
                fields[field.dataset.ownerId][field.dataset.attribute] = { included, help };
            }
        });
        return { title: form.elements.title.value, guidance: form.elements.guidance.value, fields };
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
    function updateBookmark(bookmark, setting, requiredBy) {
        const checkbox = bookmark.querySelector("[data-include-input]");
        const help = bookmark.querySelector("[data-field-help]");
        const explanation = bookmark.querySelector("[data-required-explanation]");
        bookmark.dataset.savedIncluded = String(setting.included);
        bookmark.dataset.requiredLabel = requiredBy?.label || "";
        bookmark.querySelector("[data-bookmark-icon]").className = `bi bi-bookmark${setting.included ? "-fill" : ""}`;
        if (checkbox) { checkbox.checked = setting.included; checkbox.disabled = !!requiredBy; }
        if (help) { help.value = setting.help; help.defaultValue = setting.help; }
        if (explanation) {
            explanation.hidden = !requiredBy;
            explanation.textContent = requiredBy ? `Required by ${requiredBy.label}.` : "";
        }
    }
    function refreshCreationBookmarks() {
        const script = document.getElementById("dynamic-form-data");
        if (!script) return;
        const data = JSON.parse(script.textContent);
        const bookmarks = [...document.querySelectorAll("[data-bookmark][data-provisional-owner]")];
        const active = bookmark => !bookmark.closest('[id^="item-"]')?.classList.contains("d-none");
        bookmarks.forEach(bookmark => {
            const checkbox = bookmark.querySelector("[data-include-input]");
            if (bookmark.dataset.authoredIncluded === undefined) bookmark.dataset.authoredIncluded = String(checkbox.checked);
            checkbox.checked = bookmark.dataset.authoredIncluded === "true";
            checkbox.disabled = false;
            bookmark.dataset.requiredLabel = "";
        });
        // Same-owner chains use the same dynamic-list edges as the value selectors.
        for (let pass = 0; pass <= bookmarks.length; pass++) {
            let changed = false;
            (data.dynamic_lists || []).forEach(list => {
                const bookmark = bookmarks.find(item => item.dataset.inputId === list.input_id && active(item));
                if (!bookmark) return;
                const filter = document.getElementById(list.filter_by);
                const controller = bookmarks.find(item => item.dataset.inputId === list.filter_by && active(item));
                const requirement = list.simplified_required_by?.[filter?.value]
                    || (controller?.querySelector("[data-include-input]").checked
                        ? {label: document.querySelector(`label[for="${list.filter_by}"]`)?.textContent.trim()} : null);
                if (!requirement) return;
                const checkbox = bookmark.querySelector("[data-include-input]");
                if (!checkbox.checked) changed = true;
                checkbox.checked = true;
                checkbox.disabled = true;
                bookmark.dataset.requiredLabel = requirement.label;
            });
            if (!changed) break;
        }
        bookmarks.forEach(bookmark => {
            const checkbox = bookmark.querySelector("[data-include-input]");
            updateBookmark(bookmark, {included: checkbox.checked, help: bookmark.querySelector("[data-field-help]").value},
                bookmark.dataset.requiredLabel ? {label: bookmark.dataset.requiredLabel} : null);
        });
    }
    function pendingCreationSettings(form) {
        return [...form.querySelectorAll("[data-provisional-owner]")]
            .filter(bookmark => !bookmark.closest('[id^="item-"]')?.classList.contains("d-none"))
            .map(bookmark => ({owner: bookmark.dataset.provisionalOwner, attribute: bookmark.dataset.attribute,
                included: bookmark.querySelector("[data-include-input]").checked,
                help: bookmark.querySelector("[data-field-help]").value}))
            .filter(setting => setting.included || setting.help);
    }
    function saveBookmark(bookmark, patch, undo = false) {
        bookmark.dataset.pendingPatch = JSON.stringify(patch);
        bookmark.dataset.pendingUndo = String(undo);
        window.htmx.trigger(bookmark, "bookmark-save");
    }
    document.addEventListener("toggle", event => {
        const bookmark = event.target.closest("[data-bookmark]");
        if (bookmark?.open) {
            const lazy = bookmark.querySelector('[hx-trigger="bookmark-open once"]');
            if (lazy) window.htmx.trigger(lazy, "bookmark-open");
            else bookmark.querySelector("[data-bookmark-content]").scrollIntoView({block: "nearest"});
        }
    }, true);
    document.addEventListener("change", event => {
        const bookmark = event.target.closest("[data-bookmark]");
        if (bookmark && event.target.matches("[data-include-input], [data-field-help]")) {
            if (bookmark.hasAttribute("data-provisional-owner")) {
                if (event.target.matches("[data-include-input]")) bookmark.dataset.authoredIncluded = String(event.target.checked);
            } else {
                const property = event.target.matches("[data-include-input]") ? "included" : "help";
                const value = property === "included" ? event.target.checked : event.target.value;
                saveBookmark(bookmark, {fields: {[bookmark.dataset.ownerId]: {[bookmark.dataset.attribute]: {[property]: value}}}});
            }
        }
        if (document.querySelector("[data-provisional-owner]")) refreshCreationBookmarks();
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Enter" && event.target.closest("[data-bookmark]") && event.target.matches("[data-field-help]")) {
            event.preventDefault();
            event.target.blur();
        }
    });
    document.addEventListener("click", event => {
        const button = event.target.closest('[data-action="bookmark-undo"]');
        if (button) {
            const bookmark = button.closest("[data-bookmark]");
            saveBookmark(bookmark, JSON.parse(bookmark.dataset.inversePatch), true);
        }
    });
    document.body.addEventListener("htmx:configRequest", event => {
        const element = event.detail.elt;
        if (element.matches("[data-bookmark]")) event.detail.parameters.patch = element.dataset.pendingPatch;
        if (element.querySelector("[data-provisional-owner]")) {
            event.detail.parameters.simplified_settings = JSON.stringify(pendingCreationSettings(element));
        }
    });
    document.body.addEventListener("htmx:afterRequest", event => {
        const bookmark = event.detail.elt;
        if (!bookmark?.matches("[data-bookmark]")) return;
        const failed = event.detail.successful !== true
            || (event.detail.xhr.getResponseHeader("HX-Trigger-After-Settle") || "").includes("openModalDialog");
        bookmark.querySelector("[data-bookmark-status]").textContent = failed ? "Not saved" : "Saved";
        if (failed) return;
        const result = JSON.parse(event.detail.xhr.responseText);
        result.fields.forEach(field => {
            document.querySelectorAll("[data-bookmark]").forEach(visible => {
                if (visible.dataset.ownerId !== field.object_id || visible.dataset.attribute !== field.attribute) return;
                // Help belongs to its own draft until its own request completes.
                const help = visible.querySelector("[data-field-help]");
                const draft = help?.value;
                const dirtyHelp = help && draft !== help.defaultValue;
                updateBookmark(visible, field.setting, field.required_by);
                if (dirtyHelp && visible !== bookmark) help.value = draft;
            });
        });
        if (Object.keys(result.inverse.fields).length && bookmark.dataset.pendingUndo !== "true") {
            bookmark.dataset.inversePatch = JSON.stringify(result.inverse);
            bookmark.querySelector('[data-action="bookmark-undo"]').hidden = false;
        } else if (bookmark.dataset.pendingUndo === "true") {
            bookmark.querySelector('[data-action="bookmark-undo"]').hidden = true;
        }
    });
    document.body.addEventListener("htmx:afterSettle", event => {
        const bookmark = event.target.closest("[data-bookmark]");
        if (bookmark?.open) bookmark.querySelector("[data-bookmark-content]").scrollIntoView({block: "nearest"});
    });
    document.addEventListener("initDynamicForm", refreshCreationBookmarks);

    function initialize() {
        document.querySelectorAll("[data-bookmark]:not([data-provisional-owner])").forEach(bookmark => {
            const checkbox = bookmark.querySelector("[data-include-input]");
            if (checkbox) checkbox.disabled = !!bookmark.dataset.requiredLabel;
        });
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
    // Capture before HTMX or other delegated navigation can alter the visible workspace.
    document.addEventListener("click", event => {
        if (replaying || document.body.dataset.workspaceMutation === "updating") return;
        const element = event.target.closest("a, button, [hx-get], [hx-post], [data-action]");
        if (!element || element.closest("[data-simplified-workspace], #simplified-exit-dialog, #modal-container")) return;
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
    document.addEventListener("input", event => {
        if (event.target.closest("[data-provisional-owner]")) window.tagFormAsModified();
        const form = event.target.closest("[data-configure-form]");
        if (form && event.target.matches('[name="title"], [name="guidance"], [data-field-help], [data-include-input]')) {
            form.dataset.dirty = "true";
        }
    });
    document.body.addEventListener("htmx:configRequest", event => {
        if (event.detail.elt.matches("[data-configure-form]")) {
            event.detail.parameters.definition = JSON.stringify(definitionFromForm(event.detail.elt));
        }
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
    if (typeof module !== "undefined" && module.exports) {
        module.exports = { refreshSelection, refreshFilter, initialize, setBaseView, deferExit, definitionFromForm, refreshCreationBookmarks, pendingCreationSettings, updateBookmark };
    }
})();
