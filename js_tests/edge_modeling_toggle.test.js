const {
    EDGE_MODELING_STORAGE_KEY,
    applyEdgeModelingState,
    handleEdgeModelingChange,
} = require("../theme/static/scripts/edge_modeling_toggle.js");

function renderUnlatchedToggle() {
    document.body.innerHTML = `
        <li id="edge-modeling-toggle-wrapper">
            <input id="edge-modeling-toggle" data-action="edge-modeling-toggle" type="checkbox" />
        </li>
    `;
}

function renderLatchedToggle() {
    document.body.innerHTML = `
        <li id="edge-modeling-toggle-wrapper">
            <input id="edge-modeling-toggle" data-action="edge-modeling-toggle" type="checkbox" checked disabled />
        </li>
    `;
}

beforeEach(() => {
    localStorage.clear();
    document.body.className = "";
    document.body.innerHTML = "";
    window.scheduleRebuildAllLeaderLines = jest.fn();
});

afterEach(() => {
    delete window.scheduleRebuildAllLeaderLines;
});

test("localStorage round-trip: writing 'on' sets body.edge-modeling-on", () => {
    renderUnlatchedToggle();
    const toggle = document.getElementById("edge-modeling-toggle");
    toggle.checked = true;
    handleEdgeModelingChange({ target: toggle });

    expect(localStorage.getItem(EDGE_MODELING_STORAGE_KEY)).toBe("on");
    expect(document.body.classList.contains("edge-modeling-on")).toBe(true);
    expect(document.body.classList.contains("edge-modeling-off")).toBe(false);
});

test("localStorage round-trip: writing 'off' sets body.edge-modeling-off", () => {
    renderUnlatchedToggle();
    localStorage.setItem(EDGE_MODELING_STORAGE_KEY, "on");
    const toggle = document.getElementById("edge-modeling-toggle");
    toggle.checked = false;
    handleEdgeModelingChange({ target: toggle });

    expect(localStorage.getItem(EDGE_MODELING_STORAGE_KEY)).toBe("off");
    expect(document.body.classList.contains("edge-modeling-off")).toBe(true);
    expect(document.body.classList.contains("edge-modeling-on")).toBe(false);
});

test("applyEdgeModelingState reads localStorage and sets body class when unlatched", () => {
    renderUnlatchedToggle();
    localStorage.setItem(EDGE_MODELING_STORAGE_KEY, "on");

    applyEdgeModelingState();

    expect(document.body.classList.contains("edge-modeling-on")).toBe(true);
    expect(document.getElementById("edge-modeling-toggle").checked).toBe(true);
});

test("latched toggle forces edge-modeling-on regardless of localStorage 'off'", () => {
    renderLatchedToggle();
    localStorage.setItem(EDGE_MODELING_STORAGE_KEY, "off");

    applyEdgeModelingState();

    expect(document.body.classList.contains("edge-modeling-on")).toBe(true);
    expect(document.body.classList.contains("edge-modeling-off")).toBe(false);
});

test("flipping the toggle rebuilds leader lines (reflowed canvas)", () => {
    renderUnlatchedToggle();
    const toggle = document.getElementById("edge-modeling-toggle");
    toggle.checked = true;
    handleEdgeModelingChange({ target: toggle });

    expect(window.scheduleRebuildAllLeaderLines).toHaveBeenCalledTimes(1);
});

test("re-applying the same state does not rebuild leader lines", () => {
    renderUnlatchedToggle();
    localStorage.setItem(EDGE_MODELING_STORAGE_KEY, "off");

    // body starts without the edge-modeling-* classes; first apply settles to 'off' (a real flip).
    applyEdgeModelingState();
    window.scheduleRebuildAllLeaderLines.mockClear();

    // A subsequent apply with the same preference is a no-op for the leader lines.
    applyEdgeModelingState();

    expect(window.scheduleRebuildAllLeaderLines).not.toHaveBeenCalled();
});

test("rebuild is skipped when the leaderline module is absent", () => {
    delete window.scheduleRebuildAllLeaderLines;
    renderUnlatchedToggle();
    const toggle = document.getElementById("edge-modeling-toggle");
    toggle.checked = true;

    expect(() => handleEdgeModelingChange({ target: toggle })).not.toThrow();
});
