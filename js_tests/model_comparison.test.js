// Jest coverage for the two-canvas id-namespacing the comparison workspace depends on.
// The headline correctness risk is two resident canvases sharing a DOM id;
// the active canvas owns the canonical structural ids and the parked one suffixes them by slot, with
// the canonical ids migrating on switch. These tests assert that migration keeps every id unique.

const { rekeyCanvas, switchToSlot } = require("../theme/static/scripts/model_comparison.js");

function twoCanvasDom() {
    document.body.innerHTML = `
        <nav id="model-tab-strip" data-active-slot="0">
            <button data-model-tab="0" class="fw-bold bg-white border border-bottom-0"></button>
            <button data-model-tab="1" class="text-muted"></button>
        </nav>
        <div data-model-canvas="0" id="model-canva-0">
            <div data-canvas-id="usage-pattern-container" id="usage-pattern-container" data-tour-target="usage-patterns"></div>
            <div data-canvas-id="up-list" id="up-list"></div>
            <button data-canvas-id="btn-add-server" id="btn-add-server"></button>
        </div>
        <div data-model-canvas="1" id="model-canva-1" class="d-none">
            <div data-canvas-id="usage-pattern-container" id="usage-pattern-container-1"></div>
            <div data-canvas-id="up-list" id="up-list-1"></div>
            <button data-canvas-id="btn-add-server" id="btn-add-server-1"></button>
        </div>
    `;
}

function allIds() {
    return Array.from(document.querySelectorAll("[id]")).map(el => el.id);
}

function duplicateIds() {
    const seen = {};
    allIds().forEach(id => { seen[id] = (seen[id] || 0) + 1; });
    return Object.keys(seen).filter(id => seen[id] > 1);
}

beforeEach(() => {
    window.initModelBuilderMain = () => {};
    twoCanvasDom();
});

test("the parked canvas suffixes its structural ids so nothing collides at rest", () => {
    expect(duplicateIds()).toEqual([]);
    expect(document.getElementById("up-list")).not.toBeNull();        // active = canonical
    expect(document.getElementById("up-list-1")).not.toBeNull();      // parked = suffixed
});

test("rekeyCanvas(canonical) restores the bare id and the tour target", () => {
    const parked = document.querySelector('[data-model-canvas="1"]');
    rekeyCanvas(parked, "1", true);
    expect(parked.querySelector('[data-canvas-id="up-list"]').id).toBe("up-list");
    expect(parked.querySelector('[data-canvas-id="usage-pattern-container"]').getAttribute("data-tour-target"))
        .toBe("usage-patterns");
});

test("rekeyCanvas(parked) suffixes the id and drops the tour target", () => {
    const active = document.querySelector('[data-model-canvas="0"]');
    rekeyCanvas(active, "0", false);
    expect(active.querySelector('[data-canvas-id="up-list"]').id).toBe("up-list-0");
    expect(active.querySelector('[data-canvas-id="usage-pattern-container"]').hasAttribute("data-tour-target"))
        .toBe(false);
});

test("switching to slot 1 migrates the canonical ids and never collides", () => {
    switchToSlot("1");

    expect(duplicateIds()).toEqual([]);
    // Canonical ids now live on the newly-active canvas, suffixed ids on the parked one.
    expect(document.querySelector('[data-model-canvas="1"]').querySelector("#up-list")).not.toBeNull();
    expect(document.querySelector('[data-model-canvas="0"]').querySelector("#up-list-0")).not.toBeNull();
    // Exactly one element carries each tour target after the switch.
    expect(document.querySelectorAll('[data-tour-target="usage-patterns"]').length).toBe(1);
    // Visibility + active pointer follow the switch.
    expect(document.querySelector('[data-model-canvas="1"]').classList.contains("d-none")).toBe(false);
    expect(document.querySelector('[data-model-canvas="0"]').classList.contains("d-none")).toBe(true);
    expect(document.getElementById("model-tab-strip").dataset.activeSlot).toBe("1");
});

test("switching back and forth keeps ids unique throughout", () => {
    switchToSlot("1");
    switchToSlot("0");
    expect(duplicateIds()).toEqual([]);
    expect(document.querySelector('[data-model-canvas="0"]').querySelector("#up-list")).not.toBeNull();
    expect(document.querySelector('[data-model-canvas="1"]').querySelector("#up-list-1")).not.toBeNull();
});

// The results panel is a singleton bound to the active slot, so switching must collapse it — otherwise
// the still-open panel covers the now-active canvas and the OOB-rebound bar floats mid-air over it.
test("switching collapses an open results panel (singleton bound to the active slot)", () => {
    document.body.insertAdjacentHTML("beforeend", '<div id="result-block">some model results</div>');
    window.hidePanelResult = jest.fn();
    switchToSlot("1");
    expect(window.hidePanelResult).toHaveBeenCalledTimes(1);
});

test("switching does not touch a closed results panel (empty #result-block)", () => {
    document.body.insertAdjacentHTML("beforeend", '<div id="result-block"></div>');
    window.hidePanelResult = jest.fn();
    switchToSlot("1");
    expect(window.hidePanelResult).not.toHaveBeenCalled();
});

// The side panel is a singleton bound to the active slot: an open edit form belongs to the model being
// left, so switching must close it (a stale-model save would otherwise target the wrong model).
test("switching closes an open side panel (singleton bound to the active slot)", () => {
    document.body.insertAdjacentHTML("beforeend", '<div id="sidePanel"></div>');  // open = no d-none
    window.closeAndEmptySidePanel = jest.fn();
    switchToSlot("1");
    expect(window.closeAndEmptySidePanel).toHaveBeenCalledTimes(1);
});

test("switching leaves a closed side panel (d-none) untouched", () => {
    document.body.insertAdjacentHTML("beforeend", '<div id="sidePanel" class="d-none"></div>');
    window.closeAndEmptySidePanel = jest.fn();
    switchToSlot("1");
    expect(window.closeAndEmptySidePanel).not.toHaveBeenCalled();
});

// remove-model replaces the whole builder (discarding an open side panel). It keeps its own destructive
// confirm rather than the shared unsaved modal, so the two never stack — instead the unsaved-changes
// warning is folded into that single dialog when the open panel is dirty.
function fireRemoveConfirm() {
    document.body.insertAdjacentHTML("beforeend",
        '<button id="rm" data-confirm-remove-model="Remove this model?"></button>');
    const event = new CustomEvent("htmx:confirm", { bubbles: true, cancelable: true });
    const issueRequest = jest.fn();
    Object.defineProperty(event, "detail", { value: { issueRequest } });
    document.getElementById("rm").dispatchEvent(event);
    return { issueRequest };
}

test("remove-model confirm folds in the unsaved-changes warning when the panel is dirty", () => {
    window.isSidePanelFormModified = () => true;
    let asked = null;
    window.confirm = (m) => { asked = m; return false; };  // user declines
    const { issueRequest } = fireRemoveConfirm();
    expect(asked).toBe("Remove this model? You also have unsaved changes in the open panel that will be lost.");
    expect(issueRequest).not.toHaveBeenCalled();
});

test("remove-model confirm is the plain message when the panel is clean; Yes issues the request", () => {
    window.isSidePanelFormModified = () => false;
    let asked = null;
    window.confirm = (m) => { asked = m; return true; };  // user confirms
    const { issueRequest } = fireRemoveConfirm();
    expect(asked).toBe("Remove this model?");
    expect(issueRequest).toHaveBeenCalledWith(true);
});
