/**
 * Unit tests for sankeyToggleChip() in sankey.js.
 *
 * The chip toggle is the only JS logic that warrants a unit test:
 * a bug there silently breaks parameter submission (CSS changes but
 * the hidden input that HTMX submits is missing).
 */

// Mock htmx before requiring sankey.js (it runs addEventListener at load time)
global.htmx = { trigger: jest.fn() };
global.ResizeObserver = class {
    observe() {}
    disconnect() {}
};
global.echarts = {
    init: jest.fn()
};

// Mock document.body.addEventListener for HTMX events (added at module load)
// jsdom supports this natively, so no special setup needed.

const {
    disposeSankeyPlot,
    estimateSankeyRightPadding,
    getSankeyLayout,
    renderSankeyPlot,
    sankeyToggleChip
} = require('../theme/static/scripts/sankey.js');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSkipChip(cardId = '1', columnIndex = '2') {
    document.body.innerHTML = `
        <form id="settings-${cardId}"></form>
        <span class="chip"
              data-class="${columnIndex}"
              data-type="skip"
              data-card="${cardId}">Column ${columnIndex}</span>
    `;
    return document.querySelector('.chip');
}

function setupExcludeChip(cardId = '1', className = 'Device') {
    document.body.innerHTML = `
        <form id="settings-${cardId}"></form>
        <span class="chip"
              data-class="${className}"
              data-type="exclude"
              data-card="${cardId}">${className}</span>
    `;
    return document.querySelector('.chip');
}

function getHiddenInput(form, inputKey) {
    return form.querySelector(`[data-chip-input="${inputKey}"]`);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
    htmx.trigger.mockClear();
    echarts.init.mockReset();
});

describe('sankeyToggleChip — skip chips', () => {
    test('activating a skip chip adds "active" CSS class', () => {
        const chip = setupSkipChip();
        sankeyToggleChip(chip);
        expect(chip.classList.contains('active')).toBe(true);
    });

    test('activating a skip chip adds a hidden input with correct name and value', () => {
        const chip = setupSkipChip('1', '2');
        sankeyToggleChip(chip);
        const form = document.getElementById('settings-1');
        const hidden = getHiddenInput(form, '2-1-skip');
        expect(hidden).not.toBeNull();
        expect(hidden.name).toBe('skipped_columns');
        expect(hidden.value).toBe('2');
    });

    test('deactivating a skip chip removes "active" CSS class', () => {
        const chip = setupSkipChip();
        sankeyToggleChip(chip); // activate
        sankeyToggleChip(chip); // deactivate
        expect(chip.classList.contains('active')).toBe(false);
    });

    test('deactivating a skip chip removes the hidden input', () => {
        const chip = setupSkipChip('1', '6');
        sankeyToggleChip(chip); // activate
        sankeyToggleChip(chip); // deactivate
        const form = document.getElementById('settings-1');
        const hidden = getHiddenInput(form, '6-1-skip');
        expect(hidden).toBeNull();
    });

    test('toggle calls htmx.trigger on the form', () => {
        const chip = setupSkipChip();
        sankeyToggleChip(chip);
        expect(htmx.trigger).toHaveBeenCalledTimes(1);
        const [calledEl, calledEvent] = htmx.trigger.mock.calls[0];
        expect(calledEl.id).toBe('settings-1');
        expect(calledEvent).toBe('change');
    });
});

describe('sankeyToggleChip — exclude chips', () => {
    test('activating an exclude chip uses "active-exclude" class, not "active"', () => {
        const chip = setupExcludeChip();
        sankeyToggleChip(chip);
        expect(chip.classList.contains('active-exclude')).toBe(true);
        expect(chip.classList.contains('active')).toBe(false);
    });

    test('activating an exclude chip adds hidden input with name "excluded_types"', () => {
        const chip = setupExcludeChip('1', 'Device');
        sankeyToggleChip(chip);
        const form = document.getElementById('settings-1');
        const hidden = getHiddenInput(form, 'Device-1-exclude');
        expect(hidden).not.toBeNull();
        expect(hidden.name).toBe('excluded_types');
        expect(hidden.value).toBe('Device');
    });

    test('deactivating an exclude chip removes "active-exclude" class', () => {
        const chip = setupExcludeChip();
        sankeyToggleChip(chip); // activate
        sankeyToggleChip(chip); // deactivate
        expect(chip.classList.contains('active-exclude')).toBe(false);
    });

    test('deactivating an exclude chip removes the hidden input', () => {
        const chip = setupExcludeChip('1', 'Network');
        sankeyToggleChip(chip); // activate
        sankeyToggleChip(chip); // deactivate
        const form = document.getElementById('settings-1');
        const hidden = getHiddenInput(form, 'Network-1-exclude');
        expect(hidden).toBeNull();
    });
});

