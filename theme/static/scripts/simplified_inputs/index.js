"use strict";

const { createWorkspace } = require("./workspace.js");
const { createFieldEdits } = require("./field_edits.js");
const { registerBookmarks } = require("./bookmarks.js");
const { registerConfiguration } = require("./configuration.js");

// Compose feature modules without publishing widget functions on window.
const workspace = createWorkspace();
const fieldEdits = createFieldEdits({ activeWorkspace: workspace.activeWorkspace });

// Bootstrap delegates dropdown clicks in document capture, so intercept exports
// at window capture before a dirty Configure draft can open the menu.
window.addEventListener("click", event => {
    const element = event.target.closest("[data-workspace-export]");
    if (!element || document.body.dataset.workspaceMutation === "updating") return;
    if (workspace.configureForm()?.dataset.dirty !== "true") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const notice = document.createElement("p");
    notice.setAttribute("role", "status");
    notice.dataset.simplifiedNotice = "";
    notice.textContent = "Save or discard Configure changes before exporting.";
    const activeWorkspace = workspace.activeWorkspace();
    activeWorkspace.querySelector("[data-simplified-notice]")?.remove();
    activeWorkspace.querySelector(".simplified-header").after(notice);
}, true);

// Keep registration synchronous and before model_builder_main.js, as in the
// original script: editor baselines and bookmark locks observe settled controls.
fieldEdits.registerFieldEdits();
registerBookmarks();
registerConfiguration(workspace);
workspace.registerWorkspace();

module.exports = { workspace, fieldEdits };
