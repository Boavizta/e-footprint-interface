const fs = require("fs");
const path = require("path");

const FIXTURE = path.join(__dirname, "fixtures", "sortable_canvas_six_lists.html");

function loadModule() {
    jest.resetModules();
    return require("../theme/static/scripts/model_builder_main.js");
}

beforeEach(() => {
    document.body.innerHTML = fs.readFileSync(FIXTURE, "utf8");
    document.body.setAttribute("hx-headers", JSON.stringify({"X-CSRFToken": "csrf-token"}));
    global.updateLines = jest.fn();
    global.fetch = jest.fn(() => Promise.resolve({ok: true}));
    global.htmx = {ajax: jest.fn(() => Promise.resolve())};
    const sortablesByElement = new Map();
    global.Sortable = jest.fn(function (element, options) {
        this.el = element;
        this.options = options;
        this.toArray = jest.fn(() => Array.from(element.children, child => child.id));
        this.destroy = jest.fn(() => sortablesByElement.delete(element));
        sortablesByElement.set(element, this);
    });
    global.Sortable.get = jest.fn(element => sortablesByElement.get(element));
});

afterEach(() => {
    delete global.Sortable;
    delete global.fetch;
    delete global.htmx;
    delete global.updateLines;
});

test("initializes the six rendered card lists using their existing id attributes", () => {
    const {CARD_ORDER_LIST_IDS, initSortableObjectCards} = loadModule();

    initSortableObjectCards();

    const initializedIds = global.Sortable.mock.calls.map(([element]) => element.id);
    expect(initializedIds).toEqual(CARD_ORDER_LIST_IDS);
    global.Sortable.mock.calls.forEach(([, options]) => expect(options.dataIdAttr).toBe("id"));
    expect(initializedIds).toContain("external-api-list");
});

test("every initialized sortable drag persists the current order of every initialized list", () => {
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    const instances = global.Sortable.mock.instances;

    instances.forEach((instance, index) => {
        instance.toArray.mockReturnValue([`${instance.el.id}-card-${index}`]);
    });

    instances.forEach(instance => instance.options.onEnd());

    expect(global.fetch).toHaveBeenCalledTimes(instances.length);
    const initializedIds = instances.map(instance => instance.el.id);
    global.fetch.mock.calls.forEach(([url, request]) => {
        const payload = JSON.parse(request.body);
        expect(url).toBe("/model_builder/save-card-order/");
        expect(request.method).toBe("POST");
        expect(request.headers["X-CSRFToken"]).toBe("csrf-token");
        expect(Object.keys(payload)).toEqual(initializedIds);
        instances.forEach(instance => expect(payload[instance.el.id]).toEqual(instance.toArray()));
    });
});

test("one drag end saves once, refreshes only storage metadata, clears grab state, and updates leader lines", async () => {
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    const grabbed = document.querySelector("#server-list > div");
    grabbed.classList.add("grabbing");

    global.Sortable.mock.instances[0].options.onEnd();
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.htmx.ajax).toHaveBeenCalledWith(
        "GET",
        "/model_builder/workspace-storage-status/",
        {target: "#workspace-storage-status", swap: "none"},
    );
    expect(grabbed.classList.contains("grabbing")).toBe(false);
    expect(global.updateLines).toHaveBeenCalledTimes(1);
});

test("reinitialization destroys old sortables and a later drag sends one request", () => {
    const {CARD_ORDER_LIST_IDS, initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    const oldInstances = global.Sortable.mock.instances.slice();

    initSortableObjectCards();
    const currentInstances = global.Sortable.mock.instances.slice(CARD_ORDER_LIST_IDS.length);
    global.fetch.mockClear();
    currentInstances[0].options.onEnd();

    oldInstances.forEach(instance => expect(instance.destroy).toHaveBeenCalledTimes(1));
    currentInstances.forEach(instance => expect(instance.destroy).not.toHaveBeenCalled());
    expect(global.fetch).toHaveBeenCalledTimes(1);
});

test("a rejected background save keeps the DOM order and is handled", async () => {
    global.fetch.mockImplementation(() => Promise.reject(new Error("offline")));
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    const serverList = document.getElementById("server-list");
    const reorderedIds = Array.from(serverList.children, child => child.id).reverse();
    serverList.prepend(serverList.lastElementChild);

    global.Sortable.mock.instances[0].options.onEnd();
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(Array.from(serverList.children, child => child.id)).toEqual(reorderedIds);
    expect(global.htmx.ajax).not.toHaveBeenCalled();
});

test("a rejected card-order response does not refresh storage metadata", async () => {
    global.fetch.mockResolvedValue({ok: false});
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();

    global.Sortable.mock.instances[0].options.onEnd();
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(global.htmx.ajax).not.toHaveBeenCalled();
});

test("a successful Sankey deletion refreshes storage metadata through its fetch boundary", async () => {
    const originalFetch = global.fetch;
    const {installSankeyStorageStatusRefresh} = loadModule();
    installSankeyStorageStatusRefresh();

    await global.fetch("/model_builder/sankey-delete-card/", {method: "POST"});
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(originalFetch).toHaveBeenCalledTimes(1);
    expect(global.htmx.ajax).toHaveBeenCalledWith(
        "GET",
        "/model_builder/workspace-storage-status/",
        {target: "#workspace-storage-status", swap: "none"},
    );
});

test("HTMX button restoration does not overwrite control state changed during a request", () => {
    document.body.innerHTML = `
        <button id="persistently-disabled" disabled>Unavailable</button>
        <input id="builder-payload" disabled>
    `;
    loadModule();
    const xhr = {};
    const button = document.getElementById("persistently-disabled");
    const payload = document.getElementById("builder-payload");

    document.body.dispatchEvent(new CustomEvent("htmx:beforeRequest", {detail: {xhr}}));
    button.disabled = false;
    payload.disabled = false;
    document.body.dispatchEvent(new CustomEvent("htmx:afterRequest", {detail: {xhr}}));

    expect(button.disabled).toBe(true);
    expect(payload.disabled).toBe(false);
});
