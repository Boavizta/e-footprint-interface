function initModelBuilderMain() {
    initLeaderLines();
    initSortableObjectCards();
    initGrabEffect();
    initHammer();
    initTruncatedTextTooltips();
}

function rememberAutosavingRelationshipCount(event) {
    const input = event.target.closest("[data-action='autosave-relationship-count']");
    if (input) {
        input.dataset.valueBeforeEdit = input.value;
    }
}

function rejectInvalidAutosavingRelationshipCount(event) {
    const input = event.target.closest("[data-action='autosave-relationship-count']");
    const valueBeforeEdit = input?.dataset.valueBeforeEdit;
    if (!input || valueBeforeEdit === undefined) {
        return;
    }

    const value = Number(input.value);
    const invalid = input.value === "" || !Number.isFinite(value)
        || (input.dataset.strictlyPositive === "true" && value <= 0);
    if (!invalid) return;

    input.value = valueBeforeEdit;
    event.preventDefault();
    event.stopImmediatePropagation();
}

// Capture before HTMX receives the change on the input. Delegation keeps the guard active for
// relationship controls introduced by partial and out-of-band swaps.
document.addEventListener("focusin", rememberAutosavingRelationshipCount, true);
document.addEventListener("change", rejectInvalidAutosavingRelationshipCount, true);

function initTruncatedTextTooltips(root = document) {
    if (!window.bootstrap || !bootstrap.Tooltip) {
        return;
    }

    root.querySelectorAll(".truncated-text-tooltip[data-bs-toggle='tooltip']").forEach(element => {
        if (element.dataset.tooltipTruncationListenerAdded !== "true") {
            element.addEventListener("show.bs.tooltip", event => {
                if (!isTextTruncated(element)) {
                    event.preventDefault();
                }
            });
            element.dataset.tooltipTruncationListenerAdded = "true";
        }

        bootstrap.Tooltip.getOrCreateInstance(element, {
            container: "body",
            delay: { show: 0, hide: 0 },
            trigger: "hover",
            // animation: false keeps hide() synchronous so its cleanup can't be deferred past an
            // HTMX swap that disposes the instance (see bootstrap_widgets.js disposeShownWidgets).
            animation: false
        });
    });
}

function isTextTruncated(element) {
    return element.scrollWidth > element.clientWidth;
}

const CARD_ORDER_LIST_IDS = [
    "up-list",
    "uj-list",
    "external-api-list",
    "server-list",
    "edge-device-groups-list",
    "edge-devices-list",
];

function csrfTokenFromHtmxHeaders() {
    try {
        return JSON.parse(document.body.getAttribute("hx-headers") || "{}")["X-CSRFToken"] || "";
    } catch (_error) {
        return "";
    }
}

function requestWorkspaceStorageStatus() {
    const statusRegion = document.getElementById("workspace-storage-status");
    if (!statusRegion || !window.htmx) return;
    return window.htmx.ajax("GET", "/model_builder/workspace-storage-status/", {
        target: "#workspace-storage-status",
        swap: "none",
    });
}

function saveCardOrder(sortables) {
    const cardOrder = Object.fromEntries(
        sortables.map(({listId, sortable}) => [listId, sortable.toArray()])
    );
    const xhr = {};
    const begin = new CustomEvent("workspace-mutation:begin", {cancelable: true, detail: {xhr}});
    if (!document.body.dispatchEvent(begin)) return Promise.resolve();
    let successful = false;
    return fetch("/model_builder/save-card-order/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfTokenFromHtmxHeaders(),
        },
        body: JSON.stringify(cardOrder),
    }).then(response => {
        successful = response.ok;
        if (response.ok) requestWorkspaceStorageStatus();
    }).catch(() => {}).finally(() => {
        document.body.dispatchEvent(new CustomEvent("workspace-mutation:end", {detail: {xhr, successful}}));
    });
}

