const fs = require("fs");
const path = require("path");

window.tagFormAsModified = jest.fn();
window.hideLoadingBar = jest.fn();

require("../theme/static/scripts/timeseries_preview.js");
const {activateSelectedBuilder, initializeAll} = require("../theme/static/scripts/weekly_pattern_builder.js");

const FIXTURE = fs.readFileSync(path.join(__dirname, "fixtures", "weekly_pattern_default.html"), "utf8");

function selectWeeklyBuilder() {
    const selector = document.querySelector("[data-builder-selector]");
    selector.value = "weekly_pattern";
    selector.dispatchEvent(new Event("change", {bubbles: true}));
    return document.querySelector("[data-weekly-pattern-editor]");
}

function profiles(editor) {
    return [...editor.querySelectorAll("[data-weekly-profile]")];
}

beforeEach(() => {
    document.body.innerHTML = FIXTURE;
    delete window.htmx;
    window.tagFormAsModified.mockClear();
    window.hideLoadingBar.mockClear();
    initializeAll(document);
});

test("valid continuous edits debounce preview requests and keep only the latest revision", () => {
    jest.useFakeTimers();
    window.htmx = {ajax: jest.fn()};
    const editor = selectWeeklyBuilder();
    jest.runOnlyPendingTimers();
    expect(window.htmx.ajax).toHaveBeenCalledTimes(1);

    const baseline = editor.querySelector("[data-profile-baseline]");
    baseline.value = "4";
    baseline.dispatchEvent(new Event("input", {bubbles: true}));
    baseline.value = "6";
    baseline.dispatchEvent(new Event("input", {bubbles: true}));
    jest.advanceTimersByTime(299);
    expect(window.htmx.ajax).toHaveBeenCalledTimes(1);
    jest.advanceTimersByTime(1);

    expect(window.htmx.ajax).toHaveBeenCalledTimes(2);
    const requestConfig = window.htmx.ajax.mock.calls[1][2];
    const values = requestConfig.values;
    expect(JSON.parse(values.form_inputs).profiles[0].baseline).toBe(6);
    expect(requestConfig.source.closest("form")).toBeNull();
    expect(values.request_sequence).toBe(
        document.querySelector("[data-timeseries-preview]").dataset.latestRequestSequence
    );
    jest.useRealTimers();
});

test("component-driven unit changes refresh the active preview immediately", () => {
    jest.useFakeTimers();
    window.htmx = {ajax: jest.fn()};
    const editor = selectWeeklyBuilder();
    jest.runOnlyPendingTimers();
    const callsBeforeUnitChange = window.htmx.ajax.mock.calls.length;
    const unitInput = document.getElementById("RecurrentEdgeProcess_recurrent_compute_needed__constant_unit");

    unitInput.value = "GB_ram";
    unitInput.dispatchEvent(new CustomEvent("timeseries-unit:changed", {bubbles: true}));
    jest.runOnlyPendingTimers();

    expect(window.htmx.ajax).toHaveBeenCalledTimes(callsBeforeUnitChange + 1);
    const values = window.htmx.ajax.mock.calls.at(-1)[2].values;
    expect(JSON.parse(values.form_inputs).unit).toBe("GB_ram");
    expect([...editor.querySelectorAll("[data-weekly-unit]")].map((element) => element.textContent.trim()))
        .toEqual(["GB_ram", "GB_ram", "GB_ram"]);
    jest.useRealTimers();
});

test("replacement and HTMX cleanup abort active preview requests", () => {
    jest.useFakeTimers();
    const abortedSources = [];
    window.htmx = {ajax: jest.fn((_method, _url, config) => {
        config.source.addEventListener("htmx:abort", function () { abortedSources.push(config.source); });
        return new Promise(function () {});
    })};
    const editor = selectWeeklyBuilder();
    jest.runOnlyPendingTimers();
    const firstSource = window.htmx.ajax.mock.calls[0][2].source;

    const baseline = editor.querySelector("[data-profile-baseline]");
    baseline.value = "4";
    baseline.dispatchEvent(new Event("input", {bubbles: true}));
    expect(abortedSources).toEqual([firstSource]);
    jest.advanceTimersByTime(300);
    const secondSource = window.htmx.ajax.mock.calls[1][2].source;

    document.querySelector("[data-timeseries-builder]").dispatchEvent(new CustomEvent("htmx:beforeCleanupElement", {
        bubbles: true,
        detail: {elt: document.querySelector("[data-timeseries-builder]")},
    }));

    expect(abortedSources).toEqual([firstSource, secondSource]);
    jest.useRealTimers();
});

