let resizeTimeout;
let globalListenersInitialized = false;
let currentScrollableArea = null;
let currentScrollContainer = null;

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

let allLines = new Map();

function updateLines() {
    Object.values(allLines).forEach(lineArray => {
        lineArray.forEach(line => {
            line.position();
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
    allLines = [];
}

function updateOrCreateLines(element) {

    function drawLines(fromElement) {
        const linkedIds = fromElement.dataset.linkTo?.split('|') || [];
        linkedIds.forEach(toElementId => {
            if (!allLines[fromElement.id]) {
                allLines[fromElement.id] = [];
            }
            const existingLine = allLines[fromElement.id].find(line => line.end.id === toElementId);
            if (!existingLine) {
                const toElement = document.getElementById(toElementId);
                if (toElement) {
                    let optLine = fromElement.getAttribute('data-line-opt');
                    let line = new LeaderLine(fromElement, toElement, {
                      ...dictLeaderLineOption[optLine],
                      parent: document.getElementById('leaderlines-layer')
                    });
                    allLines[fromElement.id].push(line);
                }
            }
        });
    }

    function getDirectLeaderLineChildren(parent) {
        return Array.from(parent.querySelectorAll('.leader-line-object'))
            .filter(child => child.parentElement.closest('.leader-line-object') === parent);
    }

    const elementId = element.id;
    let accordionCollapse = document.getElementById("flush-" + elementId);
    if (accordionCollapse) {
        let isOpen = accordionCollapse.classList.contains('show');
        if (isOpen) {
            const childElements = getDirectLeaderLineChildren(element);
            if (childElements.length > 0) {
                removeAllLinesDepartingFromElement(elementId);
                childElements.forEach(child => updateOrCreateLines(child));
            } else {
                drawLines(element);
            }
            // Handle usage journey step circles
            const svgLeaderLineChildren = element.querySelectorAll('img.leader-line-object');
            svgLeaderLineChildren.forEach(child => drawLines(child));
        }
        else {
            drawLines(element);
            const childElements = element.querySelectorAll('.leader-line-object');
            childElements.forEach(child => removeAllLinesDepartingFromElement(child.id));
        }
    } else {
        drawLines(element);
    }
}

function addAccordionListener(accordion){
    // Prevent adding duplicate listeners
    if (accordion.dataset.leaderLineListenerAdded === "true") {
        return;
    }
    accordion.dataset.leaderLineListenerAdded = "true";

    accordion.addEventListener('shown.bs.collapse', function () {
        let closestLeaderlineObject = accordion.closest('.leader-line-object');
        if (closestLeaderlineObject) {
            updateOrCreateLines(closestLeaderlineObject);
        }
        updateLines();
    });
    accordion.addEventListener('hidden.bs.collapse', function () {
        let closestLeaderlineObject = accordion.closest('.leader-line-object');
        if (closestLeaderlineObject) {
            updateOrCreateLines(closestLeaderlineObject);
        }
        updateLines();
    });
    accordion.addEventListener('hide.bs.collapse', function (event) {
        event.stopPropagation();
        const childElements = accordion.querySelectorAll('.leader-line-object');
        childElements.forEach(child => removeAllLinesDepartingFromElement(child.id));
    });
}

function initLeaderLines() {
    removeAllLines();
    let leaderLineObjects = document.querySelectorAll('.leader-line-object');
    leaderLineObjects.forEach(leaderLineObject => {
        let leaderLineObjectParent = leaderLineObject.parentElement.closest('.leader-line-object');
        if (leaderLineObjectParent == null) {
            updateOrCreateLines(leaderLineObject);
        }
    });
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
