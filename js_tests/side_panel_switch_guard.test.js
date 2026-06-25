// Pre-navigation unsaved-changes guard: leaving the active model with a modified side-panel form
// (switch-model, +Add) must be deferred behind the shared unsaved modal, not fired immediately. These
// requests do NOT target #sidePanel, so the older #sidePanel-targeted beforeRequest guard misses them;
// this one hooks htmx:confirm (fires before the request) and only lets it through on "Continue".
// Opening Compare is NOT guarded (the side panel survives hidden behind the resident comparison view);
// remove-model is handled separately (model_comparison.js).

function modalDom() {
    document.body.innerHTML = `
        <div id="unsavedModal"></div>
        <button id="continue-unsaved-modal"></button>
    `;
}

let shownTimes;
beforeEach(() => {
    jest.resetModules();
    // Each require re-attaches the guard's htmx:confirm listener to document.body. Swap in a fresh body
    // so a prior test's listener (with its own stale formModified) can't fire on this test's event.
    document.body.replaceWith(document.createElement("body"));
    modalDom();
    shownTimes = 0;
    // Minimal Bootstrap modal stub — the guard only constructs/shows/hides it.
    global.bootstrap = {
        Modal: class {
            constructor() {}
            show() { shownTimes += 1; }
            hide() {}
            static getInstance() { return { hide() {} }; }
        },
    };
});

function fireNavConfirm(path) {
    // CustomEvent must be cancelable so the guard's preventDefault() registers as defaultPrevented.
    const event = new CustomEvent("htmx:confirm", { cancelable: true });
    const issueRequest = jest.fn();
    Object.defineProperty(event, "detail", { value: { path, issueRequest } });
    document.body.dispatchEvent(event);
    return { event, issueRequest };
}

test("an unmodified switch is not intercepted (fires immediately, no modal)", () => {
    require("../theme/static/scripts/side_panel_utils.js");
    const { event } = fireNavConfirm("/model_builder/switch-model/");
    expect(event.defaultPrevented).toBe(false);
    expect(shownTimes).toBe(0);
});

test("a modified switch is deferred behind the unsaved modal", () => {
    const { tagFormAsModified } = require("../theme/static/scripts/side_panel_utils.js");
    tagFormAsModified();
    const { event } = fireNavConfirm("/model_builder/switch-model/");
    expect(event.defaultPrevented).toBe(true);                 // request held
    expect(shownTimes).toBe(1);                                // modal shown
    expect(document.getElementById("continue-unsaved-modal").getAttribute("onclick"))
        .toBe("proceedWithPendingNavigation()");
});

// Opening Compare no longer discards the panel: the comparison view is a resident sibling, so a modified
// panel survives hidden behind it and a same-slot return resumes it intact. So /compare/ must NOT be
// intercepted — guarding it would falsely warn about losing edits that aren't being lost.
test("a modified Compare navigation is NOT intercepted (Compare is non-destructive)", () => {
    const { tagFormAsModified } = require("../theme/static/scripts/side_panel_utils.js");
    tagFormAsModified();
    const { event } = fireNavConfirm("/model_builder/compare/");  // route name compare-models, path /compare/
    expect(event.defaultPrevented).toBe(false);
    expect(shownTimes).toBe(0);
});

test.each([
    ["+Add Duplicate/Blank", "/model_builder/add-model/"],
    ["+Add Import",          "/model_builder/open-add-model-import-panel/"],
])("a modified %s navigation is deferred behind the unsaved modal", (_label, path) => {
    const { tagFormAsModified } = require("../theme/static/scripts/side_panel_utils.js");
    tagFormAsModified();
    const { event } = fireNavConfirm(path);
    expect(event.defaultPrevented).toBe(true);
    expect(shownTimes).toBe(1);
});

test("remove-model is left alone by this guard (its own confirm handles it)", () => {
    const { tagFormAsModified } = require("../theme/static/scripts/side_panel_utils.js");
    tagFormAsModified();
    const { event } = fireNavConfirm("/model_builder/remove-model/");
    expect(event.defaultPrevented).toBe(false);
    expect(shownTimes).toBe(0);
});

// /add-model/ and /open-add-model-import-panel/ both contain "add-model"; slash-delimiting must keep
// the bare /add-model/ entry from matching the import panel's path (and vice versa is handled above).
test("path matching is slash-delimited (no partial cross-match)", () => {
    const { tagFormAsModified } = require("../theme/static/scripts/side_panel_utils.js");
    tagFormAsModified();
    // A hypothetical neighbour that merely contains "add-model" as a substring must not be intercepted.
    const { event } = fireNavConfirm("/model_builder/add-model-history/");
    expect(event.defaultPrevented).toBe(false);
    expect(shownTimes).toBe(0);
});

test("Continue re-fires the deferred navigation and clears the modified flag", () => {
    const { tagFormAsModified, proceedWithPendingNavigation } =
        require("../theme/static/scripts/side_panel_utils.js");
    tagFormAsModified();
    const { issueRequest } = fireNavConfirm("/model_builder/switch-model/");
    proceedWithPendingNavigation();
    expect(issueRequest).toHaveBeenCalledWith(true);           // exact request re-issued, no re-confirm

    // The flag is now clear, so a second navigation is no longer intercepted.
    const second = fireNavConfirm("/model_builder/switch-model/");
    expect(second.event.defaultPrevented).toBe(false);
});

test("isSidePanelFormModified reflects the modified flag", () => {
    const { tagFormAsModified, isSidePanelFormModified } =
        require("../theme/static/scripts/side_panel_utils.js");
    expect(isSidePanelFormModified()).toBe(false);
    tagFormAsModified();
    expect(isSidePanelFormModified()).toBe(true);
});
