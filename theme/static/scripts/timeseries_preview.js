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

    function destroyPreview(region) {
        const canvas = region?.querySelector("[data-timeseries-preview-canvas]");
        if (!canvas || !canvas._timeseriesPreviewChart) return;
        canvas._timeseriesPreviewChart.destroy();
        canvas._timeseriesPreviewChart = null;
    }

    function renderChart(region, config) {
        const canvas = region.querySelector("[data-timeseries-preview-canvas]");
        if (!canvas || typeof window.Chart !== "function") return null;
        if (canvas._timeseriesPreviewChart && canvas._timeseriesPreviewChart.config.type !== config.type) {
            destroyPreview(region);
        }
        if (canvas._timeseriesPreviewChart) {
            canvas._timeseriesPreviewChart.config.type = config.type;
            canvas._timeseriesPreviewChart.data = config.data;
            canvas._timeseriesPreviewChart.options = config.options;
            canvas._timeseriesPreviewChart.update();
            return canvas._timeseriesPreviewChart;
        }
        canvas._timeseriesPreviewChart = new window.Chart(canvas.getContext("2d"), config);
        return canvas._timeseriesPreviewChart;
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
            if (config) renderChart(region, config);
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

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {consumeResponses, destroyIn, destroyPreview, renderChart, selectResponse};
    }
}());