test("latest preview transport failures retain the chart and report local status", async () => {
    jest.useFakeTimers();
    window.htmx = {ajax: jest.fn(() => Promise.reject(new Error("network unavailable")))};
    const chart = {sentinel: true};
    document.querySelector("[data-timeseries-preview-canvas]")._timeseriesPreviewChart = chart;

    selectWeeklyBuilder();
    jest.runOnlyPendingTimers();
    await Promise.resolve();
    await Promise.resolve();

    expect(document.querySelector("[data-timeseries-preview-canvas]")._timeseriesPreviewChart).toBe(chart);
    expect(document.querySelector("[data-timeseries-preview-status]").textContent).toContain(
        "could not be refreshed"
    );
    jest.useRealTimers();
});

test("range bounds refresh on commit while discrete day actions refresh immediately", () => {
    jest.useFakeTimers();
    window.htmx = {ajax: jest.fn()};
    const editor = selectWeeklyBuilder();
    jest.runOnlyPendingTimers();
    const profile = profiles(editor)[0];
    profile.querySelector("[data-action='add-weekly-range']").click();
    jest.runOnlyPendingTimers();
    const callsAfterAdd = window.htmx.ajax.mock.calls.length;
    const start = profile.querySelector("[data-range-start]");

    start.value = "2";
    start.dispatchEvent(new Event("input", {bubbles: true}));
    jest.runOnlyPendingTimers();
    expect(window.htmx.ajax).toHaveBeenCalledTimes(callsAfterAdd);
    profile.querySelector("[data-range-end]").value = "3";
    start.dispatchEvent(new Event("change", {bubbles: true}));
    jest.runOnlyPendingTimers();
    expect(window.htmx.ajax).toHaveBeenCalledTimes(callsAfterAdd + 1);

    const weekendMonday = profiles(editor)[1].querySelector("[data-profile-day][value='0']");
    weekendMonday.checked = true;
    weekendMonday.dispatchEvent(new Event("change", {bubbles: true}));
    jest.runOnlyPendingTimers();
    expect(window.htmx.ajax).toHaveBeenCalledTimes(callsAfterAdd + 2);
    jest.useRealTimers();
});

test("client-invalid drafts suppress requests and retain the preview chart area", () => {
    jest.useFakeTimers();
    window.htmx = {ajax: jest.fn()};
    const editor = selectWeeklyBuilder();
    jest.runOnlyPendingTimers();
    const callsBeforeInvalidEdit = window.htmx.ajax.mock.calls.length;
    const monday = profiles(editor)[0].querySelector("[data-profile-day][value='0']");

    monday.checked = false;
    monday.dispatchEvent(new Event("change", {bubbles: true}));
    jest.runOnlyPendingTimers();

    expect(window.htmx.ajax).toHaveBeenCalledTimes(callsBeforeInvalidEdit);
    expect(document.querySelector("[data-timeseries-preview-status]").textContent).toContain("last valid chart");
    expect(document.querySelector("[data-timeseries-preview-status]").hidden).toBe(false);
    expect(document.querySelector("[data-timeseries-preview-canvas]")).not.toBeNull();
    jest.useRealTimers();
});

test("preview validation errors map to the visible weekly control", () => {
    const editor = selectWeeklyBuilder();
    const region = document.querySelector("[data-timeseries-preview]");

    region.dispatchEvent(new CustomEvent("timeseries-preview:response", {
        bubbles: true,
        detail: {
            success: false,
            errors: [{path: "profiles[0].baseline", message: "Server rejected this baseline."}],
        },
    }));

    expect(editor.querySelector("[data-profile-baseline]").validationMessage)
        .toBe("Server rejected this baseline.");
});

test("switching builders retains both drafts and submits only the active builder", () => {
    const constant = document.getElementById("RecurrentEdgeProcess_recurrent_compute_needed");
    constant.value = "7";
    const editor = selectWeeklyBuilder();
    const baseline = editor.querySelector("[data-profile-baseline]");
    baseline.value = "9";
    baseline.dispatchEvent(new Event("input", {bubbles: true}));

    expect(constant.disabled).toBe(true);
    expect(editor.querySelector("[data-weekly-pattern-payload]").disabled).toBe(false);

    const selector = document.querySelector("[data-builder-selector]");
    selector.value = "constant";
    selector.dispatchEvent(new Event("change", {bubbles: true}));

    expect(constant.disabled).toBe(false);
    expect(constant.value).toBe("7");
    expect(editor.querySelector("[data-profile-baseline]").value).toBe("9");
    expect(editor.querySelector("[data-weekly-pattern-payload]").disabled).toBe(true);
    expect(window.tagFormAsModified).toHaveBeenCalled();
});

