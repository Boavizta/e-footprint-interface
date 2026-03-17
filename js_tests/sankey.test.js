/**
 * Unit tests for sankeyToggleChip() in sankey.js.
 *
 * The chip toggle is the only JS logic that warrants a unit test:
 * a bug there silently breaks parameter submission (CSS changes but
 * the hidden input that HTMX submits is missing).
 */

// Mock htmx before requiring sankey.js (it runs addEventListener at load time)
global.htmx = { trigger: jest.fn() };

// Mock document.body.addEventListener for HTMX events (added at module load)
// jsdom supports this natively, so no special setup needed.

const { sankeyToggleChip } = require('../theme/static/scripts/sankey.js');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSkipChip(cardId = '1', className = 'UsagePattern') {
    document.body.innerHTML = `
        <form id="settings-${cardId}"></form>
        <span class="chip"
              data-class="${className}"
              data-type="skip"
              data-card="${cardId}">${className}</span>
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
});

describe('sankeyToggleChip — skip chips', () => {
    test('activating a skip chip adds "active" CSS class', () => {
        const chip = setupSkipChip();
        sankeyToggleChip(chip);
        expect(chip.classList.contains('active')).toBe(true);
    });

    test('activating a skip chip adds a hidden input with correct name and value', () => {
        const chip = setupSkipChip('1', 'UsagePattern');
        sankeyToggleChip(chip);
        const form = document.getElementById('settings-1');
        const hidden = getHiddenInput(form, 'UsagePattern-1-skip');
        expect(hidden).not.toBeNull();
        expect(hidden.name).toBe('skipped_classes');
        expect(hidden.value).toBe('UsagePattern');
    });

    test('deactivating a skip chip removes "active" CSS class', () => {
        const chip = setupSkipChip();
        sankeyToggleChip(chip); // activate
        sankeyToggleChip(chip); // deactivate
        expect(chip.classList.contains('active')).toBe(false);
    });

    test('deactivating a skip chip removes the hidden input', () => {
        const chip = setupSkipChip('1', 'JobBase');
        sankeyToggleChip(chip); // activate
        sankeyToggleChip(chip); // deactivate
        const form = document.getElementById('settings-1');
        const hidden = getHiddenInput(form, 'JobBase-1-skip');
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
            <span class="chip" data-class="UsagePattern" data-type="skip" data-card="1">UP</span>
            <span class="chip" data-class="JobBase" data-type="skip" data-card="1">Job</span>
        `;
        const chips = document.querySelectorAll('.chip');
        sankeyToggleChip(chips[0]);
        sankeyToggleChip(chips[1]);

        const form = document.getElementById('settings-1');
        const inputs = form.querySelectorAll('input[name="skipped_classes"]');
        expect(inputs.length).toBe(2);
        const values = Array.from(inputs).map(i => i.value);
        expect(values).toContain('UsagePattern');
        expect(values).toContain('JobBase');
    });
});
