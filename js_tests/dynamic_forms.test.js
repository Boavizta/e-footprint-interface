// initDynamicForm wires datalist cascades. This exercises the single-hop path that
// still ships (parent select -> child datalist): changing the parent repopulates the
// child datalist from the parent's value and clears the child input. (The three-level
// chain propagation was removed in the ecologits-video-generation cleanup — no
// single form ever holds a three-level chain.)

require("../theme/static/scripts/dynamic_forms.js");

const fs = require("fs");
const path = require("path");

const FIXTURES = path.join(__dirname, "fixtures");

function mount(name) {
    document.body.innerHTML = fs.readFileSync(path.join(FIXTURES, `${name}.html`), "utf8");
}

function setupDom(dynamicFormData) {
    document.body.innerHTML = `
        <input id="Cls_provider" name="Cls_provider" value="openai">
        <input id="Cls_model_name" name="Cls_model_name" list="datalist_Cls_model_name" value="sora-2-pro">
        <datalist id="datalist_Cls_model_name"></datalist>
        <script id="dynamic-form-data" type="application/json"></script>
    `;
    document.getElementById("dynamic-form-data").textContent = JSON.stringify(dynamicFormData);
    document.dispatchEvent(new Event("initDynamicForm"));
}

function datalistValues(id) {
    return Array.from(document.getElementById(id).options).map((opt) => opt.value);
}

test("changing the parent filter repopulates the child datalist and clears its input", () => {
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
    expect(datalistValues("datalist_Cls_model_name")).toEqual(["sora-2", "sora-2-pro"]);

    // Flip provider; the datalist listener refills from the new value and clears the input.
    const provider = document.getElementById("Cls_provider");
    provider.value = "google";
    provider.dispatchEvent(new Event("change", { bubbles: true }));

    expect(datalistValues("datalist_Cls_model_name")).toEqual(["veo-3"]);
    expect(document.getElementById("Cls_model_name").value).toBe("");
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
