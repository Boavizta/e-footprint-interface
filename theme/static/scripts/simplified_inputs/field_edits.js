"use strict";

// Inline value/provenance saves, accepted snapshots and focused-field exports.
// The workspace coordinator supplies access to the active view; export replay
// stays at the entry point so the editor does not depend on Configure exits.
function createFieldEdits({ activeWorkspace, continueExport }) {
    const savedEdits = new WeakMap();
    const saveStatusTimers = new WeakMap();
    let pendingExport = null;

    function setSaveStatus(form, message, duration = 0) {
        const status = form.querySelector("[data-simplified-save-status]");
        clearTimeout(saveStatusTimers.get(status));
        status.textContent = message;
        if (duration) saveStatusTimers.set(status, setTimeout(() => { status.textContent = ""; }, duration));
    }
    function completeFocusedEditForExport(element) {
        const focused = document.activeElement;
        const form = focused?.closest("[data-simplified-editor]");
        if (!form) return false;
        if (!form.reportValidity()) {
            pendingExport = null;
            setSaveStatus(form, "Not saved");
            return true;
        }
        pendingExport = element;
        // Source controls write their named hidden inputs on completion of the group.
        focused.blur();
        saveEdit(form);
        if (form.dataset.saving === "true") return true;
        pendingExport = null;
        return false;
    }
    function editSnapshot(form) {
        return JSON.stringify([...new FormData(form)].filter(([key]) => key !== "csrfmiddlewaretoken"));
    }
    function saveEdit(form) {
        if (!form || form.dataset.saving === "true" || document.body.dataset.workspaceMutation === "updating") return;
        if (savedEdits.get(form) === editSnapshot(form)) return;
        if (!form.reportValidity()) {
            setSaveStatus(form, "Not saved");
            return;
        }
        form.dataset.saving = "true";
        setSaveStatus(form, "Saving…");
        window.htmx.trigger(form, "simplified-save");
    }
    function initializeEdits() {
        // Replacement controls stay disabled until the shared guard finishes settling.
        // FormData omits disabled inputs, so record their accepted values only after unlock.
        if (document.body.dataset.workspaceMutation === "updating") return;
        document.querySelectorAll("[data-simplified-editor]").forEach(form => {
            if (!savedEdits.has(form)) savedEdits.set(form, editSnapshot(form));
        });
    }

    function registerFieldEdits() {
        document.addEventListener("focusout", event => {
            if (event.target.matches('[data-simplified-editor] input[type="number"]')) {
                saveEdit(event.target.closest("[data-simplified-editor]"));
            }
        });
        document.addEventListener("keydown", event => {
            const form = event.target.closest("[data-simplified-editor]");
            if (form && event.key === "Enter" && event.target.matches('input[type="number"]')) {
                event.preventDefault();
                saveEdit(form);
            }
        });
        document.addEventListener("change", event => {
            if (event.target.matches("[data-simplified-editor] select[name]")) saveEdit(event.target.closest("form"));
        });
        document.addEventListener("optional-quantity:changed", event => {
            if (event.detail.empty) saveEdit(event.target.closest("[data-simplified-editor]"));
        });
        document.addEventListener("simplified-provenance:changed", event => saveEdit(event.target.closest("[data-simplified-editor]")));
        document.addEventListener("submit", event => {
            if (event.target.matches("[data-simplified-editor]")) { event.preventDefault(); saveEdit(event.target); }
        });
        document.body.addEventListener("htmx:configRequest", event => {
            if (event.detail.elt.matches("[data-simplified-timeseries]") && window.recomputationVals?.().recomputation) {
                event.detail.parameters.recomputation = "true";
            }
            if (!event.detail.elt.matches("[data-simplified-editor]")) return;
            const saved = new Map(JSON.parse(savedEdits.get(event.detail.elt) || "[]"));
            const parameters = event.detail.parameters;
            const sourceKeys = Object.keys(parameters).filter(key => /__source_(id|name|link)$/.test(key));
            if (sourceKeys.every(key => parameters[key] === saved.get(key))) {
                sourceKeys.forEach(key => { delete parameters[key]; });
            }
            Object.keys(parameters).filter(key => /__(confidence|comment)$/.test(key)).forEach(key => {
                if (parameters[key] === saved.get(key)) delete parameters[key];
            });
            // HTMX form encoding collapses multiple selects; preserve their reference-ID list.
            event.detail.elt.querySelectorAll("select[multiple][name]").forEach(select => {
                event.detail.parameters[select.name] = [...select.selectedOptions].map(option => option.value).join(";");
            });
            if (window.recomputationVals?.().recomputation) event.detail.parameters.recomputation = "true";
        });
        document.body.addEventListener("workspace-mutation:started", () => {
            document.querySelectorAll("[data-quick-total]").forEach(total => total.setAttribute("aria-busy", "true"));
            document.querySelectorAll("[data-quick-total-status]").forEach(status => { status.textContent = "Updating…"; });
        });
        document.body.addEventListener("workspace-mutation:finished", event => {
            initializeEdits();
            document.querySelectorAll("[data-quick-total]").forEach(total => total.removeAttribute("aria-busy"));
            document.querySelectorAll("[data-quick-total-status]").forEach(status => { status.textContent = ""; });
            const form = event.detail.elt;
            let acceptedForm;
            if (form.matches("[data-simplified-editor]")) {
                delete form.dataset.saving;
                acceptedForm = [...document.querySelectorAll("[data-simplified-editor]")]
                    .find(candidate => candidate.dataset.valuePrefix === form.dataset.valuePrefix);
            } else if (form.matches("[data-simplified-timeseries]")) {
                acceptedForm = activeWorkspace()?.querySelector(
                    `[data-owner-id="${form.dataset.ownerId}"][data-attribute="${form.dataset.attribute}"] [data-simplified-editor]`);
            }
            if (acceptedForm) {
                setSaveStatus(acceptedForm, event.detail.successful ? "Saved" : "Not saved", event.detail.successful ? 3000 : 0);
            }
        });
        document.body.addEventListener("workspace-mutation:finished", event => {
            const form = event.detail.elt;
            if (form.matches("[data-simplified-timeseries]")) {
                window.closeAndEmptySidePanel();
            }
            const element = pendingExport;
            pendingExport = null;
            if (element && event.detail.successful) continueExport(element);
        });
        document.addEventListener("input", event => {
            if (event.target.closest("[data-simplified-timeseries]")) window.tagFormAsModified();
        });
        document.addEventListener("change", event => {
            if (event.target.closest("[data-simplified-timeseries]")) window.tagFormAsModified();
        });
        document.addEventListener("click", event => {
            if (event.target.closest('[data-action="simplified-timeseries-cancel"]')) window.closeAndEmptySidePanel();
        });
        document.body.addEventListener("simplifiedInputSaved", event => {
            const notices = event.detail.notices || [];
            if (notices.length) {
                const notice = document.createElement("p");
                notice.setAttribute("role", "status");
                notice.dataset.simplifiedNotice = "";
                notice.textContent = notices.join(" ");
                activeWorkspace()?.querySelector("[data-simplified-notice]")?.remove();
                activeWorkspace()?.querySelector(".simplified-header")?.after(notice);
            }
        });
        document.body.addEventListener("htmx:afterSettle", initializeEdits);
        document.addEventListener("DOMContentLoaded", initializeEdits);
    }

    return { initializeEdits, completeFocusedEditForExport, registerFieldEdits };
}

module.exports = { createFieldEdits };
