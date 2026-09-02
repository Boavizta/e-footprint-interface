const fs = require("fs");
const path = require("path");

require("../theme/static/scripts/model_builder_main.js");

const FIXTURE = path.join(__dirname, "fixtures", "inline_count_autosave.html");

beforeEach(() => {
    document.body.innerHTML = fs.readFileSync(FIXTURE, "utf8");
});

function input() {
    return document.querySelector("[data-action='autosave-relationship-count']");
}

test("the real autosaving count partial is required", () => {
    expect(input().required).toBe(true);
});

test("committing a blank restores the latest live value and suppresses the change", () => {
    const field = input();
    const requestListener = jest.fn();
    field.addEventListener("change", requestListener);

    field.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
    field.value = "4.75";
    field.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
    field.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    field.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
    field.value = "";
    const accepted = field.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));

    expect(field.defaultValue).toBe("2.5");
    expect(field.value).toBe("4.75");
    expect(accepted).toBe(false);
    expect(requestListener).toHaveBeenCalledTimes(1);
});

test.each(["0", "3", "1.25"])("valid numeric value %s reaches the change listener", value => {
    const field = input();
    const requestListener = jest.fn();
    field.addEventListener("change", requestListener);

    field.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
    field.value = value;
    const accepted = field.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));

    expect(field.value).toBe(value);
    expect(accepted).toBe(true);
    expect(requestListener).toHaveBeenCalledTimes(1);
});

test("strictly-positive relationships reject zero without imposing an epsilon", () => {
    document.body.innerHTML = fs.readFileSync(
        path.join(__dirname, "fixtures", "inline_count_strictly_positive.html"), "utf8"
    );
    const field = input();
    const requestListener = jest.fn();
    field.addEventListener("change", requestListener);
    field.dispatchEvent(new FocusEvent("focusin", {bubbles: true}));
    field.value = "0";

    expect(field.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}))).toBe(false);
    expect(field.value).toBe("0.5");
    expect(requestListener).not.toHaveBeenCalled();

    field.value = "0.000000000001";
    expect(field.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}))).toBe(true);
    expect(requestListener).toHaveBeenCalledTimes(1);
});