test("only the most recently used weekly field exposes its external preview", () => {
    const form = document.getElementById("sidePanelForm");
    const firstRoot = form.querySelector("[data-timeseries-builder]");
    const secondRoot = firstRoot.cloneNode(true);
    secondRoot.removeAttribute("data-timeseries-builder-initialized");
    secondRoot.classList.remove("weekly-preview-active");
    form.appendChild(secondRoot);
    initializeAll(secondRoot);

    const firstSelector = firstRoot.querySelector("[data-builder-selector]");
    firstSelector.value = "weekly_pattern";
    firstSelector.dispatchEvent(new Event("change", {bubbles: true}));
    expect(firstRoot.querySelector("[data-timeseries-preview-column]").hidden).toBe(false);
    expect(secondRoot.querySelector("[data-timeseries-preview-column]").hidden).toBe(true);

    const secondSelector = secondRoot.querySelector("[data-builder-selector]");
    secondSelector.value = "weekly_pattern";
    secondSelector.dispatchEvent(new Event("change", {bubbles: true}));
    expect(firstRoot.querySelector("[data-timeseries-preview-column]").hidden).toBe(true);
    expect(secondRoot.querySelector("[data-timeseries-preview-column]").hidden).toBe(false);
});

test("reactivating a selected builder restores its named payload after transient disabling", () => {
    const editor = selectWeeklyBuilder();
    const payload = editor.querySelector("[data-weekly-pattern-payload]");
    payload.disabled = true;

    activateSelectedBuilder(document.querySelector("[data-timeseries-builder]"));

    expect(payload.disabled).toBe(false);
});

test("switching away from an invalid weekly draft removes it from form validation", () => {
    const editor = selectWeeklyBuilder();
    const monday = profiles(editor)[0].querySelector("[data-profile-day][value='0']");
    monday.checked = false;
    monday.dispatchEvent(new Event("change", {bubbles: true}));
    expect(document.getElementById("sidePanelForm").checkValidity()).toBe(false);

    const selector = document.querySelector("[data-builder-selector]");
    selector.value = "constant";
    selector.dispatchEvent(new Event("change", {bubbles: true}));

    expect(selector.validationMessage).toBe("");
    expect(document.getElementById("sidePanelForm").checkValidity()).toBe(true);
});

test("day assignment steals ownership from the previous profile", () => {
    const editor = selectWeeklyBuilder();
    const profileList = profiles(editor);
    const weekendMonday = profileList[1].querySelector("[data-profile-day][value='0']");
    weekendMonday.checked = true;
    weekendMonday.dispatchEvent(new Event("change", {bubbles: true}));

    expect(profileList[0].querySelector("[data-profile-day][value='0']").checked).toBe(false);
    expect(weekendMonday.checked).toBe(true);
    const payload = JSON.parse(editor.querySelector("[data-weekly-pattern-payload]").value);
    expect(payload.profiles[0].days).toEqual([1, 2, 3, 4]);
    expect(payload.profiles[1].days).toEqual([0, 5, 6]);
});

test("profile add and remove preserve unassigned days as an invalid draft", () => {
    const editor = selectWeeklyBuilder();
    editor.querySelector("[data-action='add-weekly-profile']").click();
    expect(profiles(editor)).toHaveLength(3);
    expect(profiles(editor)[2].querySelector("[data-profile-baseline]").value).toBe("0");

    const weekday = profiles(editor)[0];
    weekday.querySelector("[data-action='remove-weekly-profile']").click();

    expect(profiles(editor)).toHaveLength(2);
    expect(editor.querySelector("[data-weekly-error]").textContent).toContain("Mon must be assigned");
    expect(document.getElementById("sidePanelForm").checkValidity()).toBe(false);
});

test("removing an existing profile marks the form modified after detaching the control", () => {
    const editor = selectWeeklyBuilder();
    window.tagFormAsModified.mockClear();

    profiles(editor)[1].querySelector("[data-action='remove-weekly-profile']").click();

    expect(window.tagFormAsModified).toHaveBeenCalledTimes(1);
});

