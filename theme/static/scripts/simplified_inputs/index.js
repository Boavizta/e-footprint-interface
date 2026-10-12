"use strict";

const { createWorkspace } = require("./workspace.js");
const { createFieldEdits } = require("./field_edits.js");
const { registerBookmarks } = require("./bookmarks.js");
const { registerConfiguration } = require("./configuration.js");

// Compose feature modules without publishing widget functions on window.
const workspace = createWorkspace();
const { configureForm, deferExit, replayClick, isReplaying } = workspace;
const fieldEdits = createFieldEdits({ activeWorkspace: workspace.activeWorkspace, continueExport });
const { completeFocusedEditForExport } = fieldEdits;
function continueExport(element) {
    if (element.matches("a")) {
        // Save settlement can outlive the click's popup permission. Download in the current
        // browsing context; the attachment response leaves the workspace in place.
        const link = document.createElement("a");
        link.href = element.href;
        link.click();
    } else queueMicrotask(() => replayClick(element));
}
document.addEventListener("mousedown", event => {
    // Keep focus until activation: a blur save would disable the export control
    // before click. Pressing alone (or cancelling the gesture) must not export.
    if (event.button === 0 && event.target.closest("[data-workspace-export]")
        && document.activeElement?.closest("[data-simplified-editor]")) event.preventDefault();
}, true);

// Bootstrap delegates dropdown clicks in document capture, so intercept exports
// at window capture before the menu can toggle ahead of the save.
window.addEventListener("click", event => {
    const element = event.target.closest("[data-workspace-export]");
    if (!element || isReplaying() || document.body.dataset.workspaceMutation === "updating") return;
    if (!configureForm() && completeFocusedEditForExport(element)) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
    }
    if (!configureForm()) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    deferExit(() => continueExport(element));
}, true);

// Keep registration synchronous and before model_builder_main.js, as in the
// original script: editor baselines and bookmark locks observe settled controls.
fieldEdits.registerFieldEdits();
registerBookmarks();
registerConfiguration(workspace);
workspace.registerWorkspace();

module.exports = { workspace, fieldEdits };
