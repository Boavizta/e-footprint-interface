const fs = require("fs");
const path = require("path");

const {
    applyConfidenceToBadge,
    toggleConfidenceMenu,
    setConfidence,
    openSourceEditor,
    cancelSourceEditor,
    applySourceEditor,
    handleSourceSelect,
    checkCollision,
    resetConfidenceForField,
    swapHypothesisToUserDataForField,
    autosaveConfidence,
    initInFormSourceEditorsIn,
} = require("../theme/static/scripts/source_metadata.js");

const FIXTURES_DIR = path.join(__dirname, "fixtures");

function loadFixture(name) {
    const file = path.join(FIXTURES_DIR, `${name}.html`);
    if (!fs.existsSync(file)) {
        throw new Error(
            `Fixture "${name}" not found at ${file}. Run \`poetry run python js_tests/build_fixtures.py\` (or \`npm run jest\` which chains it).`
        );
    }
    return fs.readFileSync(file, "utf8");
}

function mount(name) {
    document.body.innerHTML = `<form>${loadFixture(name)}</form>`;
}

// Row-editor fixtures already include their own <form>; the HTML parser silently drops a nested
// <form>, so we mount them straight into a stand-in for the .collapse wrapper that hosts them
// in production.
function mountRowEditor(name) {
    document.body.innerHTML = `<div class="collapse show" id="row-editor-row1">${loadFixture(name)}</div>`;
}

global.tagFormAsModified = jest.fn();

if (!global.crypto) global.crypto = {};
global.crypto.randomUUID = () => "abcdef-0000-0000-0000-000000000000";

if (typeof global.CSS === "undefined") {
    global.CSS = { escape: s => String(s).replace(/[^a-zA-Z0-9_-]/g, c => "\\" + c) };
}

beforeEach(() => {
    document.body.innerHTML = "";
    global.tagFormAsModified.mockClear();
});

test("applyConfidenceToBadge swaps the conf-* and bars-* classes", () => {
    mount("field_empty");
    const badge = document.querySelector(".confidence-badge");

    applyConfidenceToBadge(badge, "high");

    expect(badge.classList.contains("conf-high")).toBe(true);
    expect(badge.classList.contains("conf-none")).toBe(false);
    expect(badge.dataset.level).toBe("high");
    expect(badge.querySelector(".bars").classList.contains("bars-high")).toBe(true);
});

test("setConfidence updates badge state, hidden input and tags the form modified", () => {
    mount("field_empty");
    const highItem = document.querySelector('[data-level="high"][data-action="set-confidence"]');

    setConfidence(highItem, "high");

    expect(document.getElementById("Compute_cpu_cores__confidence").value).toBe("high");
    expect(highItem.classList.contains("selected")).toBe(true);
    expect(global.tagFormAsModified).toHaveBeenCalled();
});

test("setConfidence to 'none' clears the hidden input", () => {
    mount("field_high_no_source");
    const noneItem = document.querySelector('[data-level="none"][data-action="set-confidence"]');

    setConfidence(noneItem, "none");

    expect(document.getElementById("Compute_cpu_cores__confidence").value).toBe("");
});

test("resetConfidenceForField switches a high badge to none and clears the input", () => {
    mount("field_high_no_source");

    resetConfidenceForField("Compute_cpu_cores");

    const badge = document.querySelector(".confidence-badge");
    expect(badge.dataset.level).toBe("none");
    expect(badge.classList.contains("confidence-just-reset")).toBe(true);
    expect(document.getElementById("Compute_cpu_cores__confidence").value).toBe("");
});

test("resetConfidenceForField is a no-op when the badge is already none", () => {
    mount("field_empty");
    const badge = document.querySelector(".confidence-badge");

    resetConfidenceForField("Compute_cpu_cores");

    expect(badge.classList.contains("confidence-just-reset")).toBe(false);
});

