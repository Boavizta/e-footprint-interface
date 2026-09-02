const fs = require("fs");
const path = require("path");

const {selectResponse} = require("../theme/static/scripts/timeseries_preview.js");

const EDITOR_FIXTURE = fs.readFileSync(
    path.join(__dirname, "fixtures", "weekly_pattern_default.html"), "utf8"
);
const SUCCESS_FIXTURE = fs.readFileSync(
    path.join(__dirname, "fixtures", "timeseries_preview_success.html"), "utf8"
);
const ERROR_FIXTURE = fs.readFileSync(
    path.join(__dirname, "fixtures", "timeseries_preview_error.html"), "utf8"
);
const HOURLY_EDITOR_FIXTURE = fs.readFileSync(
    path.join(__dirname, "fixtures", "hourly_preview_default.html"), "utf8"
);
const HOURLY_SUCCESS_FIXTURE = fs.readFileSync(
    path.join(__dirname, "fixtures", "timeseries_preview_hourly_success.html"), "utf8"
);

function responseFrom(html) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    return wrapper.firstElementChild;
}

beforeEach(() => {
    document.body.innerHTML = EDITOR_FIXTURE;
    HTMLCanvasElement.prototype.getContext = jest.fn(() => ({}));
    window.Chart = jest.fn(function (_context, config) {
        this.config = config;
        this.data = config.data;
        this.options = config.options;
        this.update = jest.fn();
        this.destroy = jest.fn();
    });
});

test("newest valid response creates and then updates one chart instance", () => {
    const region = document.querySelector("[data-timeseries-preview]");
    region.dataset.latestRequestSequence = "2";
    expect(selectResponse(responseFrom(SUCCESS_FIXTURE))).toBe(true);
    expect(window.Chart).toHaveBeenCalledTimes(1);
    const chart = region.querySelector("canvas")._timeseriesPreviewChart;
    expect(chart.data.labels).toEqual(["Mon 00:00", "Mon 01:00"]);
    expect(region.querySelector("[data-timeseries-preview-status]").textContent).toBe("");
    expect(region.querySelector("[data-timeseries-preview-status]").hidden).toBe(true);

    region.dataset.latestRequestSequence = "2";
    expect(selectResponse(responseFrom(SUCCESS_FIXTURE))).toBe(true);
    expect(window.Chart).toHaveBeenCalledTimes(1);
    expect(chart.update).toHaveBeenCalledTimes(1);
});

test("stale responses cannot update the active preview", () => {
    const region = document.querySelector("[data-timeseries-preview]");
    region.dataset.latestRequestSequence = "3";

    expect(selectResponse(responseFrom(SUCCESS_FIXTURE))).toBe(false);
    expect(window.Chart).not.toHaveBeenCalled();
    expect(region.querySelector("[data-timeseries-preview-status]").textContent.trim()).toBe("Preparing preview…");
});

test("invalid newest response retains the last valid chart and publishes structured errors", () => {
    const region = document.querySelector("[data-timeseries-preview]");
    region.dataset.latestRequestSequence = "2";
    selectResponse(responseFrom(SUCCESS_FIXTURE));
    const chart = region.querySelector("canvas")._timeseriesPreviewChart;
    const listener = jest.fn();
    region.addEventListener("timeseries-preview:response", listener);

    region.dataset.latestRequestSequence = "3";
    expect(selectResponse(responseFrom(ERROR_FIXTURE))).toBe(true);

    expect(region.querySelector("canvas")._timeseriesPreviewChart).toBe(chart);
    expect(chart.destroy).not.toHaveBeenCalled();
    expect(region.querySelector("[data-timeseries-preview-status]").textContent).toContain("last valid chart");
    expect(region.querySelector("[data-timeseries-preview-status]").hidden).toBe(false);
    expect(listener.mock.calls[0][0].detail.errors[0].path).toBe("profiles[0].baseline");
});

test("destroying an HTMX-swapped subtree disposes its chart", () => {
    const root = document.querySelector("[data-timeseries-builder]");
    const region = root.querySelector("[data-timeseries-preview]");
    region.dataset.latestRequestSequence = "2";
    selectResponse(responseFrom(SUCCESS_FIXTURE));
    const chart = region.querySelector("canvas")._timeseriesPreviewChart;

    root.dispatchEvent(new CustomEvent("htmx:beforeCleanupElement", {
        bubbles: true,
        detail: {elt: root},
    }));

    expect(chart.destroy).toHaveBeenCalledTimes(1);
    expect(region.querySelector("canvas")._timeseriesPreviewChart).toBeNull();
});

test("HTMX response-sink swaps select the response and clear the carrier", () => {
    const region = document.querySelector("[data-timeseries-preview]");
    const sink = document.querySelector("[data-timeseries-preview-responses]");
    region.dataset.latestRequestSequence = "2";
    sink.innerHTML = SUCCESS_FIXTURE;

    sink.dispatchEvent(new CustomEvent("htmx:afterSwap", {
        bubbles: true,
        detail: {target: sink},
    }));

    expect(window.Chart).toHaveBeenCalledTimes(1);
    expect(sink.children).toHaveLength(0);
});

test("template gives the weekly preview its own external surface", () => {
    const editor = document.querySelector("[data-timeseries-editor-column]");
    const preview = document.querySelector("[data-timeseries-preview-column]");

    expect(preview.classList).toContain("recurrent-timeseries-preview-shell");
    expect(preview.querySelector("[data-timeseries-preview]").classList).toContain("recurrent-timeseries-preview");
    expect(preview.querySelector("[data-timeseries-preview]").classList).toContain("timeseries-preview-panel");
    expect(preview.querySelector(".timeseries-preview-panel__chart")).not.toBeNull();
    expect(editor.className).not.toContain("col-");
    expect(preview.className).not.toContain("col-");
});

test("weekly and hourly previews share the same panel template structure", () => {
    const weeklyPanel = document.querySelector("[data-timeseries-preview]");
    const weeklyStructure = Array.from(weeklyPanel.children).map((child) => child.className);

    document.body.innerHTML = HOURLY_EDITOR_FIXTURE;
    const hourlyPanel = document.getElementById("chartTimeseries");

    expect(hourlyPanel.classList).toContain("timeseries-preview-panel");
    expect(hourlyPanel.querySelector(".timeseries-preview-panel__title")).not.toBeNull();
    expect(hourlyPanel.querySelector(".timeseries-preview-panel__chart")).not.toBeNull();
    expect(weeklyStructure).toContain("timeseries-preview-panel__title my-2");
});

test("hourly granularity switches between server-prepared series without another request", () => {
    document.body.innerHTML = HOURLY_EDITOR_FIXTURE;
    const region = document.querySelector("[data-hourly-timeseries-preview]");
    region.dataset.latestRequestSequence = "2";

    expect(selectResponse(responseFrom(HOURLY_SUCCESS_FIXTURE))).toBe(true);
    expect(window.Chart).toHaveBeenCalledTimes(1);
    const chart = document.getElementById("timeSeriesChart")._timeseriesPreviewChart;
    expect(window.chart).toBe(chart);
    expect(chart.data.labels).toEqual(["2025-01", "2025-02"]);

    document.getElementById("display_granularity").value = "year";
    window.createOrUpdateTimeSeriesChart();

    expect(window.Chart).toHaveBeenCalledTimes(1);
    expect(chart.update).toHaveBeenCalledTimes(1);
    expect(chart.data.labels).toEqual(["2025", "2026"]);
});
