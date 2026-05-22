const { initBootstrapWidgets } = require("../theme/static/scripts/bootstrap_widgets.js");

let popoverCalls;
let tooltipCalls;

beforeEach(() => {
    document.body.innerHTML = "";
    popoverCalls = [];
    tooltipCalls = [];
    global.bootstrap = {
        Popover: {
            getOrCreateInstance: el => {
                popoverCalls.push(el);
                return { _id: el.id };
            },
        },
        Tooltip: {
            getOrCreateInstance: (el, config) => {
                tooltipCalls.push({ el, config });
                return { _id: el.id };
            },
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

test("initBootstrapWidgets no-ops when bootstrap is undefined", () => {
    delete global.bootstrap;
    document.body.innerHTML = `<div data-bs-toggle="popover"></div>`;
    expect(() => initBootstrapWidgets(document)).not.toThrow();
});