test("applySourceEditor with a listed source writes its id/name/link and the comment to hidden inputs", () => {
    mount("field_src_listed");
    const editor = document.getElementById("editor-Compute_cpu_cores");
    editor.querySelector(".source-editor-select").value = "src1";
    editor.querySelector(".source-editor-comment").value = "vetted";

    applySourceEditor("Compute_cpu_cores");

    expect(document.getElementById("Compute_cpu_cores__source_id").value).toBe("src1");
    expect(document.getElementById("Compute_cpu_cores__source_name").value).toBe("ADEME 2024");
    expect(document.getElementById("Compute_cpu_cores__source_link").value).toBe("https://ademe.fr");
    expect(document.getElementById("Compute_cpu_cores__comment").value).toBe("vetted");
    expect(editor.classList.contains("open")).toBe(false);
});

test("applySourceEditor with a custom name mints a fresh id, broadcasts to siblings, and dedup-keys by id", () => {
    mount("two_empty_fields");
    // Form A: pick custom and set name
    const editorA = document.getElementById("editor-FieldA");
    editorA.querySelector(".source-editor-select").value = "__custom__";
    editorA.querySelector(".source-editor-custom-name").value = "My benchmark";
    editorA.querySelector(".source-editor-custom-link").value = "https://example.com";

    applySourceEditor("FieldA");

    const newId = document.getElementById("FieldA__source_id").value;
    expect(newId).toMatch(/^[0-9a-f]{6}$/); // 6-char hex slice from randomUUID

    // Sibling B's <select> now has the new option as a non-selected entry, before __custom__
    const selectB = document.getElementById("editor-FieldB").querySelector(".source-editor-select");
    const optionValues = Array.from(selectB.options).map(o => o.value);
    const customIdx = optionValues.indexOf("__custom__");
    const newIdIdx = optionValues.indexOf(newId);
    expect(newIdIdx).toBeGreaterThanOrEqual(0);
    expect(newIdIdx).toBeLessThan(customIdx);
    const newOpt = selectB.options[newIdIdx];
    expect(newOpt.dataset.name).toBe("My benchmark");
    expect(newOpt.dataset.link).toBe("https://example.com");

    // A's own select is untouched (broadcast skips the originator).
    const selectA = editorA.querySelector(".source-editor-select");
    expect(Array.from(selectA.options).map(o => o.value)).not.toContain(newId);
});

test("openSourceEditor populates the form from hidden inputs", () => {
    mount("field_src_selected_with_comment");
    const expectedComment = document.getElementById("Compute_cpu_cores__comment").value;

    openSourceEditor("Compute_cpu_cores");

    const editor = document.getElementById("editor-Compute_cpu_cores");
    expect(editor.classList.contains("open")).toBe(true);
    expect(editor.querySelector(".source-editor-select").value).toBe("src1");
    expect(editor.querySelector(".source-editor-comment").value).toBe(expectedComment);
});

test("openSourceEditor with a non-listed source falls into the custom branch", () => {
    mount("field_unlisted_source");

    openSourceEditor("Compute_cpu_cores");

    const editor = document.getElementById("editor-Compute_cpu_cores");
    expect(editor.querySelector(".source-editor-select").value).toBe("__custom__");
    expect(document.getElementById("custom-fields-Compute_cpu_cores").classList.contains("open")).toBe(true);
    expect(editor.querySelector(".source-editor-custom-name").value).toBe("Internal");
});

test("cancelSourceEditor restores from hidden inputs and does not leak typed text", () => {
    mount("field_src_selected_with_comment");
    const original = document.getElementById("Compute_cpu_cores__comment").value;
    const editor = document.getElementById("editor-Compute_cpu_cores");
    editor.querySelector(".source-editor-comment").value = "Tampered";

    cancelSourceEditor("Compute_cpu_cores");

    expect(editor.classList.contains("open")).toBe(false);
    expect(editor.querySelector(".source-editor-comment").value).toBe(original);
    expect(document.getElementById("Compute_cpu_cores__comment").value).toBe(original);
});

