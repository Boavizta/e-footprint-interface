"use strict";

// Membership/help patches and provisional selection during object creation.
// Bookmark saves send only their patch and the mounted bookmark ids; the server answers with fragments.
function updateProvisionalBookmark(bookmark, setting, requiredBy) {
    const checkbox = bookmark.querySelector("[data-include-input]");
    const help = bookmark.querySelector("[data-field-help]");
    const explanation = bookmark.querySelector("[data-required-explanation]");
    bookmark.querySelector("[data-bookmark-icon]").className = `bi bi-bookmark${setting.included ? "-fill" : ""}`;
    const summary = bookmark.querySelector("summary");
    const state = `${setting.included ? "Included" : "Not included"} in Simplified inputs.`;
    summary.setAttribute("aria-label", `${state} Open settings.`);
    summary.title = `${state}${requiredBy ? ` Required by ${requiredBy.label}.` : ""} Open settings.`;
    if (checkbox) { checkbox.checked = setting.included; checkbox.disabled = !!requiredBy; }
    if (help) { help.value = setting.help; help.defaultValue = setting.help; }
    if (explanation) {
        explanation.hidden = !requiredBy;
        explanation.textContent = requiredBy ? `Required by ${requiredBy.label}.` : "";
    }
}
function isActiveCreationBookmark(bookmark) {
    // EdgeComputer's Storage is a sibling form hidden independently of the class sections.
    return !bookmark.closest('[id^="item-"]')?.classList.contains("d-none")
        && bookmark.closest("form")?.style.display !== "none";
}
function refreshCreationBookmarks() {
    const script = document.getElementById("dynamic-form-data");
    if (!script) return;
    const data = JSON.parse(script.textContent);
    const bookmarks = [...document.querySelectorAll("[data-bookmark][data-provisional-owner]")];
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
            const bookmark = bookmarks.find(item => item.dataset.inputId === list.input_id && isActiveCreationBookmark(item));
            if (!bookmark) return;
            const filter = document.getElementById(list.filter_by);
            const controller = bookmarks.find(item => item.dataset.inputId === list.filter_by && isActiveCreationBookmark(item));
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
        updateProvisionalBookmark(bookmark, {included: checkbox.checked, help: bookmark.querySelector("[data-field-help]").value},
            bookmark.dataset.requiredLabel ? {label: bookmark.dataset.requiredLabel} : null);
    });
}
function pendingCreationSettings(panel) {
    return [...panel.querySelectorAll("[data-provisional-owner]")]
        .filter(isActiveCreationBookmark)
        .map(bookmark => ({owner: bookmark.dataset.provisionalOwner, attribute: bookmark.dataset.attribute,
            included: bookmark.querySelector("[data-include-input]").checked,
            help: bookmark.querySelector("[data-field-help]").value}))
        .filter(setting => setting.included || setting.help);
}
function saveBookmark(bookmark, patch) {
    bookmark.dataset.pendingPatch = JSON.stringify(patch);
    window.htmx.trigger(bookmark, "bookmark-save");
}

function registerBookmarks() {
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
    document.body.addEventListener("htmx:configRequest", event => {
        const element = event.detail.elt;
        // Controls are nameless so the surrounding form never submits them; the payload is built here.
        if (element.matches("[data-bookmark]")) {
            event.detail.parameters.patch = element.dataset.pendingPatch;
            event.detail.parameters.mounted = JSON.stringify([...document.querySelectorAll(
                "[data-bookmark]:not([data-provisional-owner])")].map(bookmark => bookmark.id));
        }
        const panel = element.matches("#sidePanelForm") ? element.closest("#sidePanelContent") : null;
        if (panel?.querySelector("[data-provisional-owner]")) {
            event.detail.parameters.simplified_settings = JSON.stringify(pendingCreationSettings(panel));
        }
    });
    document.body.addEventListener("htmx:afterSettle", event => {
        // Only a request's own target scrolls: out-of-band summaries of other open bookmarks settle too.
        if (event.target !== event.detail.target) return;
        const bookmark = event.target.closest("[data-bookmark]");
        if (bookmark?.open) bookmark.querySelector("[data-bookmark-content]").scrollIntoView({block: "nearest"});
    });
    document.addEventListener("initDynamicForm", refreshCreationBookmarks);
    document.addEventListener("input", event => {
        if (event.target.closest("[data-provisional-owner]")) window.tagFormAsModified();
    });
}

module.exports = { refreshCreationBookmarks, pendingCreationSettings, registerBookmarks };