test("ranges use the first free hour, sort chronologically, and reject overlaps", () => {
    const editor = selectWeeklyBuilder();
    const profile = profiles(editor)[0];
    const add = profile.querySelector("[data-action='add-weekly-range']");
    add.click();
    add.click();
    const rows = [...profile.querySelectorAll("[data-weekly-range]")];
    expect(rows.map((row) => row.querySelector("[data-range-start]").value)).toEqual(["0", "1"]);

    rows[1].querySelector("[data-range-start]").value = "8";
    rows[1].querySelector("[data-range-end]").value = "10";
    rows[1].querySelector("[data-range-end]").dispatchEvent(new Event("change", {bubbles: true}));
    rows[0].querySelector("[data-range-start]").value = "9";
    rows[0].querySelector("[data-range-end]").value = "11";
    rows[0].querySelector("[data-range-end]").dispatchEvent(new Event("change", {bubbles: true}));

    expect(rows[0].querySelector("[data-range-error]").textContent).toContain("Overlaps");
    expect(document.getElementById("sidePanelForm").checkValidity()).toBe(false);
});

test("duplicate names and forbidden negative values block submission inline", () => {
    const editor = selectWeeklyBuilder();
    const profileList = profiles(editor);
    profileList[1].querySelector("[data-profile-name]").value = "weekday";
    profileList[1].querySelector("[data-profile-name]").dispatchEvent(new Event("input", {bubbles: true}));
    profileList[0].querySelector("[data-profile-baseline]").value = "-1";
    profileList[0].querySelector("[data-profile-baseline]").dispatchEvent(new Event("input", {bubbles: true}));

    expect(profileList[1].querySelector("[data-profile-name-error]").textContent).toContain("unique");
    expect(profileList[0].querySelector("[data-profile-baseline-error]").textContent).toContain("zero or greater");
    expect(document.getElementById("sidePanelForm").checkValidity()).toBe(false);
});

test("authoritative errors map normalized paths back to visible controls", () => {
    const editor = selectWeeklyBuilder();
    const response = {
        errors: [{
            path: "profiles[0].baseline",
            code: "negative_value_not_allowed",
            message: "Server says this baseline is invalid.",
        }],
    };
    editor.closest("[data-timeseries-builder]").querySelector("[data-timeseries-preview]")
        .dispatchEvent(new CustomEvent("timeseries-preview:response", {
        bubbles: true,
        detail: {...response, success: false},
    }));

    expect(editor.querySelector("[data-profile-baseline]").validationMessage)
        .toBe("Server says this baseline is invalid.");
});

test("authoritative day paths follow serialized selection order and fall back to the profile", () => {
    const editor = selectWeeklyBuilder();
    const preview = editor.closest("[data-timeseries-builder]").querySelector("[data-timeseries-preview]");
    const weekend = profiles(editor)[1];
    const saturday = weekend.querySelector("[data-profile-day][value='5']");

    preview.dispatchEvent(new CustomEvent("timeseries-preview:response", {
        bubbles: true,
        detail: {success: false, errors: [{path: "profiles[1].days[0]", message: "Duplicate Saturday."}]},
    }));
    expect(saturday.validationMessage).toBe("Duplicate Saturday.");

    preview.dispatchEvent(new CustomEvent("timeseries-preview:response", {
        bubbles: true,
        detail: {success: false, errors: [{path: "profiles[1].days[2]", message: "Injected day is invalid."}]},
    }));
    expect(weekend.querySelector("[data-profile-days-error]").textContent).toBe("Injected day is invalid.");
});

test("dynamic controls retain accessible labels and error descriptions", () => {
    const editor = selectWeeklyBuilder();
    editor.querySelector("[data-action='add-weekly-profile']").click();
    const profile = profiles(editor)[2];
    const name = profile.querySelector("[data-profile-name]");
    expect(profile.querySelector("[data-profile-name-label]").htmlFor).toBe(name.id);
    expect(document.getElementById(name.getAttribute("aria-describedby"))).not.toBeNull();

    profile.querySelector("[data-action='add-weekly-range']").click();
    const range = profile.querySelector("[data-weekly-range]");
    const start = range.querySelector("[data-range-start]");
    expect(document.getElementById(start.getAttribute("aria-describedby"))).toBe(
        range.querySelector("[data-range-error]")
    );
});
