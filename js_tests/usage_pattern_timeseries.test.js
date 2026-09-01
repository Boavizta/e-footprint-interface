const fs = require("fs");
const path = require("path");

require("../theme/static/scripts/timeseries_preview.js");
const {
    durationMaximum,
    formInputs,
    initializeAll,
    validateDuration,
    validForPreview,
} = require("../theme/static/scripts/usage_pattern_timeseries.js");

const FIXTURE = fs.readFileSync(path.join(__dirname, "fixtures", "hourly_preview_default.html"), "utf8");

beforeEach(() => {
    jest.useFakeTimers();
    document.body.innerHTML = FIXTURE;
    Object.defineProperty(window, "innerWidth", {value: 1400, configurable: true});
    window.htmx = {ajax: jest.fn()};
});

afterEach(() => {
    jest.useRealTimers();
});

test("valid hourly controls post the fixed growth inputs to the common preview endpoint", () => {
    initializeAll(document);
    jest.runOnlyPendingTimers();

    const root = document.querySelector("[data-hourly-timeseries-preview]");
    expect(validForPreview(root)).toBe(true);
    expect(formInputs(root)).toEqual({
        start_date: "2025-01-01",
        modeling_duration_value: "2",
        modeling_duration_unit: "year",
        initial_volume: "1000",
        initial_volume_timespan: "month",
        net_growth_rate_in_percentage: "10",
        net_growth_rate_timespan: "year",
    });
    expect(window.htmx.ajax).toHaveBeenCalledWith("POST", "/model_builder/timeseries-preview/", expect.objectContaining({
        values: expect.objectContaining({
            object_type: "UsagePattern",
            field_name: "hourly_usage_journey_starts",
            builder: "growth",
        }),
    }));
});

test("invalid controls hide the chart and suppress preview requests", () => {
    const volume = document.querySelector('[id$="initial_volume"]');
    volume.value = "";
    initializeAll(document);
    jest.runOnlyPendingTimers();

    expect(window.htmx.ajax).not.toHaveBeenCalled();
    expect(document.getElementById("chartTimeseries").classList).toContain("d-none");
});

test("duration validation preserves month and year limits", () => {
    const root = document.querySelector("[data-hourly-timeseries-preview]");
    const duration = root.querySelector('[id$="modeling_duration_value"]');
    const unit = root.querySelector('[id$="modeling_duration_unit"]');
    const error = root.querySelector("[data-modeling-duration-error]");

    expect(durationMaximum("year")).toBe(10);
    expect(durationMaximum("month")).toBe(120);
    duration.value = "15";
    validateDuration(root);
    expect(duration.value).toBe("10");
    expect(error.textContent).toContain("less than or equal to 10");

    unit.value = "month";
    duration.value = "0";
    validateDuration(root);
    expect(duration.value).toBe("12");
    expect(error.textContent).toContain("greater than 0");
});

test("small viewports retain responsive hiding and avoid unnecessary requests", () => {
    Object.defineProperty(window, "innerWidth", {value: 768, configurable: true});
    initializeAll(document);
    jest.runOnlyPendingTimers();

    expect(window.htmx.ajax).not.toHaveBeenCalled();
    expect(document.getElementById("chartTimeseries").classList).toContain("d-none");
});

test("closing the side panel cancels a pending preview timer", () => {
    initializeAll(document);
    window.closeTimeseriesChart();
    jest.runOnlyPendingTimers();

    expect(window.htmx.ajax).not.toHaveBeenCalled();
});
