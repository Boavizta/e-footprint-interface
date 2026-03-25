# Refactor layout to use flexbox instead of computed CSS variable heights

## Context

The layout uses a cascade of CSS variables (`--model-height`, `--model-canva-calculated-height`, `--list-object-calculated-height`, `--result-panel-opened`) computed from individual component heights. Changing any one variable breaks dependents. JS also dynamically mutates these variables to open/close the result panel. This is fragile and caused bugs when we merged the navbar+toolbar on mobile.

**Goal:** Replace computed height variables with a flexbox column layout where the browser automatically distributes remaining space. Hiding/showing elements (navbar, toolbar) will automatically reclaim/consume space with zero JS height manipulation.

## New layout model

```
body (height: 100dvh, flex column, overflow: hidden)
  ├─ navbar          (flex: 0 0 auto — intrinsic height, hidden on mobile)
  ├─ loading-bar     (flex: 0 0 auto — 2px)
  └─ main            (flex: 1 1 0, min-height: 0, flex column, overflow: hidden)
      ├─ toolbar     (flex: 0 0 auto — intrinsic height)
      └─ model-builder-page (flex: 1 1 0, min-height: 0, flex row, position: relative)
           ├─ canvas-scrollable-area  (height: 100%, overflow: auto)
           ├─ sidePanel               (width-based, stretches to parent height)
           └─ panel-result-btn        (position: absolute, bottom: 0)
```

No height calculations needed — flex distributes remaining space automatically.

## Files to modify

### 1. `theme/static/scss/custom.scss`

**Remove these computed variables** from `:root`:
- `--model-height`
- `--model-canva-calculated-height`
- `--list-object-calculated-height`
- `--result-panel-opened`
- `--result-content-offset`
- `--home-page-height`
- `--margin-padding-model`
- `--toolbar-height` (no longer needed for calculations)
- `--navbar-height` (no longer needed for calculations — navbar uses `d-none d-xl-flex`)

**Keep** (used for their own elements only, not for calculations):
- `--full-height` — used on body and as a reference for fixed-position elements
- `--loading-bar-height` — used by `#loading-bar`
- `--open-result-btn` — used by `#btn-open-panel-result` own height

**Add flex styles:**

```scss
body {
    /* add to existing body rule */
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

#main-content-block {
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

#toolbar-nav {
    flex: 0 0 auto;
}

#model-builder-page {
    flex: 1 1 0;
    min-height: 0;
    /* keep: position: relative, overflow-x: hidden, width: 100vw */
    /* REMOVE: height: var(--model-height) */
}
```

**Replace height rules on child elements:**

| Element | Current | New |
|---------|---------|-----|
| `#main-content-block` (line 141) | `height: auto` | `flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden;` |
| `#model-builder-page` (line 448) | `height: var(--model-height)` | `flex: 1 1 0; min-height: 0;` |
| `.scrollable-area` (line 177) | `height: var(--model-canva-calculated-height)` | `height: 100%;` (stretches via flex-row cross-axis) |
| `#model-canva` (line 635) | `height: var(--model-canva-calculated-height)` | `min-height: 100%;` |
| `.list-object-efootprint` (line 455) | `min-height: var(--list-object-calculated-height)` | Remove entirely (content-driven height) |
| `#sidePanel` (line 460) | `height: var(--model-canva-calculated-height)` | Remove — flex stretch handles desktop. Mobile (fixed): `height: var(--full-height); top: 0;` |
| `#panel-result-btn` (line 465) | `height: var(--open-result-btn)` | Keep as-is (50px closed state) |
| `.navbar` (line 276) | `height: var(--navbar-height)` | Remove — intrinsic height via flex auto |
| `.home-page` desktop (line 758) | `height: var(--home-page-height)` | Remove |
| `#panel-result-btn, #result-block` mobile (line 743) | `max-height: var(--result-panel-opened)` | `max-height: 100%` |

**Remove from desktop breakpoint** `@media (min-width: 1200px)`:
- `--navbar-height: 50px`
- `--toolbar-height: 48px`
- `--result-content-offset: 120px`

### 2. `theme/static/scripts/hammer_utils.js`

