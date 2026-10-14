"use strict";

// Inline value/provenance saves and accepted snapshots.
function createFieldEdits({ activeWorkspace }) {
    const savedEdits = new WeakMap();
    const saveStatusTimers = new WeakMap();
    const saves = new WeakMap();

    function setSaveStatus(form, message, duration = 0) {
        const status = form.querySelector("[data-simplified-save-status]");
        clearTimeout(saveStatusTimers.get(status));
        status.textContent = message;
        if (duration) saveStatusTimers.set(status, setTimeout(() => { status.textContent = ""; }, duration));
    }
    function editSnapshot(form) {
        return JSON.stringify([...new FormData(form)].filter(([key]) => key !== "csrfmiddlewaretoken"));
    }
    function saveEdit(form) {
        if (!form || form.dataset.saving === "true" || form.querySelector("[data-disabled-by-htmx]")) return;
        if (savedEdits.get(form) === editSnapshot(form)) return;
        if (!form.reportValidity()) {
            setSaveStatus(form, "Not saved");
            return;
        }
        const valueKey = form.dataset.valuePrefix;
        const savedValues = JSON.parse(savedEdits.get(form) || "[]").filter(([key]) => key === valueKey);
        const currentValues = [...new FormData(form)].filter(([key]) => key === valueKey);
        if (JSON.stringify(currentValues) !== JSON.stringify(savedValues)) {
            [...form.elements].find(element => element.name === valueKey)?.dispatchEvent(
                new CustomEvent("source-metadata:value-changed", {bubbles: true}));
        }
        form.dataset.saving = "true";
        setSaveStatus(form, "Saving…");
        window.htmx.trigger(form, "simplified-save");
    }
    function initializeEdits() {
        document.querySelectorAll("[data-simplified-editor]").forEach(form => {
            // FormData omits temporarily disabled controls during an active request.
            if (!savedEdits.has(form) && !form.querySelector("[data-disabled-by-htmx]")) {
                savedEdits.set(form, editSnapshot(form));
            }
        });
    }
    function setTotalsBusy(busy) {
        document.querySelectorAll("[data-quick-total]").forEach(total => {
            if (busy) total.setAttribute("aria-busy", "true");
            else total.removeAttribute("aria-busy");
        });
        document.querySelectorAll("[data-quick-total-status]").forEach(status => {
            status.textContent = busy ? "Updating…" : "";
        });
    }
    function finishSave(xhr) {
        const save = saves.get(xhr);
        if (!save || !save.complete || (save.waitingForSettle && !save.settled)) return;
        saves.delete(xhr);
        const form = save.form;
        delete form.dataset.saving;
        initializeEdits();
        setTotalsBusy(false);
        const acceptedForm = form.matches("[data-simplified-editor]")
            ? [...document.querySelectorAll("[data-simplified-editor]")]
                .find(candidate => candidate.dataset.valuePrefix === form.dataset.valuePrefix)
            : activeWorkspace()?.querySelector(
                `[data-owner-id="${form.dataset.ownerId}"][data-attribute="${form.dataset.attribute}"] [data-simplified-editor]`);
        if (acceptedForm) {
            if (save.successful) savedEdits.set(acceptedForm, editSnapshot(acceptedForm));
            setSaveStatus(acceptedForm, save.successful ? "Saved" : "Not saved", save.successful ? 3000 : 0);
        }
        if (form.matches("[data-simplified-timeseries]")) window.closeAndEmptySidePanel();
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
        document.addEventListener("htmx:beforeRequest", event => {
            const form = event.detail.elt;
            if (!form.matches("[data-simplified-editor], [data-simplified-timeseries]")) return;
            saves.set(event.detail.xhr, {form});
            setTotalsBusy(true);
        });
        document.addEventListener("htmx:beforeSwap", event => {
            const save = saves.get(event.detail.xhr);
            if (save) save.waitingForSettle = event.detail.shouldSwap;
        });
        document.addEventListener("htmx:afterRequest", event => {
            const save = saves.get(event.detail.xhr);
            if (!save) return;
            save.complete = true;
            save.successful = event.detail.successful === true;
            finishSave(event.detail.xhr);
        });
        document.addEventListener("htmx:afterSettle", event => {
            const save = saves.get(event.detail.xhr);
            if (save) save.settled = true;
            finishSave(event.detail.xhr);
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
            const noticeText = document.getElementById(event.detail.notice_target).textContent;
            if (noticeText) {
                const notice = document.createElement("p");
                notice.setAttribute("role", "status");
                notice.dataset.simplifiedNotice = "";
                notice.textContent = noticeText;
                activeWorkspace()?.querySelector("[data-simplified-notice]")?.remove();
                activeWorkspace()?.querySelector(".simplified-header")?.after(notice);
            }
        });
        document.body.addEventListener("htmx:afterSettle", initializeEdits);
        document.addEventListener("DOMContentLoaded", initializeEdits);
    }

    return { initializeEdits, registerFieldEdits };
}

module.exports = { createFieldEdits };
