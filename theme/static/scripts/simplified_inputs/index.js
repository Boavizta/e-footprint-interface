"use strict";

const { createWorkspace } = require("./workspace.js");
const { registerBookmarks } = require("./bookmarks.js");
const { registerConfiguration } = require("./configuration.js");

// Compose feature modules without publishing widget functions on window.
const workspace = createWorkspace();

// Bootstrap delegates dropdown clicks in document capture, so intercept exports
// at window capture before a dirty Configure draft can open the menu.
window.addEventListener("click", event => {
    const element = event.target.closest("[data-workspace-export]");
    if (!element) return;
    if (workspace.configureForm()?.dataset.dirty !== "true") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    workspace.activeWorkspace().querySelector("[data-simplified-notice]").textContent =
        "Save or discard Configure changes before exporting.";
}, true);

registerBookmarks();
registerConfiguration(workspace);
workspace.registerWorkspace();

module.exports = { workspace };