Simplify dramatically — no more CSS variable manipulation or `getComputedStyle` reading:

```javascript
function enterResultFullscreen() {
    if (window.innerWidth >= 1200) return;
    var toolbar = document.getElementById("toolbar-nav");
    if (toolbar) toolbar.style.display = "none";
}

function exitResultFullscreen() {
    var toolbar = document.getElementById("toolbar-nav");
    if (toolbar) toolbar.style.display = "";
}

function displayPanelResult() {
    enterResultFullscreen();
    var panel = document.getElementById("panel-result-btn");
    var btn = document.getElementById("btn-open-panel-result");
    var resultDiv = document.getElementById("result-block");

    panel.style.height = "100%";
    resultDiv.style.height = "100%";

    if (document.getElementById("sidePanel").classList.contains("d-none")) {
        panel.classList.add("w-100");
    } else {
        panel.classList.remove("w-100");
        panel.classList.add("result-width");
    }
    btn.style.display = "none";
}

function hidePanelResult() {
    exitResultFullscreen();
    var panel = document.getElementById("panel-result-btn");
    var btn = document.getElementById("btn-open-panel-result");
    var resultDiv = document.getElementById("result-block");

    panel.style.height = "";
    resultDiv.innerHTML = "";
    resultDiv.style.height = "";

    if (document.getElementById("sidePanel").classList.contains("d-none")) {
        resultDiv.classList.remove("w-100");
    } else {
        resultDiv.classList.remove("result-width");
    }
    btn.style.display = "block";
}

// initHammer() unchanged
```

### 3. `model_builder/templates/model_builder/result/result_panel.html`

- Remove inline `style="max-height: calc(var(--result-panel-opened) - var(--result-content-offset))"` from `#graph-block` and `#source-block`
- Make the result panel inner wrapper a flex column so content fills available space:

```scss
/* Add to custom.scss */
#result-block > div {
    display: flex;
    flex-direction: column;
    height: 100%;
}

#graph-block, #source-block {
    flex: 1 1 0;
    min-height: 0;
    overflow: auto;
}
```

### 4. `theme/templates/home.html`

- Remove inline `style="height: var(--home-page-height);"` from `#home-page-container` (line 2)
- Add CSS:

```scss
#home-page-container {
    flex: 1 1 0;
    min-height: 0;
    overflow: auto;
}
```

### 5. `theme/templates/navbar.html`

No changes needed — already hidden on mobile via `d-none d-xl-flex`. Flex `auto` sizing picks up its intrinsic height on desktop.

### 6. `model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html`

No further changes needed beyond what was already done (logo icon on mobile, `id="toolbar-nav"`).

## What stays the same

- Side panel `position: fixed` on mobile/tablet — independent of flex
- Result panel `position: absolute; bottom: 0` inside model-builder-page — overlays canvas
- Desktop visual layout — unchanged
- All template structure/nesting — no HTML restructuring needed
- `initHammer()` — unchanged
- Side panel open/close logic in `side_panel_utils.js` — unchanged (manages classes, not heights)

## Why this is better

| Before | After |
|--------|-------|
| 7 computed CSS variables cascading from each other | 0 computed variables |
| JS reads/writes CSS variables to open result panel | JS only toggles `display` and `height: 100%` |
| Changing one component height requires updating multiple variables | Browser auto-distributes space |
| Mobile/desktop need different variable values via breakpoints | Same flex rules work at all sizes |
| Hiding navbar requires JS to update `--navbar-height` to 0 | Hiding navbar via `display:none` auto-reclaims space |

## Verification

1. Compile SCSS: `npx sass theme/static/scss/main.scss:theme/static/css/bs_main.css --load-path=node_modules/bootstrap/scss`
2. Run server: `python manage.py runserver`
3. Test on Chrome DevTools mobile emulation:
   - Portrait: toolbar visible, canvas scrollable, result panel opens/closes correctly
   - Landscape: same, Sankey diagrams get most of the screen
   - Result panel open: toolbar hidden, full-height results, "Back to model" button works
   - Close and reopen results: no height bugs
4. Test desktop (>= 1200px): both navbar + toolbar visible, side panel shares space, result panel opens
5. Test home page: fills viewport, scrolls if content overflows