function initSortableObjectCards() {
    const sortables = [];
    const options = {
        animation: 150,
        dataIdAttr: "id",
        onStart: () => {
            document.querySelectorAll('.grabbing').forEach(el => {
                el.classList.remove('grabbing');
            });
        },
        onEnd: () =>{
            document.querySelectorAll('.grabbing').forEach(el => {
                el.classList.remove('grabbing');
            });
            updateLines();
            saveCardOrder(sortables);
        }
    };

    CARD_ORDER_LIST_IDS.forEach(listId => {
        const element = document.getElementById(listId);
        const existingSortable = Sortable.get(element);
        if (existingSortable) {
            existingSortable.destroy();
        }
        const sortable = new Sortable(element, options);
        sortables.push({listId, sortable});
    });
}

let timer = null;

function initGrabEffect() {
    document.querySelectorAll(".grab").forEach(element => {
        if (element.dataset.grabListenerAdded === "true") {
            return;
        }
        element.addEventListener("mousedown", e => {
            timer = setTimeout(() => {
                element.classList.add('grabbing');
            }, 200);
        });
        ["mouseup", "mouseleave"].forEach(event => {
            element.addEventListener(event, () => {
                element.classList.remove('grabbing');
                clearTimeout(timer);
                timer = null;
            });
        });
        element.dataset.grabListenerAdded = "true";
    });
}

function reverseIconAccordion(objectId){
    let icon = document.getElementById("icon_accordion_"+objectId);
    if (icon.classList.contains("chevron-rotate")) {
        icon.classList.remove("chevron-rotate");
    }
    else {
        icon.classList.add("chevron-rotate");
    }
    updateLines();
}

function hideEditIcons(){
    let editIcons = document.querySelectorAll("[id^='edit-icon-']");
    editIcons.forEach(icon => {
        icon.classList.add("d-none");
    })
}

function removeAllOpenedObjectsHighlights(){
    hideEditIcons();
    let objectsActivated = document.querySelectorAll(".model-builder-card-opened");
    objectsActivated.forEach(function (object) {
        object.classList.remove("model-builder-card-opened");
    });
}


function highlightObjectAfterAddOrEdit(modelObjectId){
    let element = document.getElementById(modelObjectId);
    if (element) {
        element.classList.add("border-pulse-after-add-edit-object");
        setTimeout(() => {
            element.classList.remove("border-pulse-after-add-edit-object");
            updateLines();
        }, 1000);
    }
}

// A modeling object is rendered once per place it is mirrored. Every mirror's card button id is
// `button-<canonical web_id>`, optionally suffixed `_in_<parent web_id>`. The server sends only the
// canonical web_id (constant-size header — listing every mirror can overflow nginx's upstream header
// buffer and 502); the client expands it to all card buttons here.
function cardButtonsForWebId(webId) {
    const base = `button-${webId}`;
    return document.querySelectorAll(`[id="${base}"], [id^="${base}_in_"]`);
}

document.body.addEventListener("highlightOpenedObjects", function (event) {
    let webId = event.detail.value;
    if (!webId) return;
    cardButtonsForWebId(webId).forEach(function (element) {
        element.classList.add("model-builder-card-opened");
    })
})

document.body.addEventListener("displayToastAndHighlightObjects", function (event) {
    let toastElement = document.getElementById("toast-push-notification");
    let toastBody = document.getElementById("toast-content");
    let toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastElement);
    const container = document.getElementById("model-canva-scrollable-area");

    let actionType = event.detail["action_type"];
    let modelObjectName = event.detail["name"];
    let constraintMessages = event.detail["constraint_messages"] || [];
    let baseMessage;
    if (actionType === "delete_object"){
        baseMessage = `${modelObjectName} has been deleted!`;
    }else if( actionType === "edit_object") {
        baseMessage = `${modelObjectName} has been updated!`;
    }else if( actionType === "add_new_object"){
        baseMessage = `${modelObjectName} has been saved!`;
    }
    if (constraintMessages.length > 0) {
        toastBody.innerHTML = baseMessage + " — " + constraintMessages.join(" — ");
    } else {
        toastBody.innerHTML = baseMessage;
    }

    const highlightButtons = event.detail["id"] ? Array.from(cardButtonsForWebId(event.detail["id"])) : [];
    highlightButtons.forEach((element, index) => {
        if (index === 0) {
            const rect = element.getBoundingClientRect();
            if (rect.top < 0 || rect.bottom > window.innerHeight) {
                setTimeout(() => {
                    element.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }, 100);
            }
        }
        highlightObjectAfterAddOrEdit(element.id);
    })

    toastBootstrap.show();
});


