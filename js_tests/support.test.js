const fs = require("fs");
const path = require("path");

const fixture = fs.readFileSync(path.join(__dirname, "fixtures", "support_panel_with_model.html"), "utf8");

function flushPromises() {
    return new Promise(resolve => setTimeout(resolve, 0));
}

beforeAll(() => {
    require("../theme/static/scripts/support.js");
});

beforeEach(() => {
    document.body.innerHTML = "";
    global.openSidePanel = jest.fn();
    global.htmx = {ajax: jest.fn()};
    global.runAfterSidePanelDiscardConfirmation = action => action();
});

afterEach(() => {
    delete global.openSidePanel;
    delete global.htmx;
    delete global.runAfterSidePanelDiscardConfirmation;
    delete global.hideEditIcons;
    delete global.closeCalculatedAttributesChart;
});

test("feedback uses ordinary navigation when the builder side panel is absent", () => {
    document.body.innerHTML = '<a href="#support" data-action="open-feedback">Feedback</a>';
    const event = new MouseEvent("click", {bubbles: true, cancelable: true});

    document.querySelector("a").dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
    expect(global.htmx.ajax).not.toHaveBeenCalled();
});

test("feedback loads through the real builder panel opener and moves focus to its heading", async () => {
    document.body.innerHTML = '<div id="panel-result-btn"></div>'
        + '<div id="btn-open-panel-result" class="w-100"></div>'
        + '<div id="sidePanel" class="d-none"></div>'
        + '<a href="/support/" data-panel-url="/model_builder/support/" data-action="open-feedback">Feedback</a>';
    const sidePanel = document.getElementById("sidePanel");
    sidePanel.scrollTo = jest.fn();
    global.hideEditIcons = jest.fn();
    global.closeCalculatedAttributesChart = jest.fn();
    global.openSidePanel = require("../theme/static/scripts/side_panel_utils.js").openSidePanel;
    global.htmx.ajax.mockImplementation(() => {
        sidePanel.innerHTML = fixture;
        return Promise.resolve();
    });
    const event = new MouseEvent("click", {bubbles: true, cancelable: true});

    document.querySelector("a[data-action]").dispatchEvent(event);
    await flushPromises();

    expect(event.defaultPrevented).toBe(true);
    expect(global.htmx.ajax).toHaveBeenCalledWith("GET", "/model_builder/support/", expect.objectContaining({
        target: "#sidePanel", swap: "innerHTML",
    }));
    expect(sidePanel.classList.contains("d-none")).toBe(false);
    expect(sidePanel.scrollTo).toHaveBeenCalledWith({top: 0, behavior: "smooth"});
    expect(document.activeElement.id).toBe("sidePanelTitle");
});

test("feedback waits for confirmation before replacing a modified side panel", () => {
    document.body.innerHTML = '<div id="sidePanel"></div>'
        + '<a href="/support/" data-panel-url="/model_builder/support/" data-action="open-feedback">Feedback</a>';
    let confirmedAction;
    global.runAfterSidePanelDiscardConfirmation = jest.fn(action => { confirmedAction = action; });
    const event = new MouseEvent("click", {bubbles: true, cancelable: true});

    document.querySelector("a").dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(global.runAfterSidePanelDiscardConfirmation).toHaveBeenCalledTimes(1);
    expect(global.htmx.ajax).not.toHaveBeenCalled();

    confirmedAction();
    expect(global.htmx.ajax).toHaveBeenCalledTimes(1);
});

test("failed panel loading retries the standalone URL as ordinary navigation", async () => {
    document.body.innerHTML = '<div id="sidePanel"></div>'
        + '<a href="/support/" data-panel-url="/model_builder/support/" data-action="open-feedback">Feedback</a>';
    global.htmx.ajax.mockRejectedValue(new Error("network unavailable"));
    const retry = jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    document.querySelector("a").dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}));
    await flushPromises();

    expect(retry).toHaveBeenCalledTimes(1);
    retry.mockRestore();
});

test("the kind selector updates GitHub and email destinations without collecting report text", () => {
    document.body.innerHTML = fixture;
    const selector = document.getElementById("feedback-kind");
    selector.value = "feedback";

    selector.dispatchEvent(new Event("change", {bubbles: true}));

    expect(document.querySelector('[data-feedback-destination="github"]').href).toContain("title=feedback");
    expect(document.querySelector('[data-feedback-destination="email"]').href).toContain("subject=feedback");
    expect(document.querySelector("textarea")).toBeNull();
    expect(document.querySelector('input[type="checkbox"]')).toBeNull();
});

test("download and external handoffs remain separate keyboard-operable links", () => {
    document.body.innerHTML = fixture;
    const download = document.querySelector("[data-feedback-download]");
    const github = document.querySelector('[data-feedback-destination="github"]');

    expect(download.tagName).toBe("A");
    expect(download.href).toContain("/model_builder/download-json/");
    expect(download.href).not.toBe(github.href);
    expect(github.target).toBe("_blank");
    expect(github.rel).toContain("noopener");
    expect(github.rel).toContain("noreferrer");
});
