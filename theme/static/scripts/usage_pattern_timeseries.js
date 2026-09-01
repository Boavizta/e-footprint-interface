(function () {
    "use strict";

    const PREVIEW_DEBOUNCE_MS = 300;

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

    function previewRequestValues(root) {
        const fieldWebId = root.dataset.fieldWebId || "";
        const separator = fieldWebId.indexOf("_");
        return {
            object_type: separator < 0 ? "" : fieldWebId.slice(0, separator),
            field_name: root.dataset.fieldName,
            builder: "growth",
            form_inputs: JSON.stringify(formInputs(root)),
        };
    }

    function schedulePreview(root, delay) {
        if (!validForPreview(root) || window.innerWidth < 1200) {
            root.dispatchEvent(new CustomEvent("timeseries-preview:cancel", {bubbles: true}));
            setVisible(root, false);
            return;
        }
        setVisible(root, true);
        root.dispatchEvent(new CustomEvent("timeseries-preview:request", {
            bubbles: true,
            detail: {delay: delay, values: previewRequestValues(root)},
        }));
    }

    function initialize(root) {
        if (!root || root.dataset.hourlyTimeseriesPreviewInitialized === "true") return;
        root.dataset.hourlyTimeseriesPreviewInitialized = "true";
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
