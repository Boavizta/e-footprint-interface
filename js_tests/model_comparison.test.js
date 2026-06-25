// Jest coverage for the two-canvas id-namespacing the comparison workspace depends on.
// The headline correctness risk is two resident canvases sharing a DOM id;
// the active canvas owns the canonical structural ids and the parked one suffixes them by slot, with
// the canonical ids migrating on switch. These tests assert that migration keeps every id unique.

const { rekeyCanvas, switchToSlot, openCompareView, dismissCompareView } =
    require("../theme/static/scripts/model_comparison.js");

function twoCanvasDom() {
    document.body.innerHTML = `
        <nav id="model-tab-strip" data-active-slot="0">
            <span class="model-tab fw-bold bg-white border border-bottom-0">
                <button data-model-tab="0"></button>
            </span>
            <span class="model-tab text-muted">
                <button data-model-tab="1"></button>
            </span>
            <span class="model-tab model-tab--compare text-muted">
                <button id="compare-tab"></button>
            </span>
        </nav>
        <nav id="toolbar-nav"></nav>
        <div id="model-builder-page">
            <div class="scrollable-area" id="model-canva-scrollable-area">
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
            </div>
        </div>
        <div id="comparison-view" class="d-none"></div>
    `;
}

// Put the DOM into the comparing state: the comparison fragment swapped in, the view shown, the builder
// hidden and the ⇄Compare tab hidden — the state model_comparison.js's afterSwap handler produces.
function enterComparing() {
    const view = document.getElementById("comparison-view");
    view.classList.remove("d-none");
    view.innerHTML = '<div id="comparison-dashboard">charts</div>';
    openCompareView();
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

// The comparison view is a resident sibling of the canvases: opening Compare hides the builder + the
// ⇄Compare tab and shows the view; a model tab then dismisses it client-side (reveal the canvas, no
// reload). These tests pin the toggle and the reveal-from-comparison-view switch branch.
describe("resident comparison view toggle", () => {
    test("opening Compare hides the builder + ⇄Compare tab and flips body.comparing", () => {
        enterComparing();
        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(true);
        expect(document.getElementById("toolbar-nav").classList.contains("d-none")).toBe(true);
        expect(document.body.classList.contains("comparing")).toBe(true);
        // ⇄Compare's own tab wrapper is hidden while comparing (so the strip is just the two model tabs).
        expect(document.getElementById("compare-tab").closest(".model-tab").classList.contains("d-none")).toBe(true);
        // No model tab carries the active highlight while comparing (no model is being edited).
        expect(document.querySelectorAll(".model-tab.fw-bold").length).toBe(0);
    });

    test("dismissing reveals the builder, restores the ⇄Compare tab + active highlight, empties the view", () => {
        window.destroyComparisonCharts = jest.fn();
        enterComparing();
        dismissCompareView();

        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(false);
        expect(document.getElementById("toolbar-nav").classList.contains("d-none")).toBe(false);
        expect(document.body.classList.contains("comparing")).toBe(false);
        expect(document.getElementById("compare-tab").closest(".model-tab").classList.contains("d-none")).toBe(false);
        // The active slot (0) regains its highlight; the charts are destroyed and the view emptied.
        expect(document.querySelector('[data-model-tab="0"]').closest(".model-tab").classList.contains("fw-bold")).toBe(true);
        expect(window.destroyComparisonCharts).toHaveBeenCalledTimes(1);
        expect(document.getElementById("comparison-view").innerHTML).toBe("");
        expect(document.getElementById("comparison-view").classList.contains("d-none")).toBe(true);
    });

    test("a same-slot model tab dismisses the comparison view and rebuilds lines — no reload", () => {
        window.destroyComparisonCharts = jest.fn();
        window.htmx = { ajax: jest.fn() };
        const initSpy = jest.fn();
        window.initModelBuilderMain = initSpy;
        const canvasBefore = document.querySelector('[data-model-canvas="0"]');

        enterComparing();
        switchToSlot("0");  // the model tab fires switchModelCanvas for the active slot

        // Reveal: the comparison view is gone, the builder is back, and the SAME canvas element is shown
        // (client-side reveal, never a re-render / reload).
        expect(document.getElementById("comparison-view").classList.contains("d-none")).toBe(true);
        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(false);
        expect(document.querySelector('[data-model-canvas="0"]')).toBe(canvasBefore);
        expect(canvasBefore.classList.contains("d-none")).toBe(false);
        expect(window.htmx.ajax).not.toHaveBeenCalled();        // no /model_builder/ reload
        expect(initSpy).toHaveBeenCalled();                     // visible canvas's lines rebuilt
        expect(window.destroyComparisonCharts).toHaveBeenCalledTimes(1);
    });

    test("an ordinary same-slot click (comparison not open) stays a no-op — no builder re-init", () => {
        // The active model tab still POSTs switch-model (so switchModelCanvas fires for the active slot)
        // even when nothing is being dismissed; re-initialising the whole builder on every such redundant
        // click would needlessly re-wire Sortable and rebuild every leader line. With the comparison view
        // closed, the same-slot switch must early-return without touching initModelBuilderMain.
        const initSpy = jest.fn();
        window.initModelBuilderMain = initSpy;
        const canvasBefore = document.querySelector('[data-model-canvas="0"]');

        switchToSlot("0");  // active slot, comparison view never opened

        expect(initSpy).not.toHaveBeenCalled();                 // no re-init on a plain same-slot click
        expect(document.querySelector('[data-model-canvas="0"]')).toBe(canvasBefore);
        expect(canvasBefore.classList.contains("d-none")).toBe(false);
    });

    test("a cross-slot model tab dismisses the view then switches to the other canvas — no reload", () => {
        window.destroyComparisonCharts = jest.fn();
        window.htmx = { ajax: jest.fn() };
        window.initModelBuilderMain = jest.fn();

        enterComparing();
        switchToSlot("1");

        expect(document.getElementById("comparison-view").classList.contains("d-none")).toBe(true);
        expect(document.querySelector('[data-model-canvas="1"]').classList.contains("d-none")).toBe(false);
        expect(document.querySelector('[data-model-canvas="0"]').classList.contains("d-none")).toBe(true);
        expect(document.getElementById("model-tab-strip").dataset.activeSlot).toBe("1");
        expect(window.htmx.ajax).not.toHaveBeenCalled();        // no reload — the canvas was resident
        expect(duplicateIds()).toEqual([]);                     // canonical ids migrated cleanly
    });

    test("the htmx:afterSwap into #comparison-view reveals it and opens the view", () => {
        const view = document.getElementById("comparison-view");
        view.innerHTML = '<div id="comparison-dashboard"></div>';
        const event = new CustomEvent("htmx:afterSwap", { bubbles: true });
        Object.defineProperty(event, "target", { value: view });
        document.body.dispatchEvent(event);

        expect(view.classList.contains("d-none")).toBe(false);
        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(true);
        expect(document.body.classList.contains("comparing")).toBe(true);
    });
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
