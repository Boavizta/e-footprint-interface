/**
 * Sankey diagram client-side logic:
 * - Chip toggle + hidden input sync
 * - Card settings toggle / advanced toggle
 * - Card removal
 * - ECharts init/dispose around HTMX swaps
 */

var SANKEY_SIDE_PADDING_PX = 30;
var SANKEY_RIGHT_PADDING_MIN_PX = 90;
var SANKEY_RIGHT_PADDING_MAX_PX = 260;
var SANKEY_LABEL_CHAR_WIDTH_PX = 7;
var SANKEY_LABEL_BUFFER_PX = 36;

function estimateSankeyRightPadding(payload) {
    if (!payload || !payload.nodes || payload.nodes.length === 0) {
        return SANKEY_SIDE_PADDING_PX;
    }

    var maxDepth = payload.nodes.reduce(function(currentMax, node) {
        return Math.max(currentMax, typeof node.depth === 'number' ? node.depth : 0);
    }, 0);

    var longestRightLabelLength = payload.nodes.reduce(function(currentMax, node) {
        if ((typeof node.depth === 'number' ? node.depth : 0) !== maxDepth) {
            return currentMax;
        }
        return Math.max(currentMax, (node.label || '').length);
    }, 0);

    if (longestRightLabelLength === 0) {
        return SANKEY_SIDE_PADDING_PX;
    }

    return Math.max(
        SANKEY_RIGHT_PADDING_MIN_PX,
        Math.min(
            SANKEY_RIGHT_PADDING_MAX_PX,
            longestRightLabelLength * SANKEY_LABEL_CHAR_WIDTH_PX + SANKEY_LABEL_BUFFER_PX
        )
    );
}

function getSankeyLayout(payload) {
    var layout = payload && payload.layout ? payload.layout : {};
    var leftPadding = typeof layout.leftPaddingPx === 'number' ? layout.leftPaddingPx : SANKEY_SIDE_PADDING_PX;
    var rightPadding = typeof layout.rightPaddingPx === 'number' ? layout.rightPaddingPx : estimateSankeyRightPadding(payload);

    return {
        leftPaddingPx: leftPadding,
        rightPaddingPx: rightPadding
    };
}

function buildEchartsOption(payload) {
    var labelByKey = {};
    payload.nodes.forEach(function(node) {
        labelByKey[node.nameKey] = node.label;
    });

    var layout = getSankeyLayout(payload);

    return {
        animation: false,
        tooltip: {
            trigger: 'item',
            triggerOn: 'mousemove',
            confine: true,
            formatter: function(params) {
                return params.data && params.data.tooltipHtml ? params.data.tooltipHtml : '';
            }
        },
        series: [{
            type: 'sankey',
            left: layout.leftPaddingPx,
            right: layout.rightPaddingPx,
            top: 10,
            bottom: 30,
            nodeAlign: 'justify',
            draggable: true,
            nodeWidth: 20,
            nodeGap: 20,
            emphasis: { focus: 'adjacency' },
            lineStyle: { curveness: 0.5, opacity: 0.35 },
            label: {
                show: true,
                color: '#334155',
                fontSize: 12,
                formatter: function(params) {
                    return labelByKey[params.name] || '';
                }
            },
            data: payload.nodes.map(function(node) {
                return {
                    name: node.nameKey,
                    depth: node.depth,
                    tooltipHtml: node.tooltipHtml,
                    itemStyle: { color: node.color }
                };
            }),
            links: payload.links.map(function(link) {
                return {
                    source: link.sourceNameKey,
                    target: link.targetNameKey,
                    value: link.valueKg,
                    tooltipHtml: link.tooltipHtml,
                    lineStyle: { color: link.color, opacity: 0.35 }
                };
            })
        }]
    };
}

function disposeSankeyPlot(plotEl) {
    if (!plotEl) return;
    if (plotEl.__sankeyResizeObserver) {
        plotEl.__sankeyResizeObserver.disconnect();
        plotEl.__sankeyResizeObserver = null;
    }
    if (plotEl.__sankeyChart) {
        plotEl.__sankeyChart.dispose();
        plotEl.__sankeyChart = null;
    }
}

function renderSankeyPlot(plotEl) {
    if (!plotEl || !window.echarts) return;
    var payloadAttr = plotEl.getAttribute('data-sankey');
    if (!payloadAttr) return;

    disposeSankeyPlot(plotEl);

    var rawPayload = JSON.parse(payloadAttr);
    var payload = {
        nodes: rawPayload.nodes || [],
        links: rawPayload.links || [],
        layout: rawPayload.layout || {}
    };

    payload.nodes = payload.nodes.map(function(node) {
        return {
            key: node.key,
            nameKey: node.name_key,
            label: node.label,
            valueKg: node.value_kg,
            depth: node.depth,
            color: node.color,
            tooltipHtml: node.tooltip_html
        };
    });
    payload.links = payload.links.map(function(link) {
        return {
            sourceKey: link.source_key,
            targetKey: link.target_key,
            sourceNameKey: link.source_name_key,
            targetNameKey: link.target_name_key,
            value: link.value,
            valueKg: link.value_kg,
            color: link.color,
            tooltipHtml: link.tooltip_html
        };
    });
    payload.layout = {
        leftPaddingPx: payload.layout.left_padding_px,
        rightPaddingPx: payload.layout.right_padding_px
    };

    var chart = echarts.init(plotEl, null, { renderer: 'canvas' });
    chart.setOption(buildEchartsOption(payload));
    plotEl.__sankeyChart = chart;

    if (typeof ResizeObserver !== 'undefined') {
        plotEl.__sankeyResizeObserver = new ResizeObserver(function() { chart.resize(); });
        plotEl.__sankeyResizeObserver.observe(plotEl);
    }
}

function renderSankeyPlots(rootEl) {
    var root = rootEl || document;
    if (!root.querySelectorAll) return;
    root.querySelectorAll('[id^="sankey-plot-"][data-sankey]').forEach(renderSankeyPlot);
}

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
    disposeSankeyPlot(plotEl);
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
    var fieldName = type === 'exclude' ? 'excluded_types' : 'skipped_columns';
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

// Dispose old chart instance before HTMX replaces a specific diagram area
document.body.addEventListener('htmx:beforeSwap', function(event) {
    var target = event.detail.target;
    if (!target) return;
    if (target.id && target.id.startsWith('sankey-diagram-area-')) {
        var plots = target.querySelectorAll('[id^="sankey-plot-"]');
        for (var i = 0; i < plots.length; i++) { disposeSankeyPlot(plots[i]); }
    }
});

// Scroll new cards into view, initialise Bootstrap tooltips, and render ECharts after HTMX settles
document.body.addEventListener('htmx:afterSettle', function(event) {
    var el = event.detail.elt;
    renderSankeyPlots(el);
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

document.addEventListener('DOMContentLoaded', function() {
    renderSankeyPlots(document);
});

if (typeof module !== 'undefined') {
    module.exports = {
        buildEchartsOption,
        getSankeyLayout,
        estimateSankeyRightPadding,
        disposeSankeyPlot,
        renderSankeyPlot,
        renderSankeyPlots,
        sankeyToggleChip,
        sankeyToggleSettings,
        sankeyToggleAdvanced,
        sankeyRemoveCard
    };
}