function scrollToRight() {
    const wrapper = document.getElementById("model-canva-scrollable-area");
    if (!wrapper) return;

    const scrollAmount = wrapper.clientWidth / 2;
    wrapper.scrollBy({
        left: scrollAmount,
        behavior: 'smooth'
    });
}

function scrollToLeft() {
    const wrapper = document.getElementById("model-canva-scrollable-area");
    if (!wrapper) return;

    const scrollAmount = wrapper.clientWidth / 2;
    wrapper.scrollBy({
        left: -scrollAmount,
        behavior: 'smooth'
    });
}

function updateScrollButtons(){
        const wrapper = document.getElementById("model-canva-scrollable-area");
        const btnRight = document.getElementById("model-scroll-to-right");
        const btnLeft = document.getElementById("model-scroll-to-left");
        const maxScrollLeft = wrapper.scrollWidth - wrapper.clientWidth;
        const currentScroll = wrapper.scrollLeft;

        if (btnRight) {
            if (Math.ceil(currentScroll) >= maxScrollLeft) {
                btnRight.classList.remove("d-block");
                btnRight.classList.add("d-none");
            } else {
                btnRight.classList.remove("d-none");
                btnRight.classList.add("d-block");
            }
        }

        if (btnLeft) {
            if (Math.floor(currentScroll) <= 0) {
                btnLeft.classList.remove("d-block");
                btnLeft.classList.add("d-none");
            } else {
                btnLeft.classList.remove("d-none");
                btnLeft.classList.add("d-block");
            }
        }
    }

document.addEventListener("DOMContentLoaded", () => {
    const wrapper = document.getElementById("model-canva-scrollable-area");
    initTruncatedTextTooltips();
    if (!wrapper) return;
    wrapper.addEventListener("scroll", updateScrollButtons);
    updateScrollButtons();
});

function restoreAccordionStateInFragment(serverResponse) {
    // Snapshot all currently-known accordion states (open = true, closed = false)
    const accordionStates = new Map();
    document.querySelectorAll('.accordion-collapse').forEach(el => {
        accordionStates.set(el.id, el.classList.contains('show'));
    });
    if (accordionStates.size === 0) return serverResponse;

    const doc = new DOMParser().parseFromString(serverResponse, 'text/html');
    let modified = false;

    doc.querySelectorAll('.accordion-collapse').forEach(collapseEl => {
        const wasOpen = accordionStates.get(collapseEl.id);
        if (wasOpen === undefined) return; // new element — keep server default

        const webId = collapseEl.id.replace(/^flush-/, '');
        const icon = doc.getElementById(`icon_accordion_${webId}`);
        const toggleBtn = doc.querySelector(`[data-bs-target="#flush-${webId}"]`);
        const isOpenInFragment = collapseEl.classList.contains('show');

        if (wasOpen && !isOpenInFragment) {
            collapseEl.classList.add('show');
            if (icon) icon.classList.add('chevron-rotate');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
            modified = true;
        } else if (!wasOpen && isOpenInFragment) {
            collapseEl.classList.remove('show');
            if (icon) icon.classList.remove('chevron-rotate');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
            modified = true;
        }
    });

    return modified ? doc.body.innerHTML : serverResponse;
}

document.body.addEventListener('htmx:beforeSwap', function (evt) {
    const response = evt.detail.serverResponse;
    if (!response || !response.includes("hx-swap-oob='")) return;
    evt.detail.serverResponse = restoreAccordionStateInFragment(response);
});

