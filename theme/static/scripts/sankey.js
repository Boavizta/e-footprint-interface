/**
 * Sankey diagram client-side logic:
 * - Chip toggle + hidden input sync
 * - Card settings toggle / advanced toggle
 * - Card removal
 * - Plotly cleanup before HTMX swap
 * - Plotly rendering after HTMX settle
 * - Title update after diagram swap
 */

function sankeyToggleSettings(cardId) {
    var el = document.getElementById('settings-' + cardId);
    if (!el) return;
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function sankeyToggleAdvanced(cardId) {
    var el = document.getElementById('advanced-' + cardId);
    var arrow = document.getElementById('advanced-arrow-' + cardId);
    if (!el) return;
    var open = el.style.display !== 'none';
    el.style.display = open ? 'none' : 'block';
    if (arrow) arrow.innerHTML = open ? '&#9654;' : '&#9660;';
}

function sankeyRemoveCard(cardId) {
    var card = document.getElementById('sankey-card-' + cardId);
    if (!card) return;
    var plotEl = document.getElementById('sankey-plot-' + cardId);
    if (plotEl && window.Plotly) Plotly.purge(plotEl);
    card.style.transition = 'opacity 0.2s, transform 0.2s';
    card.style.opacity = '0';
    card.style.transform = 'translateY(-10px)';
    setTimeout(function() { card.remove(); }, 200);
}

function sankeyToggleChip(chipEl) {
    var cardId = chipEl.getAttribute('data-card');
    var className = chipEl.getAttribute('data-class');
    var type = chipEl.getAttribute('data-type');
    var form = document.getElementById('settings-' + cardId);
    if (!form) return;

    var inputAttr = 'data-chip-input';
    var inputKey = className + '-' + cardId + '-' + type;
    var fieldName = type === 'exclude' ? 'excluded_types' : 'skipped_classes';
    var activeClass = type === 'exclude' ? 'active-exclude' : 'active';

    var existing = form.querySelector('[' + inputAttr + '="' + inputKey + '"]');
    if (existing) {
        chipEl.classList.remove(activeClass);
        existing.remove();
    } else {
        chipEl.classList.add(activeClass);
        var hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = fieldName;
        hidden.value = className;
        hidden.setAttribute(inputAttr, inputKey);
        form.appendChild(hidden);
    }

    htmx.trigger(form, 'change');
}

// Purge old Plotly instance before HTMX replaces a specific diagram area
document.body.addEventListener('htmx:beforeSwap', function(event) {
    var target = event.detail.target;
    if (!target || !window.Plotly) return;
    // Only purge when replacing a specific diagram area, not when appending to the cards container
    if (target.id && target.id.startsWith('sankey-diagram-area-')) {
        var plots = target.querySelectorAll('[id^="sankey-plot-"]');
        for (var i = 0; i < plots.length; i++) { Plotly.purge(plots[i]); }
    }
});

// Scroll new cards into view and initialise Bootstrap tooltips after HTMX settles
document.body.addEventListener('htmx:afterSettle', function(event) {
    var el = event.detail.elt;
    if (el && el.id && el.id === 'sankey-cards-container') {
        var cards = el.querySelectorAll('.sankey-card');
        if (cards.length > 0) {
            var lastCard = cards[cards.length - 1];
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    // Initialise Bootstrap tooltips for any newly inserted help icons
    if (el && window.bootstrap && bootstrap.Tooltip) {
        el.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(tooltipEl) {
            bootstrap.Tooltip.getOrCreateInstance(tooltipEl);
        });
    }
});

if (typeof module !== 'undefined') {
    module.exports = { sankeyToggleChip, sankeyToggleSettings, sankeyToggleAdvanced, sankeyRemoveCard };
}
