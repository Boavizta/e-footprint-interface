// initDynamicForm wires conditional select cascades. This exercises the single-hop path:
// changing the parent repopulates the child select and clears an invalid selection. (The three-level
// chain propagation was removed in the ecologits-video-generation cleanup — no
// single form ever holds a three-level chain.)

require("../theme/static/scripts/dynamic_forms.js");
const {initializeAll} = require("../theme/static/scripts/weekly_pattern_builder.js");

const fs = require("fs");
const path = require("path");

const FIXTURES = path.join(__dirname, "fixtures");

function mount(name) {
    document.body.innerHTML = fs.readFileSync(path.join(FIXTURES, `${name}.html`), "utf8");
}

function setupDom(dynamicFormData) {
    mount("conditional_select_catalog");
    document.body.insertAdjacentHTML(
        "beforeend",
        '<script id="dynamic-form-data" type="application/json"></script>',
    );
    document.getElementById("dynamic-form-data").textContent = JSON.stringify(dynamicFormData);
    document.dispatchEvent(new Event("initDynamicForm"));
}

function optionValues(id) {
    return Array.from(document.getElementById(id).options).map((opt) => opt.value);
}

test("conditional select restores its default and clears it when the parent makes it stale", () => {
    setupDom({
        dynamic_lists: [
            {
                input_id: "Cls_model_name",
                filter_by: "Cls_provider",
                list_value: {
                    openai: ["sora-2", "sora-2-pro"],
                    google: ["veo-3"],
                },
            },
        ],
    });

    // Initial fill from the starting provider value.
    expect(optionValues("Cls_model_name")).toEqual(["sora-2", "sora-2-pro"]);
    expect(document.getElementById("Cls_model_name").value).toBe("sora-2-pro");

    // Flip provider; the select listener replaces the options and clears the invalid selection.
    const provider = document.getElementById("Cls_provider");
    provider.value = "google";
    provider.dispatchEvent(new Event("change", { bubbles: true }));

    expect(optionValues("Cls_model_name")).toEqual(["veo-3"]);
    expect(document.getElementById("Cls_model_name").value).toBe("");
    expect(document.getElementById("Cls_model_name").selectedIndex).toBe(-1);
});

test("selection attribution appears only for the attributed option", () => {
    mount("select_object_with_attribution");
    document.body.insertAdjacentHTML(
        "beforeend",
        '<script id="dynamic-form-data" type="application/json">{}</script>',
    );
    document.dispatchEvent(new Event("initDynamicForm"));

    const select = document.getElementById("type_object_available");
    const attribution = document.getElementById("type_object_available-attribution");
    expect(attribution.classList).toContain("d-none");
    expect(attribution.textContent).toBe("");

    select.value = "VideoAPI";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(attribution.classList).not.toContain("d-none");
    expect(attribution.textContent).toContain("Research performed by Sasha Luccioni");

    select.value = "StandardAPI";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(attribution.classList).toContain("d-none");
    expect(attribution.textContent).toBe("");
});

test("object-type switching preserves control state owned by a nested timeseries builder", () => {
    const builder = fs.readFileSync(path.join(FIXTURES, "weekly_pattern_default.html"), "utf8");
    document.body.innerHTML = `
        <select id="type_object_available">
            <option value="recurrent" selected>Recurrent</option>
            <option value="other">Other</option>
        </select>
        <div id="item-recurrent">${builder}</div>
        <div id="item-other"><input name="other_name" required></div>
        <script id="dynamic-form-data" type="application/json"></script>
    `;
    document.getElementById("dynamic-form-data").textContent = JSON.stringify({
        switch_item: "type_object_available",
        switch_values: ["recurrent", "other"],
    });
    initializeAll(document);

    const recurrentSection = document.getElementById("item-recurrent");
    const namedControlStates = () => Array.from(recurrentSection.querySelectorAll("[name]"), function (control) {
        return {name: control.name, disabled: control.disabled, required: control.required};
    });
    const expectedStates = [
        {
            name: "RecurrentEdgeProcess_recurrent_compute_needed__constant_value",
            disabled: false,
            required: true,
        },
        {
            name: "RecurrentEdgeProcess_recurrent_compute_needed__constant_unit",
            disabled: false,
            required: false,
        },
        {
            name: "RecurrentEdgeProcess_recurrent_compute_needed__weekly_pattern",
            disabled: true,
            required: false,
        },
    ];

    document.dispatchEvent(new Event("initDynamicForm"));
    expect(namedControlStates()).toEqual(expectedStates);

    const typeSelector = document.getElementById("type_object_available");
    typeSelector.value = "other";
    typeSelector.dispatchEvent(new Event("change", {bubbles: true}));
    typeSelector.value = "recurrent";
    typeSelector.dispatchEvent(new Event("change", {bubbles: true}));

    expect(namedControlStates()).toEqual(expectedStates);
});
