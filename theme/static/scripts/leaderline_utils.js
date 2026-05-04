let resizeTimeout;
let globalListenersInitialized = false;
let currentScrollableArea = null;
let currentScrollContainer = null;
let rebuildAnimationFrameId = null;

let dictLeaderLineOption = {
    'object-to-object': {
        color: "#9CA3AF",
        size: 1,
        startPlug: 'disc',
        endPlug: 'disc',
        startPlugColor: "#E5E7EB",
        endPlugColor: "#E5E7EB",
        startPlugSize: 5,
        endPlugSize: 5,
        startSocket: "right",
        endSocket: "left",
        showEffectName: 'fade'
    },
    'vertical-step-swimlane': {
        path: 'straight',
        color: "#003235",
        size: 3,
        startPlug: 'behind',
        endPlug: 'behind',
        startSocket: "bottom",
        endSocket: "top",
        showEffectName: 'fade'
    },
    "step-dot-line": {
        path: 'straight',
        color: "#9CA3AF",
        size: 2,
        startPlug: 'behind',
        endPlug: 'behind',
        startSocket: "bottom",
        endSocket: "top",
        showEffectName: 'fade',
        dash: { animation: false, len: 2, gap: 4 }
    }
};

let allLines = {};

function updateLines() {
    Object.values(allLines).forEach(lineArray => {
        lineArray.forEach(line => {
            // Skip lines whose endpoints were detached by an OOB swap; resetLeaderLines
            // (fired right after htmx:afterSettle) will rebuild them.
            if (line.start?.isConnected && line.end?.isConnected) {
                line.position();
            }
        });
    });
}

function removeAllLinesDepartingFromElement(elementId) {
    if (allLines[elementId]) {
        allLines[elementId].forEach( line => line.remove());
        delete allLines[elementId];
    }
}

function removeAllLinesArrivingAtElement(elementId) {
    Object.keys(allLines).forEach(key => {
        allLines[key] = allLines[key].filter(line => {
            if (line.end.id === elementId) {
                line.remove();
                return false; // Remove this line from the array
            }
            return true; // Keep this line in the array
        });
    });
}

function removeAllLines() {
    Object.values(allLines).forEach(lineArray => {
        lineArray.forEach(line => line.remove());
    });
    allLines = {};
}

function parseLinkedIds(fromElement) {
    return (fromElement.dataset.linkTo || "")
        .split("|")
        .map(linkedId => linkedId.trim())
        .filter(Boolean);
}

function isElementVisible(element) {
    if (!element) {
        return false;
    }
    const computedStyle = window.getComputedStyle(element);
    return computedStyle.visibility !== "hidden" && computedStyle.display !== "none" && element.getClientRects().length > 0;
}

function getAccordionOwnerElement(accordionCollapse) {
    if (!accordionCollapse?.id?.startsWith("flush-")) {
        return null;
    }
    return document.getElementById(accordionCollapse.id.slice("flush-".length));
}

function resolveLeaderLineEndpoint(element) {
    if (!element) {
        return null;
    }
    if (isElementVisible(element)) {
        return element;
    }

    let currentAccordionCollapse = element.closest(".accordion-collapse");
    while (currentAccordionCollapse) {
        const ownerElement = getAccordionOwnerElement(currentAccordionCollapse);
        if (ownerElement && isElementVisible(ownerElement)) {
            return ownerElement;
        }
        currentAccordionCollapse = currentAccordionCollapse.parentElement?.closest(".accordion-collapse") || null;
    }

    return null;
}

function resolveLeaderLineTargets(fromElement) {
    const resolvedTargetsById = new Map();
    parseLinkedIds(fromElement).forEach(targetId => {
        const targetElement = document.getElementById(targetId);
        const resolvedTarget = resolveLeaderLineEndpoint(targetElement);
        if (resolvedTarget && !resolvedTargetsById.has(resolvedTarget.id)) {
            resolvedTargetsById.set(resolvedTarget.id, resolvedTarget);
        }
    });

    return Array.from(resolvedTargetsById.values());
}

function buildLineRegistry(lineSpecs) {
    const nextLines = {};
    const layer = document.getElementById("leaderlines-layer");

    lineSpecs.forEach(({fromElement, targets, optLine}) => {
        targets.forEach(toElement => {
            if (!nextLines[fromElement.id]) {
                nextLines[fromElement.id] = [];
            }
            nextLines[fromElement.id].push(
                new LeaderLine(fromElement, toElement, {
                    ...dictLeaderLineOption[optLine],
                    parent: layer
                })
            );
        });
    });

    return nextLines;
}