test("handleSourceSelect opens the custom-fields panel only when __custom__ is picked", () => {
    mount("field_src_listed");
    const select = document.querySelector(".source-editor-select");
    const customFields = document.getElementById("custom-fields-Compute_cpu_cores");

    select.value = "__custom__";
    handleSourceSelect(select, "Compute_cpu_cores");
    expect(customFields.classList.contains("open")).toBe(true);

    select.value = "src1";
    handleSourceSelect(select, "Compute_cpu_cores");
    expect(customFields.classList.contains("open")).toBe(false);
});

test("swapHypothesisToUserDataForField swaps when source was the hypothesis sentinel", () => {
    mount("field_hypothesis_with_comment");

    swapHypothesisToUserDataForField("Compute_cpu_cores");

    expect(document.getElementById("Compute_cpu_cores__source_id").value).toBe("user_data");
    expect(document.getElementById("Compute_cpu_cores__source_name").value).toBe("user data");
    expect(document.getElementById("Compute_cpu_cores__source_link").value).toBe("");
    // Comment is preserved through the swap.
    expect(document.getElementById("Compute_cpu_cores__comment").value).toBe("keep me");
    // The visible source line reflects the new source.
    expect(document.querySelector(".source-name-display").textContent).toContain("user data");
    // The editor select reflects the new source so re-opening shows it.
    expect(document.querySelector(".source-editor-select").value).toBe("user_data");
});

test("swapHypothesisToUserDataForField is a no-op when source is anything other than hypothesis", () => {
    mount("field_src_with_sentinels");

    swapHypothesisToUserDataForField("Compute_cpu_cores");

    expect(document.getElementById("Compute_cpu_cores__source_id").value).toBe("src1");
    expect(document.getElementById("Compute_cpu_cores__source_name").value).toBe("ADEME 2024");
});

test("value-changed event resets confidence and swaps hypothesis → user_data in one go", () => {
    mount("field_high_hypothesis");
    const input = document.createElement("input");
    input.id = "Compute_cpu_cores";
    document.querySelector("form").appendChild(input);

    input.dispatchEvent(new CustomEvent("source-metadata:value-changed", { bubbles: true }));

    expect(document.getElementById("Compute_cpu_cores__confidence").value).toBe("");
    expect(document.getElementById("Compute_cpu_cores__source_id").value).toBe("user_data");
});

test("toggleConfidenceMenu adds .menu-up when the badge sits near the bottom of #source-block", () => {
    document.body.innerHTML = `
        <div id="source-block">
            <div class="confidence-wrap">
                <button class="confidence-badge"></button>
                <div class="confidence-menu"></div>
            </div>
        </div>`;
    const block = document.getElementById("source-block");
    const btn = document.querySelector(".confidence-badge");
    const menu = document.querySelector(".confidence-menu");
    // Badge bottom (90) + 200px estimate (290) overflows container bottom (100) → flip up.
    block.getBoundingClientRect = () => ({bottom: 100});
    btn.getBoundingClientRect = () => ({bottom: 90});

    toggleConfidenceMenu(btn);

    expect(menu.classList.contains("menu-up")).toBe(true);
    expect(menu.classList.contains("open")).toBe(true);
});

test("toggleConfidenceMenu does NOT flip when there's room below", () => {
    document.body.innerHTML = `
        <div id="source-block">
            <div class="confidence-wrap">
                <button class="confidence-badge menu-up"></button>
                <div class="confidence-menu menu-up"></div>
            </div>
        </div>`;
    const block = document.getElementById("source-block");
    const btn = document.querySelector(".confidence-badge");
    const menu = document.querySelector(".confidence-menu");
    // Plenty of room (containerBottom 1000, badge bottom 50): flip-up class must be cleared.
    block.getBoundingClientRect = () => ({bottom: 1000});
    btn.getBoundingClientRect = () => ({bottom: 50});

    toggleConfidenceMenu(btn);

    expect(menu.classList.contains("menu-up")).toBe(false);
});

