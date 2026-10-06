// initDynamicForm wires conditional select cascades. This exercises the single-hop path:
// changing the parent repopulates the child select and clears an invalid selection. (The three-level
// chain propagation was removed in the ecologits-video-generation cleanup — no
// single form ever holds a three-level chain.)

require("../theme/static/scripts/dynamic_forms.js");
require("../theme/static/scripts/optional_quantity.js");
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

test.each(["autoscaling", "serverless"])("optional count clears when controller requires empty: %s", forcedValue => {
    mount("optional_quantity_fixed");
    document.body.insertAdjacentHTML("beforeend", '<script id="dynamic-form-data" type="application/json"></script>');
    document.getElementById("dynamic-form-data").textContent = "{}";
    document.dispatchEvent(new Event("initDynamicForm"));

    const type = document.getElementById("Server_server_type");
    const count = document.getElementById("Server_fixed_nb_of_instances");
    const group = document.querySelector("[data-optional-quantity-value]");
    const toggle = document.querySelector('[data-action="optional-quantity-empty"]');
    expect(count.value).toBe("3");
    expect(count.required).toBe(true);
    expect(group.classList.contains("d-none")).toBe(false);
    const changed = jest.fn();
    group.parentElement.addEventListener("optional-quantity:changed", changed);
    toggle.checked = true;
    toggle.dispatchEvent(new Event("change", {bubbles: true}));
    expect(changed.mock.calls[0][0].detail).toEqual({empty: true});
    expect(count.value).toBe("");
    expect(count.required).toBe(false);
    expect(group.classList.contains("d-none")).toBe(true);
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change", {bubbles: true}));
    expect(changed.mock.calls[1][0].detail).toEqual({empty: false});
    expect(document.activeElement).toBe(count);
    count.value = "4";
    type.value = forcedValue;
    type.dispatchEvent(new Event("change"));
    expect(count.value).toBe("");
    expect(toggle.checked).toBe(true);
    expect(toggle.disabled).toBe(true);
    expect(group.classList.contains("d-none")).toBe(true);
    type.value = "on-premise";
    type.dispatchEvent(new Event("change"));
    expect(toggle.disabled).toBe(false);
    expect(group.classList.contains("d-none")).toBe(true);
    expect(count.value).toBe("");
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


test("simplified optional quantity saves empty immediately and waits for numeric completion", () => {
    require("../theme/static/scripts/simplified_inputs.js");
    mount("simplified_optional_quantity");
    document.body.insertAdjacentHTML("beforeend", '<script id="dynamic-form-data" type="application/json">{}</script>');
    window.htmx = {trigger: jest.fn()};
    delete document.body.dataset.workspaceMutation;
    document.dispatchEvent(new Event("initDynamicForm"));
    document.dispatchEvent(new Event("DOMContentLoaded"));
    const form = document.querySelector("[data-simplified-editor]");
    const toggle = form.querySelector('[data-action="optional-quantity-empty"]');
    expect(toggle.disabled).toBe(false);
    expect(form.querySelector('input[type="number"]').value).toBe("5");
    toggle.checked = true;
    toggle.dispatchEvent(new Event("change", {bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledWith(form, "simplified-save");
    expect(form.querySelector('input[type="number"]').value).toBe("");
    form.dataset.saving = "false";
    window.htmx.trigger.mockClear();
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change", {bubbles: true}));
    expect(window.htmx.trigger).not.toHaveBeenCalled();
    const number = form.querySelector('input[type="number"]');
    number.value = "7";
    number.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
    expect(window.htmx.trigger).toHaveBeenCalledWith(form, "simplified-save");
});
