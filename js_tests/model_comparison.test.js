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
                <button class="model-tab__label fw-bold" data-model-tab="0"></button>
            </span>
            <span class="model-tab text-muted">
                <button class="model-tab__label text-muted" data-model-tab="1"></button>
            </span>
            <span class="model-tab model-tab--compare text-muted">
                <button class="model-tab__label" id="compare-tab"></button>
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
// hidden and the ⇄Compare tab marked active — the state model_comparison.js's afterSwap handler produces.
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

// The visible bold lives on the inner .model-tab__label button (a .btn pins its own font-weight, so the
// wrapper's fw-bold never reaches the text). switch-model never re-renders the strip, so the label bold
// must follow the switch client-side — otherwise the page-render active label stays bold forever.
test("switching moves the bold to the newly-active tab's label, not just its wrapper", () => {
    const refLabel = document.querySelector('[data-model-tab="0"]');
    const compLabel = document.querySelector('[data-model-tab="1"]');
    expect(refLabel.classList.contains("fw-bold")).toBe(true);   // slot 0 active at render

    switchToSlot("1");

    expect(refLabel.classList.contains("fw-bold")).toBe(false);  // Reference label de-emphasised
    expect(refLabel.classList.contains("text-muted")).toBe(true);
    expect(compLabel.classList.contains("fw-bold")).toBe(true);  // Comparison label now bold
    expect(compLabel.classList.contains("text-muted")).toBe(false);
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
    test("opening Compare hides the builder, marks ⇄Compare active, and flips body.comparing", () => {
        enterComparing();
        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(true);
        expect(document.getElementById("toolbar-nav").classList.contains("d-none")).toBe(true);
        expect(document.body.classList.contains("comparing")).toBe(true);
        // ⇄Compare's own tab wrapper stays visible (desktop) and carries the active highlight while comparing;
        // CSS hides it on mobile so the two model tabs fit.
        const compareWrapper = document.getElementById("compare-tab").closest(".model-tab");
        expect(compareWrapper.classList.contains("d-none")).toBe(false);
        expect(compareWrapper.classList.contains("fw-bold")).toBe(true);
        expect(compareWrapper.classList.contains("bg-white")).toBe(true);
        // No model tab carries the active highlight while comparing (no model is being edited) — neither
        // the wrapper nor the inner label button. The label check is the regression guard: the strip is
        // never re-rendered on switch, so the server-baked fw-bold on the originally-active label (slot 0
        // = "Reference model") would otherwise stay bold here — and surface on mobile, where body.comparing
        // reveals the strip but hides the ⇄Compare tab (the bug: the Reference tab bold behind Compare).
        document.querySelectorAll("[data-model-tab]").forEach(label => {
            expect(label.closest(".model-tab").classList.contains("fw-bold")).toBe(false);
            expect(label.classList.contains("fw-bold")).toBe(false);
        });
    });

    // Opening Compare is non-destructive: the side panel, help drawer and results panel all live inside
    // #model-builder-page, which only goes d-none — they ride along hidden and survive intact (none is
    // closed or emptied), so a same-slot return reveals them exactly as left.
    test("opening Compare preserves an open help drawer and results panel hidden, never closing them", () => {
        const page = document.getElementById("model-builder-page");
        page.insertAdjacentHTML("beforeend", '<div id="helpDrawer">class help</div>');
        page.insertAdjacentHTML("beforeend", '<div id="result-block">model results</div>');
        window.closeHelpDrawer = jest.fn();
        window.hidePanelResult = jest.fn();

        enterComparing();

        // Neither is closed; both keep their content, riding along inside the now-d-none builder page.
        expect(window.closeHelpDrawer).not.toHaveBeenCalled();
        expect(window.hidePanelResult).not.toHaveBeenCalled();
        expect(document.getElementById("helpDrawer").innerHTML).toBe("class help");
        expect(document.getElementById("result-block").innerHTML).toBe("model results");
    });

    test("dismissing reveals the builder, clears the ⇄Compare active styling + restores active highlight, empties the view", () => {
        window.destroyComparisonCharts = jest.fn();
        enterComparing();
        dismissCompareView();

        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(false);
        expect(document.getElementById("toolbar-nav").classList.contains("d-none")).toBe(false);
        expect(document.body.classList.contains("comparing")).toBe(false);
        // ⇄Compare's wrapper stays visible but its active styling is cleared on dismiss.
        const compareWrapper = document.getElementById("compare-tab").closest(".model-tab");
        expect(compareWrapper.classList.contains("d-none")).toBe(false);
        expect(compareWrapper.classList.contains("fw-bold")).toBe(false);
        // The active slot (0) regains its highlight; the charts are destroyed and the view emptied.
        expect(document.querySelector('[data-model-tab="0"]').closest(".model-tab").classList.contains("fw-bold")).toBe(true);
        expect(window.destroyComparisonCharts).toHaveBeenCalledTimes(1);
        expect(document.getElementById("comparison-view").innerHTML).toBe("");
        expect(document.getElementById("comparison-view").classList.contains("d-none")).toBe(true);
    });

    // switchToSlot is a plain client-side model switch with no Compare-awareness: the capture-phase tab
    // handler (tested below) is the single owner of Compare-dismiss, and it always tears the view down
    // before the /switch-model/ POST whose switchModelCanvas trigger drives switchToSlot — so Compare is
    // never open by the time switchToSlot runs. These tests pin the plain same-slot no-op and the
    // cross-slot canvas swap (the canonical-id migration the capture handler never touches).
    test("an ordinary same-slot click stays a no-op — no builder re-init", () => {
        // The active model tab still POSTs switch-model (so switchModelCanvas fires for the active slot)
        // even when nothing changes; re-initialising the whole builder on every such redundant click would
        // needlessly re-wire Sortable and rebuild every leader line, so the same-slot switch early-returns.
        const initSpy = jest.fn();
        window.initModelBuilderMain = initSpy;
        const canvasBefore = document.querySelector('[data-model-canvas="0"]');

        switchToSlot("0");  // active slot

        expect(initSpy).not.toHaveBeenCalled();                 // no re-init on a plain same-slot click
        expect(document.querySelector('[data-model-canvas="0"]')).toBe(canvasBefore);
        expect(canvasBefore.classList.contains("d-none")).toBe(false);
    });

    test("a cross-slot switch reveals the other canvas and migrates the canonical ids — no reload", () => {
        // The capture handler has already dismissed Compare; switchToSlot then performs the plain switch.
        window.htmx = { ajax: jest.fn() };
        window.initModelBuilderMain = jest.fn();

        switchToSlot("1");

        expect(document.querySelector('[data-model-canvas="1"]').classList.contains("d-none")).toBe(false);
        expect(document.querySelector('[data-model-canvas="0"]').classList.contains("d-none")).toBe(true);
        expect(document.getElementById("model-tab-strip").dataset.activeSlot).toBe("1");
        expect(window.htmx.ajax).not.toHaveBeenCalled();        // no reload — the canvas was resident
        expect(duplicateIds()).toEqual([]);                     // canonical ids migrated cleanly
    });

    // The capture-phase model-tab click handler runs while Compare is open, ahead of HTMX's bubble-phase
    // switch-model POST. It dismisses the dashboard first so a cross-slot unsaved warning anchors on the
    // revealed model; a same-slot click needs no switch, so it is preventDefaulted (no POST, panel resumes,
    // no warning). Dispatch a real bubbling+cancelable click so capture-phase + preventDefault are exercised.
    function clickModelTab(slot) {
        const label = document.querySelector(`[data-model-tab="${slot}"]`);
        const event = new MouseEvent("click", { bubbles: true, cancelable: true });
        label.dispatchEvent(event);
        return event;
    }

    test("a same-slot tab click dismisses the view, preventDefaults (no POST), and resumes the panel", () => {
        window.destroyComparisonCharts = jest.fn();
        const initSpy = jest.fn();
        window.initModelBuilderMain = initSpy;
        // An open side panel sits inside the (hidden) builder page; it must survive the dismiss untouched.
        document.getElementById("model-builder-page").insertAdjacentHTML(
            "beforeend", '<div id="sidePanel">edit form</div>');
        window.closeAndEmptySidePanel = jest.fn();

        enterComparing();
        const event = clickModelTab("0");  // active slot

        expect(event.defaultPrevented).toBe(true);                          // no switch-model POST fires
        expect(document.getElementById("comparison-view").classList.contains("d-none")).toBe(true);
        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(false);
        // The panel is resumed intact, never closed/emptied.
        expect(window.closeAndEmptySidePanel).not.toHaveBeenCalled();
        expect(document.getElementById("sidePanel").innerHTML).toBe("edit form");
        expect(initSpy).toHaveBeenCalled();                                 // visible canvas's lines rebuilt
        expect(window.destroyComparisonCharts).toHaveBeenCalledTimes(1);
    });

    test("a cross-slot tab click tears down the view but lets the click (the switch POST) through", () => {
        window.destroyComparisonCharts = jest.fn();
        window.initModelBuilderMain = jest.fn();

        enterComparing();
        const event = clickModelTab("1");  // other slot

        expect(event.defaultPrevented).toBe(false);                        // the switch-model POST proceeds
        // The dashboard is torn down first, so the switch's unsaved modal would land over the revealed model.
        expect(document.getElementById("comparison-view").classList.contains("d-none")).toBe(true);
        expect(document.getElementById("model-builder-page").classList.contains("d-none")).toBe(false);
        expect(window.destroyComparisonCharts).toHaveBeenCalledTimes(1);
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