test("toggleConfidenceMenu clones the shared template when the badge has no inline menu", () => {
    document.body.innerHTML = `
        <template id="source-table-confidence-menu-template">
            <div class="confidence-menu">
                <div class="menu-item" data-level="high" data-action="set-confidence"></div>
                <div class="menu-item" data-level="medium" data-action="set-confidence"></div>
                <div class="menu-item" data-level="low" data-action="set-confidence"></div>
                <div class="menu-item selected" data-level="none" data-action="set-confidence"></div>
            </div>
        </template>
        <div id="source-block">
            <div class="confidence-wrap">
                <button class="confidence-badge" data-level="medium"></button>
            </div>
        </div>`;
    const btn = document.querySelector(".confidence-badge");
    document.getElementById("source-block").getBoundingClientRect = () => ({bottom: 1000});
    btn.getBoundingClientRect = () => ({bottom: 50});

    toggleConfidenceMenu(btn);

    const menus = document.querySelectorAll(".confidence-wrap > .confidence-menu");
    expect(menus.length).toBe(1);
    expect(menus[0].classList.contains("open")).toBe(true);
    expect(menus[0].querySelector('[data-level="medium"]').classList.contains("selected")).toBe(true);
    expect(menus[0].querySelector('[data-level="none"]').classList.contains("selected")).toBe(false);
});

test("setConfidence on a wrap with autosave attrs POSTs only the new confidence", async () => {
    document.body.innerHTML = `
        <div class="confidence-wrap" data-field-id="row1"
             data-autosave-url="/edit/obj1/">
            <button class="confidence-badge conf-none" data-level="none">
                <span class="bars"><i></i><i></i><i></i></span>
            </button>
            <div class="confidence-menu">
                <div class="menu-item" data-level="high" data-action="set-confidence"></div>
            </div>
            <input type="hidden" name="Server_ram__confidence" id="row1__confidence" value="">
        </div>`;

    const ajaxCalls = [];
    global.htmx = {
        ajax: jest.fn((method, url, opts) => {
            ajaxCalls.push({method, url, opts});
            return Promise.resolve();
        }),
    };

    const highItem = document.querySelector('[data-level="high"]');
    setConfidence(highItem, "high");
    await Promise.resolve(); // let the .then() chain flush

    expect(global.tagFormAsModified).not.toHaveBeenCalled();
    expect(ajaxCalls[0]).toEqual({
        method: "POST",
        url: "/edit/obj1/",
        opts: {
            values: {"Server_ram__confidence": "high"},
            swap: "none",
        },
    });
    expect(ajaxCalls).toHaveLength(1);
    expect(document.getElementById("row1__confidence").value).toBe("high");

    delete global.htmx;
});

/* ===== In-form source editor (source-table row) ===== */

test("applySourceEditor in row form mode writes hidden inputs and triggers form submit (no manual POST)", () => {
    mountRowEditor("row_editor_listed_user_data");
    const editor = document.getElementById("editor-row1_row");
    editor.querySelector(".source-editor-select").value = "src1";
    editor.querySelector(".source-editor-comment").value = "vetted";
    global.htmx = {trigger: jest.fn(), ajax: jest.fn()};

    applySourceEditor("row1_row");

    expect(document.getElementById("row1_row__source_id").value).toBe("src1");
    expect(document.getElementById("row1_row__source_name").value).toBe("ADEME 2024");
    expect(document.getElementById("row1_row__source_link").value).toBe("https://ademe.fr");
    expect(document.getElementById("row1_row__comment").value).toBe("vetted");
    expect(global.htmx.trigger).toHaveBeenCalledWith(
        document.querySelector("form[data-action='source-table-row-edit']"), "submit");
    expect(global.htmx.ajax).not.toHaveBeenCalled();
    delete global.htmx;
});

