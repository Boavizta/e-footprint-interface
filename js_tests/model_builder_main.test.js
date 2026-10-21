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

test("closing Results while its requests are pending empties the panel at once", () => {
    document.body.innerHTML = `
        <div id="toolbar-nav"></div><div id="model-canva-scrollable-area" class="overflow-x-auto"></div>
        <div id="sidePanel" class="d-none"></div>
        <div id="panel-result-btn"></div><button id="btn-open-panel-result"></button>
        <div id="result-block"><form class="sankey-settings htmx-request"></form></div>
    `;
    window.eval(fs.readFileSync(path.join(__dirname, "../theme/static/scripts/hammer_utils.js"), "utf8"));
    window.displayPanelResult();
    window.hidePanelResult();
    const results = document.getElementById("result-block");
    expect(results.innerHTML).toBe("");
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

// bug-fixes-2026-10 Task 12
test.failing("pulse and opened highlights cover every card of the object on its own canvas only", () => {
    document.body.innerHTML = fs.readFileSync(path.join(__dirname, "fixtures", "card_highlight_two_canvases.html"), "utf8");
    loadModule();
    jest.useFakeTimers();
    global.bootstrap = {Toast: {getOrCreateInstance: jest.fn(() => ({show: jest.fn()}))}};
    const cases = JSON.parse(document.getElementById("expected-highlight-ids").textContent);
    const highlighted = className => {
        const elements = Array.from(document.getElementsByClassName(className));
        elements.forEach(element => element.classList.remove(className));
        return elements.map(element => element.id).sort();
    };
    const expected = {};
    const received = {};

    for (const [label, {canonical, buttons, parked_buttons}] of Object.entries(cases)) {
        document.body.dispatchEvent(new CustomEvent("displayToastAndHighlightObjects", {detail: {
            action_type: "edit_object", name: label, id: canonical}}));
        const pulsed = highlighted("border-pulse-after-add-edit-object");
        document.body.dispatchEvent(new CustomEvent("highlightOpenedObjects", {detail: {value: canonical}}));
        // The parked canvas holds the same object ids, so its cards must exist and stay unmarked.
        expected[label] = {pulsed: [...buttons].sort(), opened: [...buttons].sort(), parked: parked_buttons};
        received[label] = {pulsed, opened: highlighted("model-builder-card-opened"),
            parked: parked_buttons.filter(id => document.getElementById(id))};
    }

    jest.clearAllTimers();
    jest.useRealTimers();
    delete global.bootstrap;

    expect(received).toEqual(expected);
});
