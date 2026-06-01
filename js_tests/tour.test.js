const fs = require("fs");
const path = require("path");

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

// driver.js is mocked: the vendored IIFE exposes window.driver.js.driver. We record the
// config it is built with and the .drive()/.destroy() calls so we can assert step wiring.
let lastDriverConfig;
let driveCalls;
let destroyCalls;

function installDriverMock() {
    lastDriverConfig = null;
    driveCalls = 0;
    destroyCalls = 0;
    window.driver = {
        js: {
            driver: jest.fn((config) => {
                lastDriverConfig = config;
                return {
                    drive: () => { driveCalls += 1; },
                    destroy: () => { destroyCalls += 1; },
                };
            }),
        },
    };
}

function mount(fixtureName) {
    document.body.innerHTML = `<div id="helpDrawer" class="d-none"></div>${loadFixture(fixtureName)}`;
}

// Require once: tour.js attaches its delegated listeners to document.body at load. Re-requiring
// per test (jest.resetModules) would stack duplicate listeners on the persistent jsdom document
// and double-fire the event-driven tests. runTour reads window.driver lazily, so installing the
// mock in beforeEach is enough.
const tour = require("../theme/static/scripts/tour.js");

beforeEach(() => {
    document.body.innerHTML = "";
    installDriverMock();
    window.htmx = { ajax: jest.fn() };
});

describe("readTourSteps", () => {
    test("parses the server-rendered JSON payload", () => {
        mount("tour_loaded");
        const steps = tour.readTourSteps();
        expect(steps.length).toBe(6);
        expect(steps[0].title).toBe("Start in the middle: usage journeys");
    });

    test("returns [] when the payload is absent", () => {
        document.body.innerHTML = "<div></div>";
        expect(tour.readTourSteps()).toEqual([]);
    });
});

describe("buildDriverSteps", () => {
    test("maps server steps to driver steps and drops targets absent from the DOM", () => {
        mount("tour_loaded");
        // Remove one anchor so its step is filtered out.
        document.querySelector('[data-tour-target="results"]').remove();
        const driverSteps = tour.buildDriverSteps(tour.readTourSteps());
        expect(driverSteps.length).toBe(5);
        expect(driverSteps.every(s => s.popover && s.popover.title)).toBe(true);
        expect(driverSteps.some(s => s.element === '[data-tour-target="results"]')).toBe(false);
    });

    test("the help step carries an onHighlighted that opens the help drawer", () => {
        mount("tour_loaded");
        const driverSteps = tour.buildDriverSteps(tour.readTourSteps());
        const helpStep = driverSteps.find(s => typeof s.onHighlighted === "function");
        expect(helpStep).toBeDefined();

        helpStep.onHighlighted();
        expect(window.htmx.ajax).toHaveBeenCalledWith(
            "GET", "/model_builder/open-help-drawer/UsageJourney/",
            { target: "#helpDrawer", swap: "innerHTML" });
        const helpDrawer = document.getElementById("helpDrawer");
        expect(helpDrawer.style.pointerEvents).toBe("auto");
    });
});

describe("runTour", () => {
    test("builds a driver instance from the server steps and drives it", () => {
        mount("tour_loaded");
        tour.runTour();
        expect(window.driver.js.driver).toHaveBeenCalledTimes(1);
        expect(lastDriverConfig.steps.length).toBe(6);
        expect(driveCalls).toBe(1);
    });

    test("does nothing when no steps resolve", () => {
        document.body.innerHTML = `<div id="helpDrawer"></div>`;
        tour.runTour();
        expect(window.driver.js.driver).not.toHaveBeenCalled();
    });

    test("the blank flavor includes the create-a-usage-journey suggestion", () => {
        mount("tour_blank");
        tour.runTour();
        const titles = lastDriverConfig.steps.map(s => s.popover.title);
        expect(titles).toContain("Your first step");
    });
});

describe("event wiring", () => {
    test("auto-runs on the onboarding:first-run event", () => {
        mount("tour_loaded");
        document.body.dispatchEvent(new CustomEvent("onboarding:first-run"));
        expect(window.driver.js.driver).toHaveBeenCalledTimes(1);
    });

    test("replays when a data-action=replay-tour control is clicked", () => {
        mount("tour_loaded");
        document.body.insertAdjacentHTML(
            "beforeend", '<button data-action="replay-tour">Replay</button>');
        document.querySelector('[data-action="replay-tour"]').click();
        expect(window.driver.js.driver).toHaveBeenCalledTimes(1);
    });
});

describe("resetHelpDrawerLayering", () => {
    test("clears the inline overrides applied for the help step", () => {
        mount("tour_loaded");
        tour.openHelpDrawerForTour("UsageJourney");
        tour.resetHelpDrawerLayering();
        const helpDrawer = document.getElementById("helpDrawer");
        expect(helpDrawer.style.pointerEvents).toBe("");
        expect(helpDrawer.style.zIndex).toBe("");
    });
});