test("applySourceEditor in row form mode + custom source mints fresh id when prior was a listed source", () => {
    mountRowEditor("row_editor_listed_src1");
    const editor = document.getElementById("editor-row1_row");
    editor.querySelector(".source-editor-select").value = "__custom__";
    editor.querySelector(".source-editor-custom-name").value = "Internal";
    editor.querySelector(".source-editor-custom-link").value = "https://x";
    global.htmx = {trigger: jest.fn()};

    applySourceEditor("row1_row");

    const newId = document.getElementById("row1_row__source_id").value;
    expect(newId).toMatch(/^[0-9a-f]{6}$/);
    expect(newId).not.toBe("src1");
    expect(document.getElementById("row1_row__source_name").value).toBe("Internal");
    expect(document.getElementById("row1_row__source_link").value).toBe("https://x");
    delete global.htmx;
});

test("applySourceEditor in row form mode + custom source reuses prior id when still editing the same custom source", () => {
    mountRowEditor("row_editor_unlisted_custom");
    initInFormSourceEditorsIn(); // editor needs to be in __custom__ mode to read the prior id correctly
    const editor = document.getElementById("editor-row1_row");
    editor.querySelector(".source-editor-custom-name").value = "Internal v2";
    global.htmx = {trigger: jest.fn()};

    applySourceEditor("row1_row");

    expect(document.getElementById("row1_row__source_id").value).toBe("abc123");
    delete global.htmx;
});

test("initInFormSourceEditorsIn flips the select to __custom__ and prefills name/link when prior source isn't listed", () => {
    mountRowEditor("row_editor_unlisted_custom");

    initInFormSourceEditorsIn();

    const editor = document.getElementById("editor-row1_row");
    expect(editor.querySelector(".source-editor-select").value).toBe("__custom__");
    expect(document.getElementById("custom-fields-row1_row").classList.contains("open")).toBe(true);
    expect(editor.querySelector(".source-editor-custom-name").value).toBe("Internal");
    expect(editor.querySelector(".source-editor-custom-link").value).toBe("");
});

test("initInFormSourceEditorsIn keeps the listed source selected and the custom-fields panel hidden when prior id matches", () => {
    mountRowEditor("row_editor_listed_src1");

    initInFormSourceEditorsIn();

    const editor = document.getElementById("editor-row1_row");
    expect(editor.querySelector(".source-editor-select").value).toBe("src1");
    expect(document.getElementById("custom-fields-row1_row").classList.contains("open")).toBe(false);
});

test("autosaveConfidence on a 'none' selection sends an empty confidence string", async () => {
    document.body.innerHTML = `
        <div class="confidence-wrap" data-field-id="row2"
             data-autosave-url="/edit/objX/">
            <input type="hidden" name="X_attr__confidence" value="high">
        </div>`;
    const wrap = document.querySelector(".confidence-wrap");
    global.htmx = { ajax: jest.fn(() => Promise.resolve()) };

    autosaveConfidence(wrap, "");
    await Promise.resolve();

    expect(global.htmx.ajax).toHaveBeenCalledWith(
        "POST", "/edit/objX/",
        expect.objectContaining({values: expect.objectContaining({"X_attr__confidence": ""})})
    );
    delete global.htmx;
});

test("checkCollision flags a typed name that matches a listed source (case-insensitive)", () => {
    mount("field_src_listed");
    const input = document.querySelector(".source-editor-custom-name");
    const notice = document.getElementById("collision-Compute_cpu_cores");

    input.value = "ademe 2024";
    checkCollision(input, "Compute_cpu_cores");
    expect(notice.classList.contains("visible")).toBe(true);

    input.value = "Brand new name";
    checkCollision(input, "Compute_cpu_cores");
    expect(notice.classList.contains("visible")).toBe(false);
});
