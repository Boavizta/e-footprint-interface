const {
    getAccordionOwnerElement,
    parseLinkedIds,
    resolveLeaderLineEndpoint,
    resolveLeaderLineTargets,
    updateLines,
    _setAllLinesForTesting,
} = require("../theme/static/scripts/leaderline_utils.js");

function markVisible(element) {
    Object.defineProperty(element, "getClientRects", {
        configurable: true,
        value: () => [{width: 1, height: 1}],
    });
}

function markHidden(element) {
    Object.defineProperty(element, "getClientRects", {
        configurable: true,
        value: () => [],
    });
}

beforeEach(() => {
    document.body.innerHTML = "";
});

test("visible direct endpoint resolves to itself", () => {
    document.body.innerHTML = `
        <div id="service-1"></div>
    `;
    const target = document.getElementById("service-1");
    markVisible(target);

    expect(resolveLeaderLineEndpoint(target)?.id).toBe("service-1");
});

test("accordion collapse resolves to its owning element", () => {
    document.body.innerHTML = `
        <div id="server-1"></div>
        <div id="flush-server-1" class="accordion-collapse collapse"></div>
    `;

    expect(getAccordionOwnerElement(document.getElementById("flush-server-1"))?.id).toBe("server-1");
});

test("hidden target inside collapsed accordion resolves to nearest visible accordion owner", () => {
    document.body.innerHTML = `
        <div id="server-1"></div>
        <div id="flush-server-1" class="accordion-collapse collapse">
            <div id="service-1"></div>
        </div>
    `;
    const server = document.getElementById("server-1");
    const service = document.getElementById("service-1");
    markVisible(server);
    markHidden(service);

    expect(resolveLeaderLineEndpoint(service)?.id).toBe("server-1");
});

test("hidden grouped component resolves to device accordion owner", () => {
    document.body.innerHTML = `
        <div id="device-1"></div>
        <div id="flush-device-1" class="accordion-collapse collapse">
            <div id="component-1"></div>
        </div>
    `;
    const device = document.getElementById("device-1");
    const component = document.getElementById("component-1");
    markVisible(device);
    markHidden(component);

    expect(resolveLeaderLineEndpoint(component)?.id).toBe("device-1");
});

test("hidden grouped device resolves to nearest visible subgroup owner", () => {
    document.body.innerHTML = `
        <div id="root-group"></div>
        <div id="flush-root-group" class="accordion-collapse collapse show">
            <div id="subgroup-1"></div>
            <div id="flush-subgroup-1" class="accordion-collapse collapse">
                <div id="device-1"></div>
            </div>
        </div>
    `;
    const rootGroup = document.getElementById("root-group");
    const subgroup = document.getElementById("subgroup-1");
    const device = document.getElementById("device-1");
    markVisible(rootGroup);
    markVisible(subgroup);
    markHidden(device);

    expect(resolveLeaderLineEndpoint(device)?.id).toBe("subgroup-1");
});

test("hidden source inside collapsed accordion resolves upward on the source side too", () => {
    document.body.innerHTML = `
        <div id="edge-function-1"></div>
        <div id="flush-edge-function-1" class="accordion-collapse collapse">
            <div id="need-1" class="leader-line-object" data-link-to="|server-1"></div>
        </div>
        <div id="server-1"></div>
    `;
    const edgeFunction = document.getElementById("edge-function-1");
    const need = document.getElementById("need-1");
    const server = document.getElementById("server-1");
    markVisible(edgeFunction);
    markHidden(need);
    markVisible(server);

    expect(resolveLeaderLineEndpoint(need)?.id).toBe("edge-function-1");
});

test("several target ids resolving to the same visible accordion owner are deduplicated", () => {
    document.body.innerHTML = `
        <div id="job-1" data-link-to="|service-1|service-2"></div>
        <div id="server-1"></div>
        <div id="flush-server-1" class="accordion-collapse collapse">
            <div id="service-1"></div>
            <div id="service-2"></div>
        </div>
    `;
    const source = document.getElementById("job-1");
    const server = document.getElementById("server-1");
    const service1 = document.getElementById("service-1");
    const service2 = document.getElementById("service-2");
    markVisible(server);
    markHidden(service1);
    markHidden(service2);

    expect(parseLinkedIds(source)).toEqual(["service-1", "service-2"]);
    expect(resolveLeaderLineTargets(source).map((element) => element.id)).toEqual(["server-1"]);
});

test("updateLines skips lines whose endpoints were detached by an OOB swap", () => {
    document.body.innerHTML = `
        <div id="from-1"></div>
        <div id="to-1"></div>
    `;
    const fromConnected = document.getElementById("from-1");
    const toConnected = document.getElementById("to-1");
    const fromDetached = document.createElement("div");
    const toDetached = document.createElement("div");

    const positionedLines = [];
    const makeLine = (start, end) => ({start, end, position: jest.fn(() => positionedLines.push({start, end}))});

    const liveLine = makeLine(fromConnected, toConnected);
    const staleStartLine = makeLine(fromDetached, toConnected);
    const staleEndLine = makeLine(fromConnected, toDetached);

    _setAllLinesForTesting({
        "from-1": [liveLine, staleEndLine],
        "stale-source": [staleStartLine],
    });

    expect(() => updateLines()).not.toThrow();
    expect(liveLine.position).toHaveBeenCalledTimes(1);
    expect(staleStartLine.position).not.toHaveBeenCalled();
    expect(staleEndLine.position).not.toHaveBeenCalled();

    _setAllLinesForTesting({});
});
