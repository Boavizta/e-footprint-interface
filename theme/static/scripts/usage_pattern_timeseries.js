(function () {
    "use strict";

    const PREVIEW_DEBOUNCE_MS = 300;
    const previewTimers = new WeakMap();
    const activeRequests = new WeakMap();
    const initializedRoots = new Set();

    function durationMaximum(unit) {
        return unit === "month" ? 120 : 10;
    }

    function controls(root) {
        return {
            startDate: root.querySelector('[id$="start_date"]'),
            duration: root.querySelector('[id$="modeling_duration_value"]'),
            durationUnit: root.querySelector('[id$="modeling_duration_unit"]'),
            initialVolume: root.querySelector('[id$="initial_volume"]'),
            initialVolumeTimespan: root.querySelector('[id$="initial_volume_timespan"]'),
            growthRate: root.querySelector('[id$="net_growth_rate_in_percentage"]'),
            growthTimespan: root.querySelector('[id$="net_growth_rate_timespan"]'),
        };
    }

    function validateDuration(root) {
        const fields = controls(root);
        const maximum = durationMaximum(fields.durationUnit.value);
        const value = Number.parseInt(fields.duration.value, 10);
        const error = root.querySelector("[data-modeling-duration-error]");
        fields.duration.max = String(maximum);
        if (!Number.isFinite(value) || value <= 0) {
            fields.duration.value = fields.durationUnit.value === "month" ? "12" : "1";
            error.textContent = "Modeling duration value must be greater than 0 and can't be empty";
            error.classList.remove("d-none");
        } else if (value > maximum) {
            fields.duration.value = String(maximum);
            error.textContent = `Modeling duration value must be less than or equal to ${maximum}`;
            error.classList.remove("d-none");
        } else {
            error.textContent = "";
            error.classList.add("d-none");
        }
    }

    function validForPreview(root) {
        const fields = controls(root);
        return Boolean(fields.startDate.value)
            && Number(fields.duration.value) > 0
            && Number(fields.initialVolume.value) > 0
            && fields.growthRate.value !== "";
    }

    function formInputs(root) {
        const fields = controls(root);
        return {
            start_date: fields.startDate.value,
            modeling_duration_value: fields.duration.value,
            modeling_duration_unit: fields.durationUnit.value,
            initial_volume: fields.initialVolume.value,
            initial_volume_timespan: fields.initialVolumeTimespan.value,
            net_growth_rate_in_percentage: fields.growthRate.value,
            net_growth_rate_timespan: fields.growthTimespan.value,
        };
    }

    function setVisible(root, visible) {
        root.dispatchEvent(new CustomEvent("timeseries-preview:visibility", {
            bubbles: true,
            detail: {visible: visible},
        }));
    }

    function abortRequest(root) {
        const request = activeRequests.get(root);
        if (!request) return;
        activeRequests.delete(root);
        request.source.dispatchEvent(new Event("htmx:abort"));
        request.source.remove();
    }

    function sendPreview(root, sequence) {
        const sink = root.querySelector("[data-timeseries-preview-responses]");
        if (!sink || Number(root.dataset.latestRequestSequence) !== sequence || !window.htmx?.ajax) return;
        const source = document.createElement("span");
        source.hidden = true;
        document.body.appendChild(source);
        const activeRequest = {source: source, sequence: sequence};
        activeRequests.set(root, activeRequest);
        const fieldWebId = root.dataset.fieldWebId || "";
        const separator = fieldWebId.indexOf("_");
        const request = window.htmx.ajax("POST", root.dataset.previewUrl, {
            source: source,
            target: sink,
            swap: "innerHTML",
            values: {
                object_type: separator < 0 ? "" : fieldWebId.slice(0, separator),
                field_name: root.dataset.fieldName,
                builder: "growth",
                form_inputs: JSON.stringify(formInputs(root)),
                preview_id: root.dataset.previewId,
                request_sequence: String(sequence),
            },
        });
        const finish = function () {
            if (activeRequests.get(root) === activeRequest) activeRequests.delete(root);
            source.remove();
        };
        if (request && typeof request.then === "function") Promise.resolve(request).then(finish, finish);
        else finish();
    }

    function schedulePreview(root, delay) {
        const previousTimer = previewTimers.get(root);
        if (previousTimer) window.clearTimeout(previousTimer);
        abortRequest(root);
        const sequence = Number(root.dataset.latestRequestSequence || 0) + 1;
        root.dataset.latestRequestSequence = String(sequence);
        if (!validForPreview(root) || window.innerWidth < 1200) {
            setVisible(root, false);
            return;
        }
        setVisible(root, true);
        const timer = window.setTimeout(function () {
            previewTimers.delete(root);
            sendPreview(root, sequence);
        }, delay);
        previewTimers.set(root, timer);
    }

    function initialize(root) {
        if (!root || root.dataset.hourlyTimeseriesPreviewInitialized === "true") return;
        root.dataset.hourlyTimeseriesPreviewInitialized = "true";
        initializedRoots.add(root);
        validateDuration(root);
        schedulePreview(root, 0);
    }

    function initializeAll(container) {
        if (!container?.querySelectorAll) return;
        if (container.matches?.("[data-hourly-timeseries-preview]")) initialize(container);
        container.querySelectorAll("[data-hourly-timeseries-preview]").forEach(initialize);
    }

    document.addEventListener("input", function (event) {
        const root = event.target.closest?.("[data-hourly-timeseries-preview]");
        if (!root || !event.target.matches("[data-hourly-preview-input]")) return;
        if (typeof window.tagFormAsModified === "function") window.tagFormAsModified();
        if (event.target.matches('[id$="modeling_duration_value"]')) validateDuration(root);
        schedulePreview(root, PREVIEW_DEBOUNCE_MS);
    });

    document.addEventListener("change", function (event) {
        const root = event.target.closest?.("[data-hourly-timeseries-preview]");
        if (!root || !event.target.matches("[data-hourly-preview-input]")) return;
        if (typeof window.tagFormAsModified === "function") window.tagFormAsModified();
        if (event.target.matches('[id$="modeling_duration_unit"]')) validateDuration(root);
        schedulePreview(root, 0);
    });

    document.addEventListener("htmx:afterSettle", function (event) {
        initializeAll(event.detail?.target || event.target);
    });

    document.addEventListener("htmx:beforeCleanupElement", function (event) {
        const container = event.detail?.elt || event.target;
        if (!container?.querySelectorAll) return;
        const roots = [];
        if (container.matches?.("[data-hourly-timeseries-preview]")) roots.push(container);
        roots.push(...container.querySelectorAll("[data-hourly-timeseries-preview]"));
        roots.forEach(function (root) {
            const timer = previewTimers.get(root);
            if (timer) window.clearTimeout(timer);
            abortRequest(root);
            initializedRoots.delete(root);
        });
    });

    document.addEventListener("timeseries-preview:close-hourly", function () {
        initializedRoots.forEach(function (root) {
            const timer = previewTimers.get(root);
            if (timer) window.clearTimeout(timer);
            abortRequest(root);
        });
        initializedRoots.clear();
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { initializeAll(document); }, {once: true});
    } else {
        initializeAll(document);
    }

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            durationMaximum, formInputs, initializeAll, schedulePreview, validateDuration, validForPreview,
        };
    }
}());
