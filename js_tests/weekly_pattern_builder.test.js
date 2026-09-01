const fs = require("fs");
const path = require("path");

window.tagFormAsModified = jest.fn();
window.hideLoadingBar = jest.fn();

const {initializeAll} = require("../theme/static/scripts/weekly_pattern_builder.js");

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
    window.tagFormAsModified.mockClear();
    window.hideLoadingBar.mockClear();
    initializeAll(document);
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
    const form = document.getElementById("sidePanelForm");
    const response = {
        errors: [{
            path: "profiles[0].baseline",
            code: "negative_value_not_allowed",
            message: "Server says this baseline is invalid.",
        }],
    };
    form.dispatchEvent(new CustomEvent("htmx:afterRequest", {
        bubbles: true,
        detail: {xhr: {status: 422, responseText: JSON.stringify(response)}, elt: form},
    }));

    expect(editor.querySelector("[data-profile-baseline]").validationMessage)
        .toBe("Server says this baseline is invalid.");
    expect(window.hideLoadingBar).toHaveBeenCalled();
});