// HTMX removes hx-disabled-elt states unconditionally. Keep the original constraint state
// per XHR, and hold workspace controls until all response swaps have settled.
(function () {
    "use strict";
    const disabledBeforeHtmxRequest = new WeakMap();
    const constraintDisabled = new WeakMap();
    const actionSelector = "[hx-post], [hx-put], [hx-patch], [hx-delete], [data-workspace-control], "
        + "[hx-target='#sidePanel'], [hx-target='#comparison-view'], [data-model-tab], "
        + "[data-action='open-add-model-import'], [data-action='edge-modeling-toggle'], "
        + "[data-autosave-url], [data-action='source-table-row-edit'], "
        + "[data-action='toggle-source-table-row-editor'], .grab";
    const editorSelector = "#sidePanel input, #sidePanel select, #sidePanel textarea, #sidePanel button, "
        + "[data-model-canvas] input, [data-model-canvas] select, [data-model-canvas] textarea, "
        + "#result-block input, #result-block select, #result-block textarea, "
        + "[data-workspace-editor] input, [data-workspace-editor] select, [data-workspace-editor] textarea";
    let active = null;

    function isPreview(detail) {
        const path = detail.path || detail.requestConfig?.path || "";
        return path.split("?")[0].endsWith("/timeseries-preview/");
    }

    function isMutation(detail) {
        const verb = detail.verb || detail.requestConfig?.verb;
        return verb && verb.toLowerCase() !== "get" && !isPreview(detail);
    }

    function lockControls() {
        if (!active) return;
        document.querySelectorAll(`${actionSelector}, ${editorSelector}`).forEach(element => {
            // Editor forms contain stateless reading controls; lock their inputs and save actions,
            // rather than declaring the whole form (and its reading controls) aria-disabled.
            if (element.matches("form[data-workspace-editor], [data-workspace-read]")) return;
            if (!active.controls.has(element)) {
                active.controls.set(element, {
                    disabled: "disabled" in element
                        ? (element.hasAttribute("data-disabled-by-htmx")
                            ? constraintDisabled.get(element) ?? element.disabled : element.disabled)
                        : null,
                    ariaDisabled: element.getAttribute("aria-disabled"),
                    href: element.matches("a[data-workspace-control]") ? element.getAttribute("href") : null,
                });
            }
            if ("disabled" in element) element.disabled = true;
            else element.setAttribute("aria-disabled", "true");
            if (element.matches("a[data-workspace-control]")) element.removeAttribute("href");
        });
    }

    function begin(xhr, elt) {
        if (active) return false;
        active = {xhr, elt, controls: new Map(), waitingForSettle: false, settled: false};
        document.body.dataset.workspaceMutation = "updating";
        lockControls();
        document.body.dispatchEvent(new CustomEvent("workspace-mutation:started", {detail: {xhr, elt}}));
        return true;
    }

    function finish(successful) {
        const completed = active;
        completed.controls.forEach((state, element) => {
            if (!element.isConnected) return; // Replacements keep their server-rendered constraints.
            if (state.disabled !== null) element.disabled = state.disabled;
            if (state.ariaDisabled === null) element.removeAttribute("aria-disabled");
            else element.setAttribute("aria-disabled", state.ariaDisabled);
            if (state.href !== null) element.setAttribute("href", state.href);
        });
        active = null;
        delete document.body.dataset.workspaceMutation;
        document.body.dispatchEvent(new CustomEvent("workspace-mutation:finished", {
            detail: {xhr: completed.xhr, elt: completed.elt, successful},
        }));
    }

    function suppress(event) {
        event.preventDefault();
        event.stopImmediatePropagation();
    }

    // HTMX queues same-element requests before beforeRequest. Reject at confirm and at the
    // original interaction; window capture also precedes Compare's document-capture navigation.
    ["click", "change", "input", "submit", "keydown", "mousedown", "touchstart"].forEach(type => {
        window.addEventListener(type, event => {
            if (!active || !(event.target instanceof Element)) return;
            if (event.target.closest("[data-workspace-read]")) return;
            if (event.target.closest(`${actionSelector}, ${editorSelector}`)) suppress(event);
        }, true);
    });
    window.addEventListener("htmx:confirm", event => {
        if (active && (isMutation(event.detail)
            || event.detail.elt?.matches(actionSelector))) suppress(event);
    }, true);
    window.addEventListener("htmx:configRequest", event => {
        if (active && isMutation(event.detail)) suppress(event);
    }, true);

    document.body.addEventListener("htmx:beforeRequest", event => {
        if (event.defaultPrevented) return;
        const {xhr, elt} = event.detail;
        const snapshot = new Map();
        document.querySelectorAll("button").forEach(element => {
            const disabled = active?.controls.get(element)?.disabled
                ?? (element.hasAttribute("data-disabled-by-htmx")
                    ? constraintDisabled.get(element) ?? element.disabled : element.disabled);
            constraintDisabled.set(element, disabled);
            snapshot.set(element, disabled);
        });
        if (isMutation(event.detail) && !begin(xhr, elt)) {
            suppress(event);
            return;
        }
        disabledBeforeHtmxRequest.set(xhr, snapshot);
    });

    document.body.addEventListener("htmx:beforeSend", event => {
        if (active?.xhr !== event.detail.xhr) return;
        // hx-disabled-elt="button" must not also prevent reading/scrolling during a save.
        disabledBeforeHtmxRequest.get(event.detail.xhr)?.forEach((disabled, element) => {
            if (!active.controls.has(element)) element.disabled = disabled;
        });
    });
    document.body.addEventListener("htmx:beforeSwap", event => {
        if (active?.xhr === event.detail.xhr) active.waitingForSettle = event.detail.shouldSwap;
    });
    document.body.addEventListener("htmx:afterSwap", lockControls);
    document.body.addEventListener("htmx:afterSettle", event => {
        if (active?.xhr !== event.detail.xhr) return;
        active.settled = true;
        if (active.requestComplete) finish(active.successful);
    });
    document.body.addEventListener("htmx:afterRequest", event => {
        const {xhr} = event.detail;
        disabledBeforeHtmxRequest.get(xhr)?.forEach((disabled, element) => {
            if (disabled && element.isConnected) element.disabled = true;
        });
        disabledBeforeHtmxRequest.delete(xhr);
        if (active?.xhr === xhr) {
            const triggers = xhr.getResponseHeader?.("HX-Trigger-After-Settle") || "";
            active.successful = event.detail.successful === true && !triggers.includes("openModalDialog");
            active.requestComplete = true;
            if (!active.waitingForSettle || active.settled) finish(active.successful);
            else lockControls();
        } else lockControls();
    });

    document.body.addEventListener("htmx:onLoadError", event => {
        if (active?.xhr === event.detail.xhr) finish(false);
    });

    // Card ordering and diagram deletion use fetch, but still write the same workspace.
    document.body.addEventListener("workspace-mutation:begin", event => {
        if (!begin(event.detail.xhr, event.detail.elt)) event.preventDefault();
    });
    document.body.addEventListener("workspace-mutation:end", event => {
        if (active?.xhr === event.detail.xhr) finish(event.detail.successful);
    });
})();

