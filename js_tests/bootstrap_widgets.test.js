const { initBootstrapWidgets, disposeShownWidgets } = require("../theme/static/scripts/bootstrap_widgets.js");

let popoverCalls;
let tooltipCalls;
let disposeCalls;

beforeEach(() => {
    document.body.innerHTML = "";
    popoverCalls = [];
    tooltipCalls = [];
    disposeCalls = [];
    global.bootstrap = {
        Popover: {
            getOrCreateInstance: el => {
                popoverCalls.push(el);
                return { _id: el.id };
            },
            getInstance: el => ({ dispose: () => disposeCalls.push(`popover:${el.id}`) }),
        },
        Tooltip: {
            getOrCreateInstance: (el, config) => {
                tooltipCalls.push({ el, config });
                return { _id: el.id };
            },
            getInstance: el => ({ dispose: () => disposeCalls.push(`tooltip:${el.id}`) }),
        },
    };
});

afterEach(() => {
    delete global.bootstrap;
});

test("initBootstrapWidgets initializes popovers in the given root", () => {
    document.body.innerHTML = `
        <div id="a" data-bs-toggle="popover"></div>
        <div id="b" data-bs-toggle="popover"></div>
    `;
    initBootstrapWidgets(document);
    expect(popoverCalls.map(el => el.id).sort()).toEqual(["a", "b"]);
});

test("initBootstrapWidgets initializes generic tooltips but skips .truncated-text-tooltip", () => {
    document.body.innerHTML = `
        <button id="disabled-btn" data-bs-toggle="tooltip"></button>
        <span id="truncated" class="truncated-text-tooltip" data-bs-toggle="tooltip"></span>
    `;
    initBootstrapWidgets(document);
    expect(tooltipCalls.map(c => c.el.id)).toEqual(["disabled-btn"]);
});

test("initBootstrapWidgets scopes to the provided root", () => {
    document.body.innerHTML = `
        <div id="outside" data-bs-toggle="popover"></div>
        <div id="scope">
            <div id="inside" data-bs-toggle="popover"></div>
        </div>
    `;
    initBootstrapWidgets(document.getElementById("scope"));
    expect(popoverCalls.map(el => el.id)).toEqual(["inside"]);
});

test("initBootstrapWidgets initializes the scope element itself when it matches", () => {
    // After an htmx OOB outerHTML swap, htmx fires htmx:afterSettle with elt = the
    // newly-swapped-in root element. If the tooltip attributes live on that root (as
    // they do on #btn-open-panel-result and #show-results-toolbar-btn), descendants-only
    // queries would miss it and the tooltip would never get a Bootstrap instance until
    // the next full page reload.
    document.body.innerHTML = `<div id="root" data-bs-toggle="tooltip" title="x"></div>`;
    initBootstrapWidgets(document.getElementById("root"));
    expect(tooltipCalls.map(c => c.el.id)).toEqual(["root"]);
});

test("initBootstrapWidgets no-ops when bootstrap is undefined", () => {
    delete global.bootstrap;
    document.body.innerHTML = `<div data-bs-toggle="popover"></div>`;
    expect(() => initBootstrapWidgets(document)).not.toThrow();
});

test("disposeShownWidgets disposes shown tooltips/popovers in the swap target", () => {
    // A swap that removes a trigger while its tip is shown would otherwise orphan the
    // tip (Bootstrap appends it to <body>, outside the swap target). The shown trigger
    // is identified by aria-describedby pointing at a tooltip-/popover- tip.
    document.body.innerHTML = `
        <div id="target">
            <button id="shown-tip" aria-describedby="tooltip1234"></button>
            <button id="shown-pop" aria-describedby="popover5678"></button>
            <button id="not-shown"></button>
        </div>`;
    disposeShownWidgets(document.getElementById("target"));
    expect(disposeCalls.sort()).toEqual(["popover:shown-pop", "tooltip:shown-tip"]);
});

test("disposeShownWidgets leaves shown widgets outside the swap target untouched", () => {
    document.body.innerHTML = `
        <button id="outside" aria-describedby="tooltip9999"></button>
        <div id="target"></div>`;
    disposeShownWidgets(document.getElementById("target"));
    expect(disposeCalls).toEqual([]);
});

test("disposeShownWidgets disposes the scope element itself when it matches", () => {
    // OOB outerHTML swaps fire with the swapped element as the root; if it carries the
    // shown tip, a descendants-only query would miss it.
    document.body.innerHTML = `<button id="root" aria-describedby="tooltip4321"></button>`;
    disposeShownWidgets(document.getElementById("root"));
    expect(disposeCalls).toEqual(["tooltip:root"]);
});

test("disposeShownWidgets ignores aria-describedby unrelated to bootstrap tips", () => {
    document.body.innerHTML = `
        <div id="target"><input id="field" aria-describedby="help-text"></div>`;
    disposeShownWidgets(document.getElementById("target"));
    expect(disposeCalls).toEqual([]);
});

test("disposeShownWidgets no-ops when bootstrap is undefined", () => {
    delete global.bootstrap;
    document.body.innerHTML = `<button aria-describedby="tooltip1"></button>`;
    expect(() => disposeShownWidgets(document)).not.toThrow();
});