function rebuildAllLeaderLines() {
    const deduplicatedLineSpecs = new Map();
    document.querySelectorAll(".leader-line-object").forEach(sourceElement => {
        const resolvedSourceElement = resolveLeaderLineEndpoint(sourceElement);
        if (!resolvedSourceElement) {
            return;
        }

        const optLine = sourceElement.getAttribute("data-line-opt");
        resolveLeaderLineTargets(sourceElement).forEach(targetElement => {
            if (resolvedSourceElement.id === targetElement.id) {
                return;
            }
            const specKey = `${resolvedSourceElement.id}|${targetElement.id}|${optLine}`;
            if (!deduplicatedLineSpecs.has(specKey)) {
                deduplicatedLineSpecs.set(specKey, {
                    fromElement: resolvedSourceElement,
                    targets: [targetElement],
                    optLine
                });
            }
        });
    });

    const previousLines = allLines;
    allLines = buildLineRegistry(Array.from(deduplicatedLineSpecs.values()));

    Object.values(previousLines).forEach(lineArray => {
        lineArray.forEach(line => line.remove());
    });
}

function scheduleRebuildAllLeaderLines() {
    if (rebuildAnimationFrameId !== null) {
        cancelAnimationFrame(rebuildAnimationFrameId);
    }
    rebuildAnimationFrameId = requestAnimationFrame(() => {
        rebuildAnimationFrameId = null;
        rebuildAllLeaderLines();
        updateLines();
    });
}

function addAccordionListener(accordion){
    // Prevent adding duplicate listeners
    if (accordion.dataset.leaderLineListenerAdded === "true") {
        return;
    }
    accordion.dataset.leaderLineListenerAdded = "true";

    accordion.addEventListener('shown.bs.collapse', function () {
        scheduleRebuildAllLeaderLines();
    });
    accordion.addEventListener('hidden.bs.collapse', function () {
        scheduleRebuildAllLeaderLines();
    });
}

function initLeaderLines() {
    rebuildAllLeaderLines();
    document.querySelectorAll('.accordion').forEach(accordion => {
        addAccordionListener(accordion);
    });

    // Attach scroll listeners to current DOM elements (they may be replaced on JSON upload)
    attachScrollListeners();

    // Only add global listeners once to prevent accumulation
    if (!globalListenersInitialized) {
        globalListenersInitialized = true;

        document.addEventListener("htmx:afterSettle", function() {
            updateLines();
        });

        setLeaderLineListeners();
    }

    updateLines();
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        getAccordionOwnerElement,
        isElementVisible,
        parseLinkedIds,
        resolveLeaderLineEndpoint,
        resolveLeaderLineTargets,
        updateLines,
        _setAllLinesForTesting: (lines) => { allLines = lines; },
    };
}

function attachScrollListeners() {
    // Attach scroll listeners only if DOM elements have changed (e.g., after JSON upload)
    // Old elements + their listeners are garbage collected when removed from DOM
    const newScrollableArea = document.querySelector('#model-canva-scrollable-area');
    const newScrollContainer = document.querySelector('#model-canva');

    if (newScrollableArea && newScrollableArea !== currentScrollableArea) {
        newScrollableArea.addEventListener('scroll', updateLines);
        currentScrollableArea = newScrollableArea;
    }
    if (newScrollContainer && newScrollContainer !== currentScrollContainer) {
        newScrollContainer.addEventListener('scroll', updateLines);
        currentScrollContainer = newScrollContainer;
    }
}

function setLeaderLineListeners() {
    document.body.addEventListener('resetLeaderLines', function (event) {
        removeAllLines();
        // resetLeaderLines is fired pre-swap (HX-Trigger) so the new DOM isn't here yet.
        // 100ms is a slack window that lets HTMX finish swap + settle before we rebuild.
        // Cleaner alternative: set a "pendingRebuild" flag here and rebuild from the
        // htmx:afterSettle handler — left as a follow-up since the timer works fine.
        setTimeout(() => {initLeaderLines();}, 100);
    });

    document.body.addEventListener('setAccordionListeners', function (event) {
        event.detail['accordionIds'].forEach(accordionId => {
            addAccordionListener(document.getElementById(accordionId));
        });
        initGrabEffect();
    });

    let resizeTimeout = null;

    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            requestAnimationFrame(() => {
                updateLines();
            });
        }, 100);
    });
}