describe('sankeyToggleChip — multiple chips', () => {
    test('multiple active skip chips produce multiple hidden inputs with same name', () => {
        document.body.innerHTML = `
            <form id="settings-1"></form>
            <span class="chip" data-class="2" data-type="skip" data-card="1">Usage patterns</span>
            <span class="chip" data-class="6" data-type="skip" data-card="1">Jobs / component needs</span>
        `;
        const chips = document.querySelectorAll('.chip');
        sankeyToggleChip(chips[0]);
        sankeyToggleChip(chips[1]);

        const form = document.getElementById('settings-1');
        const inputs = form.querySelectorAll('input[name="skipped_columns"]');
        expect(inputs.length).toBe(2);
        const values = Array.from(inputs).map(i => i.value);
        expect(values).toContain('2');
        expect(values).toContain('6');
    });
});

describe('ECharts rendering', () => {
    test('getSankeyLayout prefers payload layout when provided', () => {
        const layout = getSankeyLayout({
            nodes: [],
            layout: { leftPaddingPx: 42, rightPaddingPx: 128 }
        });

        expect(layout.leftPaddingPx).toBe(42);
        expect(layout.rightPaddingPx).toBe(128);
    });

    test('estimateSankeyRightPadding reserves extra space for long rightmost labels', () => {
        const padding = estimateSankeyRightPadding({
            nodes: [
                { label: 'Manufacturing', depth: 0 },
                { label: 'Short', depth: 1 },
                { label: 'mutualized_equipment_cluster_alpha_beta', depth: 2 }
            ]
        });

        expect(padding).toBeGreaterThan(30);
        expect(padding).toBeLessThanOrEqual(260);
    });

    test('renderSankeyPlot initialises an ECharts instance with Sankey payload', () => {
        const chart = { setOption: jest.fn(), dispose: jest.fn(), resize: jest.fn() };
        echarts.init.mockReturnValue(chart);
        document.body.innerHTML = `
            <div id="sankey-plot-1" data-sankey='{"nodes":[{"key":"node-0","name_key":"Root⁣0","label":"Root","value_kg":10,"depth":0,"color":"rgba(1,2,3,0.8)","tooltip_html":"root"}],"links":[],"layout":{"left_padding_px":30,"right_padding_px":120}}'></div>
        `;

        const plotEl = document.getElementById('sankey-plot-1');
        renderSankeyPlot(plotEl);

        expect(echarts.init).toHaveBeenCalledTimes(1);
        expect(chart.setOption).toHaveBeenCalledTimes(1);
        const option = chart.setOption.mock.calls[0][0];
        expect(option.series[0].type).toBe('sankey');
        expect(option.series[0].left).toBe(30);
        expect(option.series[0].right).toBe(120);
        expect(option.series[0].data[0].name).toBe('Root⁣0');
        expect(option.series[0].data[0].value).toBeUndefined();
        expect(option.series[0].label.formatter({ name: 'Root⁣0' })).toBe('Root');
    });

    test('renderSankeyPlot disposes the previous chart instance before re-rendering', () => {
        const previousChart = { setOption: jest.fn(), dispose: jest.fn(), resize: jest.fn() };
        const nextChart = { setOption: jest.fn(), dispose: jest.fn(), resize: jest.fn() };
        echarts.init.mockReturnValueOnce(nextChart);
        document.body.innerHTML = `
            <div id="sankey-plot-1" data-sankey='{"nodes":[],"links":[]}'></div>
        `;

        const plotEl = document.getElementById('sankey-plot-1');
        plotEl.__sankeyChart = previousChart;
        renderSankeyPlot(plotEl);

        expect(previousChart.dispose).toHaveBeenCalledTimes(1);
        expect(nextChart.setOption).toHaveBeenCalledTimes(1);
    });

    test('disposeSankeyPlot disposes the chart and clears the instance reference', () => {
        const chart = { dispose: jest.fn(), resize: jest.fn() };
        document.body.innerHTML = '<div id="sankey-plot-1"></div>';
        const plotEl = document.getElementById('sankey-plot-1');
        plotEl.__sankeyChart = chart;
        plotEl.__sankeyResizeObserver = { disconnect: jest.fn() };

        disposeSankeyPlot(plotEl);

        expect(chart.dispose).toHaveBeenCalledTimes(1);
        expect(plotEl.__sankeyChart).toBeNull();
        expect(plotEl.__sankeyResizeObserver).toBeNull();
    });
});
