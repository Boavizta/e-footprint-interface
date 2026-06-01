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
                    // Mirror driver.js: destroying a tour fires its onDestroyed hook,
                    // which is how tour.js clears its active-instance reference.
                    destroy: () => { destroyCalls += 1; config.onDestroyed?.(); },
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
    test("maps every server step straight through to a driver step", () => {
        mount("tour_loaded");
        const steps = tour.readTourSteps();
        const driverSteps = tour.buildDriverSteps(steps);
        expect(driverSteps.length).toBe(steps.length);
        expect(driverSteps.every(s => s.popover && s.popover.title)).toBe(true);
    });

    test("the help step opens the help drawer as it begins", () => {
        mount("tour_loaded");
        const steps = tour.readTourSteps();
        const helpIndex = steps.findIndex(s => s.open_help_class);
        const helpStep = tour.buildDriverSteps(steps)[helpIndex];
        expect(typeof helpStep.onHighlightStarted).toBe("function");

        // tour.js delegates the actual open to help_drawer_utils.js's
        // data-action dispatch; stand in for it here.
        const action = jest.fn();
        document.body.addEventListener("click", function (event) {
            const trigger = event.target.closest("[data-action]");
            if (trigger) action(trigger.dataset.action, trigger.dataset.helpClass);
        });

        helpStep.onHighlightStarted();
        expect(action).toHaveBeenCalledWith("open-help-drawer", "UsageJourney");
    });

    test("the help-menu step closes the help drawer as it begins", () => {
        mount("tour_loaded");
        const steps = tour.readTourSteps();
        const closeIndex = steps.findIndex(s => s.close_help);
        const closeStep = tour.buildDriverSteps(steps)[closeIndex];
        expect(typeof closeStep.onHighlightStarted).toBe("function");

        const action = jest.fn();
        document.body.addEventListener("click", function (event) {
            const trigger = event.target.closest("[data-action]");
            if (trigger) action(trigger.dataset.action);
        });

        closeStep.onHighlightStarted();
        expect(action).toHaveBeenCalledWith("close-help-drawer");
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

    test("replaying while a tour is active destroys the in-flight instance first", () => {
        mount("tour_loaded");
        tour.runTour();
        expect(window.driver.js.driver).toHaveBeenCalledTimes(1);
        const destroyedBefore = destroyCalls;

        // A second run with the first still live must tear the first one down,
        // not stack a second tour on screen.
        tour.runTour();
        expect(window.driver.js.driver).toHaveBeenCalledTimes(2);
        expect(destroyCalls).toBe(destroyedBefore + 1);
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

    test("re-opening the template picker ends an active tour", () => {
        mount("tour_loaded");
        tour.runTour();
        const destroyedBefore = destroyCalls;

        // Help ▸ Open templates swaps the picker back into #main-content-block; tour.js
        // tears the tour down so the picker is not stranded under the overlay.
        const swapped = document.createElement("div");
        swapped.innerHTML = '<div id="template-picker"></div>';
        document.body.appendChild(swapped);
        document.body.dispatchEvent(new CustomEvent("htmx:afterSwap", { detail: { target: swapped } }));
        expect(destroyCalls).toBe(destroyedBefore + 1);
    });
});

