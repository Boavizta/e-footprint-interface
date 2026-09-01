(function () {
    "use strict";

    const requestTimers = new WeakMap();
    const activeRequests = new WeakMap();
    const managedRegions = new Set();

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

    function requestOwner(region) {
        return region?.closest("[data-timeseries-builder], [data-hourly-timeseries-preview]") || region;
    }

    function setPreviewStatus(region, message) {
        const status = region?.querySelector("[data-timeseries-preview-status]");
        if (!status) return;
        status.textContent = message || "";
        status.hidden = !message;
    }

    function beginRequestRevision(region) {
        const sequence = Number(region.dataset.latestRequestSequence || 0) + 1;
        region.dataset.latestRequestSequence = String(sequence);
        return sequence;
    }

    function finishRequest(region, activeRequest) {
        if (activeRequests.get(region) === activeRequest) activeRequests.delete(region);
        activeRequest.source.remove();
        if (!requestTimers.has(region) && !activeRequests.has(region)) managedRegions.delete(region);
    }

    function abortRequest(region) {
        const activeRequest = activeRequests.get(region);
        if (!activeRequest) return;
        activeRequests.delete(region);
        activeRequest.source.dispatchEvent(new Event("htmx:abort"));
        activeRequest.source.remove();
    }

    function cancelRequest(region) {
        if (!region) return;
        const timer = requestTimers.get(region);
        if (timer) window.clearTimeout(timer);
        requestTimers.delete(region);
        beginRequestRevision(region);
        abortRequest(region);
        managedRegions.delete(region);
    }

    function handleTransportFailure(region, sequence, message) {
        if (Number(region.dataset.latestRequestSequence) === sequence) {
            setPreviewStatus(region, message || "Preview could not be refreshed; the last valid chart is retained.");
        }
    }

    function sendRequest(region, sequence, detail) {
        const owner = requestOwner(region);
        const sink = owner?.querySelector("[data-timeseries-preview-responses]");
        if (!owner || !sink || Number(region.dataset.latestRequestSequence) !== sequence || !window.htmx?.ajax) {
            managedRegions.delete(region);
            return;
        }

        setPreviewStatus(region, detail.refreshingStatus);
        const source = document.createElement("span");
        source.hidden = true;
        source.dataset.timeseriesPreviewRequest = "";
        document.body.appendChild(source);
        const activeRequest = {source: source, sequence: sequence};
        activeRequests.set(region, activeRequest);
        const values = {
            ...detail.values,
            preview_id: region.dataset.previewId || owner.dataset.previewId,
            request_sequence: String(sequence),
        };
        let request;
        try {
            request = window.htmx.ajax("POST", owner.dataset.previewUrl, {
                source: source,
                target: sink,
                swap: "innerHTML",
                values: values,
            });
        } catch (error) {
            handleTransportFailure(region, sequence, detail.failureStatus);
            finishRequest(region, activeRequest);
            return;
        }
        if (request && typeof request.then === "function") {
            Promise.resolve(request).then(
                function () { finishRequest(region, activeRequest); },
                function () {
                    handleTransportFailure(region, sequence, detail.failureStatus);
                    finishRequest(region, activeRequest);
                }
            );
        } else {
            finishRequest(region, activeRequest);
        }
    }

    function scheduleRequest(region, detail) {
        const previousTimer = requestTimers.get(region);
        if (previousTimer) window.clearTimeout(previousTimer);
        requestTimers.delete(region);
        abortRequest(region);
        const sequence = beginRequestRevision(region);
        managedRegions.add(region);
        setPreviewStatus(region, detail.waitingStatus);
        const timer = window.setTimeout(function () {
            requestTimers.delete(region);
            sendRequest(region, sequence, detail);
        }, detail.delay || 0);
        requestTimers.set(region, timer);
    }

    function previewRegionsIn(container) {
        if (!container?.querySelectorAll) return [];
        const regions = [];
        if (container.matches?.("[data-timeseries-preview]")) regions.push(container);
        regions.push(...container.querySelectorAll("[data-timeseries-preview]"));
        return regions;
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
        setPreviewStatus(region, response.dataset.status || "");
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
        previewRegionsIn(container).forEach(destroyPreview);
    }

    document.addEventListener("timeseries-preview:request", function (event) {
        const region = event.target.closest?.("[data-timeseries-preview]") || event.target;
        if (region?.matches?.("[data-timeseries-preview]")) scheduleRequest(region, event.detail || {});
    });

    document.addEventListener("timeseries-preview:cancel", function (event) {
        const region = event.target.closest?.("[data-timeseries-preview]") || event.target;
        if (region?.matches?.("[data-timeseries-preview]")) cancelRequest(region);
    });

    document.addEventListener("htmx:afterSwap", function (event) {
        consumeResponses(event.detail?.target || event.target);
    });

    document.addEventListener("htmx:beforeCleanupElement", function (event) {
        const container = event.detail?.elt || event.target;
        previewRegionsIn(container).forEach(cancelRequest);
        destroyIn(container);
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
        Array.from(managedRegions).forEach(cancelRequest);
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
            cancelRequest, consumeResponses, destroyIn, destroyPreview, renderChart, renderSelectedSeries,
            scheduleRequest, selectResponse, setPreviewVisibility,
        };
    }
}());
