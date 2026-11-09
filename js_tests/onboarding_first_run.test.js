const {
    SEEN_KEY,
    onboardingSeen,
    markOnboardingSeen,
    handleBuilderEntry,
} = require("../theme/static/scripts/onboarding_first_run.js");

function renderBuilder({ withPicker = false } = {}) {
    document.body.innerHTML = `
        <div id="main-content-block">
            <div id="model-builder-page">
                ${withPicker ? '<div id="example-picker"></div>' : ""}
            </div>
        </div>
    `;
}

beforeEach(() => {
    localStorage.clear();
    document.body.innerHTML = "";
});

describe("flag round-trip", () => {
    test("markOnboardingSeen / onboardingSeen agree", () => {
        expect(onboardingSeen()).toBe(false);
        markOnboardingSeen();
        expect(localStorage.getItem(SEEN_KEY)).toBe("true");
        expect(onboardingSeen()).toBe(true);
    });
});

describe("handleBuilderEntry", () => {
    test("emits onboarding:first-run once on a loaded canvas and marks seen", () => {
        renderBuilder();
        const handler = jest.fn();
        document.body.addEventListener("onboarding:first-run", handler);

        handleBuilderEntry();
        expect(handler).toHaveBeenCalledTimes(1);
        expect(onboardingSeen()).toBe(true);

        // Second entry is a no-op: the flag is already set.
        handleBuilderEntry();
        expect(handler).toHaveBeenCalledTimes(1);
    });

    test("does not emit while the example picker still overlays the canvas", () => {
        renderBuilder({ withPicker: true });
        const handler = jest.fn();
        document.body.addEventListener("onboarding:first-run", handler);

        handleBuilderEntry();
        expect(handler).not.toHaveBeenCalled();
        expect(onboardingSeen()).toBe(false);
    });

    test("emits once the picker is gone (e.g. an example loaded)", () => {
        renderBuilder({ withPicker: true });
        const handler = jest.fn();
        document.body.addEventListener("onboarding:first-run", handler);

        handleBuilderEntry();           // picker present → deferred
        expect(handler).not.toHaveBeenCalled();

        document.getElementById("example-picker").remove();
        handleBuilderEntry();           // picker gone → fires
        expect(handler).toHaveBeenCalledTimes(1);
        expect(onboardingSeen()).toBe(true);
    });

    test("does nothing when not on the builder page", () => {
        document.body.innerHTML = "<div>home</div>";
        const handler = jest.fn();
        document.body.addEventListener("onboarding:first-run", handler);

        handleBuilderEntry();
        expect(handler).not.toHaveBeenCalled();
        expect(onboardingSeen()).toBe(false);
    });

    test("does not re-emit for a returning user (flag already set)", () => {
        markOnboardingSeen();
        renderBuilder();
        const handler = jest.fn();
        document.body.addEventListener("onboarding:first-run", handler);

        handleBuilderEntry();
        expect(handler).not.toHaveBeenCalled();
    });
});

test.each(["input", "summary"])("AI %s consumes first-run without emitting or deferring a tour", panel => {
    renderBuilder();
    document.querySelector("#model-builder-page").innerHTML = `<div data-ai-bootstrap-panel="${panel}"></div>`;
    const handler = jest.fn();
    document.body.addEventListener("onboarding:first-run", handler);
    handleBuilderEntry();
    expect(onboardingSeen()).toBe(true);
    expect(handler).not.toHaveBeenCalled();
    document.querySelector("[data-ai-bootstrap-panel]").remove();
    handleBuilderEntry();
    expect(handler).not.toHaveBeenCalled();
});
