const fs = require("fs");
const path = require("path");

const FIXTURE = path.join(__dirname, "fixtures", "sortable_canvas_six_lists.html");

function loadModule() {
    require("../theme/static/scripts/modal_utils.js");
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

test("every completed sortable drag persists the current order of every initialized list", async () => {
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    const instances = global.Sortable.mock.instances;

    instances.forEach((instance, index) => {
        instance.toArray.mockReturnValue([`${instance.el.id}-card-${index}`]);
    });

    for (const instance of instances) {
        instance.options.onEnd({from: instance.el});
        await new Promise(resolve => setTimeout(resolve, 0));
    }

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
    const started = jest.fn();
    document.body.addEventListener("workspace-mutation:started", started, {once: true});
    const grabbed = document.querySelector("#server-list > div");
    grabbed.classList.add("grabbing");

    global.Sortable.mock.instances[0].options.onEnd({from: global.Sortable.mock.instances[0].el});
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(started.mock.calls[0][0].detail.elt).toBe(global.Sortable.mock.instances[0].el);
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
    currentInstances[0].options.onEnd({from: currentInstances[0].el});

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

    global.Sortable.mock.instances[0].options.onEnd({from: global.Sortable.mock.instances[0].el});
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(Array.from(serverList.children, child => child.id)).toEqual(reorderedIds);
    expect(global.htmx.ajax).not.toHaveBeenCalled();
});

test("a rejected card-order response does not refresh storage metadata", async () => {
    global.fetch.mockResolvedValue({ok: false});
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();

    global.Sortable.mock.instances[0].options.onEnd({from: global.Sortable.mock.instances[0].el});
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(global.htmx.ajax).not.toHaveBeenCalled();
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

function requestEvent(type, detail, target = document.body) {
    const event = new CustomEvent(type, {bubbles: true, cancelable: true, detail});
    target.dispatchEvent(event);
    return event;
}

function startMutation(elt = document.body) {
    const xhr = {getResponseHeader: jest.fn(() => null)};
    requestEvent("htmx:beforeRequest", {xhr, elt, requestConfig: {verb: "post", path: "/edit/"}});
    return xhr;
}

function completeMutation(xhr, {successful = true, swap = true} = {}) {
    requestEvent("htmx:beforeSwap", {xhr, shouldSwap: swap});
    requestEvent("htmx:afterRequest", {xhr, successful});
    if (swap) requestEvent("htmx:afterSettle", {xhr});
}

test("a mutation captures its payload before locking and blocks further edits, switches and exports until settlement", () => {
    document.body.innerHTML = `
        <div id="sidePanel"><input id="value" value="12"><select disabled></select><button>Save</button></div>
        <button data-model-tab="1" hx-post="/switch/">Switch</button>
        <a data-workspace-control href="/download/">Export</a>
        <button id="read">Read</button>
    `;
    loadModule();
    const field = document.getElementById("value");
    const xhr = startMutation(field);
    expect(field.disabled).toBe(true);
    expect(document.body.dataset.workspaceMutation).toBe("updating");
    expect(requestEvent("htmx:confirm", {elt: field, verb: "post"}).defaultPrevented).toBe(true);
    expect(requestEvent("htmx:beforeRequest", {xhr: {}, requestConfig: {verb: "post"}}).defaultPrevented).toBe(true);
    for (const selector of ["[data-model-tab]", "[data-workspace-control]"]) {
        const click = new MouseEvent("click", {bubbles: true, cancelable: true});
        document.querySelector(selector).dispatchEvent(click);
        expect(click.defaultPrevented).toBe(true);
    }
    expect(document.getElementById("read").disabled).toBe(false);
    requestEvent("htmx:beforeSwap", {xhr, shouldSwap: true});
    requestEvent("htmx:afterRequest", {xhr, successful: true});
    expect(field.disabled).toBe(true);
    requestEvent("htmx:afterSettle", {xhr});
    expect(field.disabled).toBe(false);
    expect(document.querySelector("select").disabled).toBe(true);
    expect(document.body.dataset.workspaceMutation).toBeUndefined();
    expect(document.querySelector("a").hasAttribute("aria-disabled")).toBe(false);
});

test("swapped controls keep server constraints and are locked until the initiating response settles", () => {
    document.body.innerHTML = '<div id="sidePanel"><input></div>';
    loadModule();
    const xhr = startMutation();
    document.getElementById("sidePanel").innerHTML = '<input id="replacement"><button disabled>Unavailable</button>';
    requestEvent("htmx:afterSwap", {xhr});
    expect(document.getElementById("replacement").disabled).toBe(true);
    completeMutation(xhr);
    expect(document.getElementById("replacement").disabled).toBe(false);
    expect(document.querySelector("button").disabled).toBe(true);
});

test.each([true, false])("exports have no native link destination until completion (successful=%s)", successful => {
    document.body.innerHTML = `
        <a id="model" data-workspace-control href="download-json/" target="_blank">Model</a>
        <a id="workspace" data-workspace-control href="download-workspace/">Workspace</a>
        <a id="empty" data-workspace-control href="">Empty</a>
        <a id="absent" data-workspace-control>Absent</a>
        <a id="documentation" href="/docs/">Read</a>
    `;
    loadModule();
    const destinations = () => Object.fromEntries(Array.from(document.querySelectorAll("a"),
        link => [link.id, link.getAttribute("href")]));
    const before = destinations();
    const xhr = startMutation();
    expect(destinations()).toEqual({model: null, workspace: null, empty: null, absent: null, documentation: "/docs/"});
    completeMutation(xhr, {successful, swap: successful});
    expect(destinations()).toEqual(before);
});

test.each(["HTTP error", "abort", "HTTP error modal"])("%s unlocks and reports an unsuccessful mutation", failure => {
    document.body.innerHTML = '<div id="sidePanel"><input value="unsaved"></div>';
    loadModule();
    const finished = jest.fn();
    document.body.addEventListener("workspace-mutation:finished", finished, {once: true});
    const xhr = startMutation();
    if (failure === "HTTP error modal") xhr.getResponseHeader.mockReturnValue('{"openModalDialog": {}}');
    completeMutation(xhr, {successful: false, swap: failure === "HTTP error modal"});
    expect(finished.mock.calls[0][0].detail.successful).toBe(false);
    expect(document.querySelector("input").disabled).toBe(false);
    expect(document.querySelector("input").value).toBe("unsaved");
});

test("stateless previews remain available and their completion cannot release the mutation lock", () => {
    loadModule();
    const xhr = startMutation();
    const preview = {xhr: {}, elt: document.body, requestConfig: {verb: "post", path: "/model_builder/timeseries-preview/"}};
    expect(requestEvent("htmx:confirm", {verb: "post", path: preview.requestConfig.path}).defaultPrevented).toBe(false);
    expect(requestEvent("htmx:beforeRequest", preview).defaultPrevented).toBe(false);
    requestEvent("htmx:afterRequest", preview);
    expect(document.body.dataset.workspaceMutation).toBe("updating");
    completeMutation(xhr);
    expect(document.body.dataset.workspaceMutation).toBeUndefined();
});

test("HTMX's global button disabling leaves reading controls available while constraint buttons stay disabled", () => {
    document.body.innerHTML = '<button id="read">Read</button><button id="unavailable" disabled>No</button><button hx-post="/save/">Save</button>';
    loadModule();
    const xhr = startMutation();
    document.querySelectorAll("button").forEach(button => button.disabled = true);
    requestEvent("htmx:beforeSend", {xhr});
    expect(document.getElementById("read").disabled).toBe(false);
    expect(document.getElementById("unavailable").disabled).toBe(true);
    document.querySelectorAll("button").forEach(button => button.disabled = false);
    completeMutation(xhr);
    expect(document.getElementById("unavailable").disabled).toBe(true);
});

test("a swap-processing error releases the workspace lock as a failed mutation", () => {
    document.body.innerHTML = '<div id="sidePanel"><input></div>';
    loadModule();
    const xhr = startMutation();
    requestEvent("htmx:beforeSwap", {xhr, shouldSwap: true});
    requestEvent("htmx:onLoadError", {xhr});
    expect(document.body.dataset.workspaceMutation).toBeUndefined();
    expect(document.querySelector("input").disabled).toBe(false);
});

test("an already-busy workspace rejects fetch mutations without queueing a later write", async () => {
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    const xhr = startMutation();
    global.Sortable.mock.instances[0].options.onEnd({from: global.Sortable.mock.instances[0].el});
    expect(global.fetch).not.toHaveBeenCalled();
    completeMutation(xhr);
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(global.fetch).not.toHaveBeenCalled();
});

test("a nested mutation distinguishes temporary HTMX disabling from constraint disabling", () => {
    document.body.innerHTML = '<button id="read">Read</button><button id="constraint" disabled>No</button><button hx-post="/save/">Save</button>';
    loadModule();
    const readXhr = {};
    requestEvent("htmx:beforeRequest", {xhr: readXhr, requestConfig: {verb: "get"}});
    document.querySelectorAll("button").forEach(button => {
        button.disabled = true;
        button.setAttribute("data-disabled-by-htmx", "");
    });
    const xhr = startMutation();
    requestEvent("htmx:beforeSend", {xhr});
    expect(document.getElementById("read").disabled).toBe(false);
    completeMutation(xhr);
    document.querySelectorAll("button").forEach(button => {
        button.disabled = false;
        button.removeAttribute("data-disabled-by-htmx");
    });
    requestEvent("htmx:afterRequest", {xhr: readXhr});
    expect(document.getElementById("read").disabled).toBe(false);
    expect(document.querySelector("[hx-post]").disabled).toBe(false);
    expect(document.getElementById("constraint").disabled).toBe(true);
});


test.each([422, 500])("HTTP %s modal processes OOB content and stays locked until settlement", status => {
    require("../theme/static/scripts/modal_utils.js");
    loadModule();
    const finished = jest.fn();
    document.body.addEventListener("workspace-mutation:finished", finished, {once: true});
    const xhr = startMutation();
    xhr.status = status;
    xhr.getResponseHeader.mockImplementation(name => name === "HX-Reswap" ? "none" : null);
    const event = requestEvent("htmx:beforeSwap", {xhr, shouldSwap: false, isError: true});
    expect(event.detail.shouldSwap).toBe(true);
    expect(event.detail.isError).toBe(true);
    expect(xhr.getResponseHeader("HX-Reswap")).toBe("none");
    requestEvent("htmx:afterRequest", {xhr, successful: false});
    expect(finished).not.toHaveBeenCalled();
    expect(document.body.dataset.workspaceMutation).toBe("updating");
    requestEvent("htmx:afterSettle", {xhr});
    expect(finished.mock.calls[0][0].detail.successful).toBe(false);
    expect(document.body.dataset.workspaceMutation).toBeUndefined();
});

test("a successful modal action is not mistaken for a failed save", () => {
    loadModule();
    const finished = jest.fn();
    document.body.addEventListener("workspace-mutation:finished", finished, {once: true});
    const xhr = startMutation();
    xhr.getResponseHeader.mockReturnValue('{"openModalDialog": {}}');
    completeMutation(xhr);
    expect(finished.mock.calls[0][0].detail.successful).toBe(true);
});
