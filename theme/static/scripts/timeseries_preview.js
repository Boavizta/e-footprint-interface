(function () {
    "use strict";

    function previewRegion(previewId) {
        return Array.from(document.querySelectorAll("[data-timeseries-preview]")).find(function (candidate) {
            return candidate.dataset.previewId === previewId;
        }) || null;
    }

    function parseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (error) {
            return fallback;
        }
    }

    function previewCanvas(region) {
        const canvasId = region?.dataset.timeseriesPreviewCanvasId;
        return canvasId ? document.getElementById(canvasId) : region?.querySelector("[data-timeseries-preview-canvas]");
    }

    function previewContainer(region) {
        const containerId = region?.dataset.timeseriesPreviewContainerId;
        return containerId ? document.getElementById(containerId) : region;
    }

    function destroyPreview(region) {
        const canvas = previewCanvas(region);
        if (!canvas || !canvas._timeseriesPreviewChart) return;
        canvas._timeseriesPreviewChart.destroy();
        if (window.chart === canvas._timeseriesPreviewChart) window.chart = null;
        canvas._timeseriesPreviewChart = null;
    }

    function renderChart(region, config) {
        const canvas = previewCanvas(region);
        if (!canvas || typeof window.Chart !== "function") return null;
        if (canvas._timeseriesPreviewChart && canvas._timeseriesPreviewChart.config.type !== config.type) {
            destroyPreview(region);
        }
        if (canvas._timeseriesPreviewChart) {
            canvas._timeseriesPreviewChart.config.type = config.type;
            canvas._timeseriesPreviewChart.data = config.data;
            canvas._timeseriesPreviewChart.options = config.options;
            canvas._timeseriesPreviewChart.update();
            if (canvas.id === "timeSeriesChart") window.chart = canvas._timeseriesPreviewChart;
            return canvas._timeseriesPreviewChart;
        }
        canvas._timeseriesPreviewChart = new window.Chart(canvas.getContext("2d"), config);
        if (canvas.id === "timeSeriesChart") window.chart = canvas._timeseriesPreviewChart;
        return canvas._timeseriesPreviewChart;
    }

    function selectedGranularity(region) {
        const controlId = region?.dataset.timeseriesPreviewGranularityId;
        return controlId ? document.getElementById(controlId)?.value : null;
    }

    function renderSelectedSeries(region) {
        const configs = region?._timeseriesPreviewConfigs;
        const granularity = selectedGranularity(region);
        const config = configs && (configs[granularity] || Object.values(configs)[0]);
        return config ? renderChart(region, config) : null;
    }

    function setPreviewVisibility(region, visible) {
        const container = previewContainer(region);
        if (!container) return;
        const shouldShow = visible && window.innerWidth >= 1200;
        container.classList.toggle("d-none", !shouldShow);
        container.classList.toggle("d-block", shouldShow);
        if (!shouldShow) destroyPreview(region);
    }

    function selectResponse(response) {
        const region = previewRegion(response.dataset.previewId);
        if (!region) return false;
        const responseSequence = Number(response.dataset.requestSequence);
        const latestSequence = Number(region.dataset.latestRequestSequence || 0);
        if (!Number.isFinite(responseSequence) || responseSequence !== latestSequence) return false;

        const success = response.dataset.success === "true";
        const errors = parseJson(response.dataset.errors || "[]", []);
        const status = region.querySelector("[data-timeseries-preview-status]");
        if (status) status.textContent = response.dataset.status || "";
        if (success) {
            const config = parseJson(response.dataset.chartConfig || "", null);
            const configs = parseJson(response.dataset.chartConfigs || "", null);
            if (configs) {
                region._timeseriesPreviewConfigs = configs;
                renderSelectedSeries(region);
            } else if (config) {
                renderChart(region, config);
            }
        }
        region.dispatchEvent(new CustomEvent("timeseries-preview:response", {
            bubbles: true,
            detail: {success: success, errors: errors, requestSequence: responseSequence},
        }));
        return true;
    }

    function consumeResponses(container) {
        if (!container?.querySelectorAll) return;
        const responses = [];
        if (container.matches?.("[data-timeseries-preview-response]")) responses.push(container);
        responses.push(...container.querySelectorAll("[data-timeseries-preview-response]"));
        responses.forEach(selectResponse);
        if (container.matches?.("[data-timeseries-preview-responses]")) container.replaceChildren();
    }

    function destroyIn(container) {
        if (!container?.querySelectorAll) return;
        if (container.matches?.("[data-timeseries-preview]")) destroyPreview(container);
        container.querySelectorAll("[data-timeseries-preview]").forEach(destroyPreview);
    }

    document.addEventListener("htmx:afterSwap", function (event) {
        consumeResponses(event.detail?.target || event.target);
    });

    document.addEventListener("htmx:beforeCleanupElement", function (event) {
        destroyIn(event.detail?.elt || event.target);
    });

    document.addEventListener("timeseries-preview:visibility", function (event) {
        const region = event.target.closest?.("[data-timeseries-preview]") || event.target;
        if (region?.matches?.("[data-timeseries-preview]")) {
            setPreviewVisibility(region, Boolean(event.detail?.visible));
        }
    });

    window.createOrUpdateTimeSeriesChart = function () {
        const region = document.querySelector("[data-hourly-timeseries-preview]");
        if (region) renderSelectedSeries(region);
    };

    window.closeTimeseriesChart = function () {
        document.dispatchEvent(new CustomEvent("timeseries-preview:close-hourly"));
        document.querySelectorAll("[data-hourly-timeseries-preview]").forEach(function (region) {
            setPreviewVisibility(region, false);
        });
        const canvas = document.getElementById("timeSeriesChart");
        if (canvas?._timeseriesPreviewChart) {
            canvas._timeseriesPreviewChart.destroy();
            canvas._timeseriesPreviewChart = null;
        }
        window.chart = null;
        const container = document.getElementById("chartTimeseries");
        container?.classList.add("d-none");
        container?.classList.remove("d-block");
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            consumeResponses, destroyIn, destroyPreview, renderChart, renderSelectedSeries, selectResponse,
            setPreviewVisibility,
        };
    }
}());
