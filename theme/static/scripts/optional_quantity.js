(function () {
    function controllerFor(control) {
        const id = control.dataset.emptyControllerId;
        return id ? control.closest("form")?.querySelector(`#${id}`) : null;
    }

    function sync(control) {
        const toggle = control.querySelector('[data-action="optional-quantity-empty"]');
        const number = control.querySelector('input[type="number"]');
        const valueGroup = control.querySelector('[data-optional-quantity-value]');
        const controller = controllerFor(control);
        const controllerValue = controller?.value || control.dataset.emptyControllerValue;
        const forced = (control.dataset.emptyOnlyFor || "").split(",").filter(Boolean).includes(controllerValue);

        if (forced) toggle.checked = true;
        toggle.disabled = forced;
        if (toggle.checked) number.value = "";
        number.required = !toggle.checked;
        valueGroup.classList.toggle("d-none", toggle.checked);
    }

    function initialize() {
        document.querySelectorAll("[data-optional-quantity]").forEach(control => {
            if (control.dataset.optionalQuantityInitialized) return;
            control.dataset.optionalQuantityInitialized = "true";
            const controller = controllerFor(control);
            controller?.addEventListener("change", () => sync(control));
            sync(control);
        });
    }

    document.addEventListener("change", event => {
        if (event.target.dataset.action !== "optional-quantity-empty") return;
        const control = event.target.closest("[data-optional-quantity]");
        sync(control);
        control.dispatchEvent(new CustomEvent("optional-quantity:changed", {
            bubbles: true, detail: {empty: event.target.checked},
        }));
        if (!event.target.checked) control.querySelector('input[type="number"]').focus();
    });
    document.addEventListener("initDynamicForm", initialize);
    document.body.addEventListener("htmx:afterSettle", initialize);
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
    else initialize();
})();
