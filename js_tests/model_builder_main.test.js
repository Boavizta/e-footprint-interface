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
    const grabbed = document.querySelector("#server-list > div");
    grabbed.classList.add("grabbing");

    global.Sortable.mock.instances[0].options.onEnd({from: global.Sortable.mock.instances[0].el});
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

test("model replacement keeps its ordinary destructive confirmation", () => {
    document.body.innerHTML = `
        <div class="model-builder-card">Current modeling</div>
        <button data-confirm-when-model-not-empty="Start blank?">Start blank</button>
    `;
    loadModule();
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);
    const issueRequest = jest.fn();
    const event = new CustomEvent("htmx:confirm", {bubbles: true, cancelable: true, detail: {issueRequest}});

    document.querySelector("button").dispatchEvent(event);

    expect(confirm).toHaveBeenCalledWith("Start blank?");
    expect(issueRequest).toHaveBeenCalledWith(true);
    confirm.mockRestore();
});

function requestEvent(type, detail, target = document.body) {
    const event = new CustomEvent(type, {bubbles: true, cancelable: true, detail});
    target.dispatchEvent(event);
    return event;
}

test.each([true, false])("OOB replacements preserve the accordion transition destination (open=%s)", open => {
    loadModule();
    const card = document.getElementById("uj-first");
    const collapse = card.querySelector(".accordion-collapse");
    const toggle = card.querySelector("[data-bs-toggle='collapse']");
    const responseCard = card.cloneNode(true);
    responseCard.setAttribute("hx-swap-oob", "outerHTML");
    collapse.classList.remove("show", "collapse");
    collapse.classList.add("collapsing");
    toggle.setAttribute("aria-expanded", String(open));

    const detail = {xhr: {status: 200}, serverResponse: "<div hx-swap-oob='true'>" + responseCard.outerHTML + "</div>"};
    requestEvent("htmx:beforeSwap", detail);
    const fragment = new DOMParser().parseFromString(detail.serverResponse, "text/html");
    const replacement = fragment.getElementById(card.id);

    expect(replacement.querySelector(".accordion-collapse").classList.contains("show")).toBe(open);
    expect(replacement.querySelector("[data-bs-toggle='collapse']").getAttribute("aria-expanded")).toBe(String(open));
    expect(replacement.querySelector("[id^='icon_accordion_']").classList.contains("chevron-rotate")).toBe(open);
});

test("native disabling restores prerequisite controls in both resident workspaces and leaves replacements alone", () => {
    document.body.innerHTML = `
        <button id="unavailable" disabled>Unavailable</button>
        <div data-simplified-workspace><input disabled><select disabled></select></div>
        <div data-simplified-workspace hidden><textarea disabled></textarea></div>
        <input id="outside" disabled>
    `;
    loadModule();
    const xhr = {};
    requestEvent("htmx:beforeRequest", {xhr});
    document.querySelectorAll("[disabled]").forEach(element => element.disabled = false);
    const replaced = document.querySelector("select");
    replaced.outerHTML = "<select></select>";
    requestEvent("htmx:afterRequest", {xhr});
    expect(document.querySelector("button").disabled).toBe(true);
    expect(document.querySelector("[data-simplified-workspace] input").disabled).toBe(true);
    expect(document.querySelector("textarea").disabled).toBe(true);
    expect(document.querySelector("select").disabled).toBe(false);
    expect(document.querySelector("#outside").disabled).toBe(false);
});

test("overlapping HTMX requests distinguish temporary disabling from prerequisites", () => {
    document.body.innerHTML = '<button id="read">Read</button><button id="constraint" disabled>No</button>';
    loadModule();
    const first = {};
    const second = {};
    requestEvent("htmx:beforeRequest", {xhr: first});
    document.querySelectorAll("button").forEach(button => {
        button.disabled = true;
        button.setAttribute("data-disabled-by-htmx", "");
    });
    requestEvent("htmx:beforeRequest", {xhr: second});
    requestEvent("htmx:afterRequest", {xhr: first});
    document.querySelectorAll("button").forEach(button => {
        button.disabled = false;
        button.removeAttribute("data-disabled-by-htmx");
    });
    requestEvent("htmx:afterRequest", {xhr: second});
    expect(document.getElementById("read").disabled).toBe(false);
    expect(document.getElementById("constraint").disabled).toBe(true);
});