document.body.addEventListener("htmx:afterSettle", function (event) {
    initTruncatedTextTooltips(event.detail.elt);
});

// Conditional confirmation for destructive model-replacing actions (toolbar reboot, picker cards).
// The triggering element carries `data-confirm-when-model-not-empty="<question>"`; we only prompt
// when the canvas actually holds objects (`.model-builder-card`) — rebooting/replacing an empty
// model has nothing to discard. Decided here at click time from the live DOM, so it stays correct
// no matter which partials have swapped since the toolbar/picker was rendered. Bound once at the
// body level (not per-element hyperscript) so it survives HTMX swaps with no wiring window (see
// conventions.md on hyperscript-on-swapped-content).
document.body.addEventListener("htmx:confirm", function (evt) {
    const elt = evt.target.closest("[data-confirm-when-model-not-empty]");
    if (!elt) return; // not a guarded action — let HTMX proceed normally
    if (!document.querySelector(".model-builder-card")) return; // empty model — nothing to discard
    evt.preventDefault();
    if (window.confirm(elt.getAttribute("data-confirm-when-model-not-empty"))) {
        evt.detail.issueRequest(true);
    }
});

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        CARD_ORDER_LIST_IDS,
        initSortableObjectCards,
        rejectInvalidAutosavingRelationshipCount,
        requestWorkspaceStorageStatus,
        rememberAutosavingRelationshipCount,
    };
}