test("card ordering keeps its own fetch while an unrelated request is pending", () => {
    const {initSortableObjectCards} = loadModule();
    initSortableObjectCards();
    requestEvent("htmx:beforeRequest", {xhr: {}});
    global.Sortable.mock.instances[0].options.onEnd({from: global.Sortable.mock.instances[0].el});
    expect(global.fetch).toHaveBeenCalledTimes(1);
});

test.each([422, 500])("HTTP %s modal still processes rejected OOB content", status => {
    loadModule();
    const xhr = {status, getResponseHeader: name => name === "HX-Reswap" ? "none" : null};
    const event = requestEvent("htmx:beforeSwap", {xhr, shouldSwap: false, isError: true});
    expect(event.detail.shouldSwap).toBe(true);
    expect(event.detail.isError).toBe(true);
});

test("closing Results waits for its pending response and swap before detaching targets", () => {
    document.body.innerHTML = `
        <div id="toolbar-nav"></div><div id="model-canva-scrollable-area" class="overflow-x-auto"></div>
        <div id="sidePanel" class="d-none"></div>
        <div id="panel-result-btn"></div><button id="btn-open-panel-result"></button>
        <div id="result-block"><form class="sankey-settings htmx-request"></form></div>
    `;
    window.eval(fs.readFileSync(path.join(__dirname, "../theme/static/scripts/hammer_utils.js"), "utf8"));
    const results = document.getElementById("result-block");
    const form = results.querySelector("form");
    window.hidePanelResult();
    expect(results.style.display).toBe("none");
    expect(form.isConnected).toBe(true);
    form.classList.remove("htmx-request");
    results.classList.add("htmx-settling");
    requestEvent("htmx:afterRequest", {xhr: {}}, form);
    expect(form.isConnected).toBe(true);
    window.displayPanelResult();
    document.getElementById("btn-open-panel-result").outerHTML = '<button id="btn-open-panel-result" style="display:none"></button>';
    results.classList.remove("htmx-settling");
    requestEvent("htmx:afterSettle", {xhr: {}}, results);
    expect(results.innerHTML).toBe("");
    expect(results.style.display).toBe("");
    expect(results.style.height).toBe("");
    expect(document.getElementById("panel-result-btn").style.height).toBe("");
    expect(document.getElementById("btn-open-panel-result").style.display).toBe("block");
    expect(document.getElementById("toolbar-nav").style.display).toBe("");
    expect(document.getElementById("model-canva-scrollable-area").className).toBe("overflow-x-auto");
});

test("edit toast renders every repair notice and authored name as text", () => {
    loadModule();
    const toastTemplate = path.join(__dirname, "../model_builder/templates/model_builder/components/toast.html");
    document.body.insertAdjacentHTML("beforeend", fs.readFileSync(toastTemplate, "utf8"));
    document.getElementById("input-repair-notices").outerHTML = fs.readFileSync(
        path.join(__dirname, "fixtures", "input_repair_notices.html"), "utf8");
    const show = jest.fn();
    global.bootstrap = {Toast: {getOrCreateInstance: jest.fn(() => ({show}))}};
    document.body.dispatchEvent(new CustomEvent("displayToastAndHighlightObjects", {detail: {
        action_type: "edit_object", name: '<img src=x onerror="bad()">',
        constraint_messages: ["Existing constraint notice"],
        notice_target: "input-repair-notices"
    }}));
    const body = document.getElementById("toast-content");
    expect(body.textContent).toBe('<img src=x onerror="bad()"> has been updated! — Existing constraint notice — Job A: Resolution changed to 480p. — Job B: <script>unsafe()</script> & resolution changed to 480p.');
    expect(body.children).toHaveLength(0);
    expect(document.getElementById("input-repair-notices").children).toHaveLength(0);
    expect(show).toHaveBeenCalled();
    document.body.dispatchEvent(new CustomEvent("displayToastAndHighlightObjects", {detail: {
        action_type: "add_new_object", name: "Another object"
    }}));
    expect(body.textContent).toBe("Another object has been saved!");
    delete global.bootstrap;
});
