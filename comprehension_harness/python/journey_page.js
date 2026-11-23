/**
 * What a journey run needs IN THE PAGE (`journey.py`). Added as an init script, so it runs before the app in
 * every document of the page and leaves two globals: `__jt`, the recorder's state, and `__jtLib`, the
 * functions `journey.py` calls through `page.evaluate`.
 *
 * Actions: capture-phase listeners on the document record each trusted click, change, submit and Enter /
 * Escape / Space key with the control it landed on, and hand it at once to the exposed binding `__jtEmit`.
 * Each action takes the next number of a counter kept in the cookie `jt_action`, so the counter survives a
 * navigation and every request the page sends afterwards carries the number of the action before it. That is
 * how the server's `narrate` and `event` calls are filed under the action that caused them: the listener runs
 * in the capture phase, before the handler that sends the request.
 *
 * `capturePage`: a screen as text. The DOM is serialised by a walker of its own rather than `outerHTML`,
 * because what makes two runs of an unchanged app differ is decided node by node:
 *
 *  - `script`, `style`, `link`, `noscript`, `template`, `base` and comments are dropped; every stylesheet's
 *    rules are returned once, apart, as one text the captures of a run share;
 *  - a `blob:` URL (minted per page load) is written as the bare `blob:`; `audio` / `video` lose their `src`,
 *    kept as `data-capture-src`;
 *  - an `img` is inlined as a data URI, a `canvas` becomes an `img` of its pixels;
 *  - what lives on the element and not in its attributes is written down as attributes: a field's value /
 *    checked, the focused element (`data-capture-focus`), a scrolled box's offset (`data-capture-scroll`);
 *  - the recorder's own `data-jt-*` stamps are left out.
 *
 * One tag per line, and the line break sits INSIDE the tag (`<p class="x"⏎>`), never between two nodes:
 * whitespace between inline elements is layout. A text diff of two captures is then a diff of tags.
 */
(() => {
  if (window.__jt) return;

  /** Controls as the DOM declares them; the accessibility tree decides their role and name afterwards. */
  const CONTROL_SELECTOR = [
    'a[href]', 'button', 'input:not([type="hidden"])', 'select', 'textarea', 'summary',
    '[role="button"]', '[role="link"]', '[role="tab"]', '[role="checkbox"]', '[role="switch"]',
    '[role="slider"]', '[role="menuitem"]', '[role="radio"]', '[role="option"]', '[contenteditable="true"]',
  ].join(',');

  const ACTION_COOKIE = /(?:^|; )jt_action=(\d+)/;
  /** Takes the next action number: what the page sends from here on is this action's. */
  const next = () => {
    const found = ACTION_COOKIE.exec(document.cookie);
    const seq = (found ? Number(found[1]) : 0) + 1;
    document.cookie = `jt_action=${seq}; path=/; SameSite=Lax`;
    return seq;
  };

  const jt = { controls: new WeakMap(), screen: 0, next };
  window.__jt = jt;

  const ownText = (el) => (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120);

  for (const type of ['click', 'change', 'submit', 'keydown']) {
    document.addEventListener(type, (ev) => {
      if (!ev.isTrusted) return;
      const key = ev instanceof KeyboardEvent ? ev.key : null;
      if (type === 'keydown' && key !== 'Enter' && key !== 'Escape' && key !== ' ') return;
      const target = ev.target instanceof Element ? ev.target : null;
      if (!target) return;
      // The stamped control the event landed in (a control, or a clickable-looking box), else the nearest control.
      let el = target;
      while (el && !jt.controls.has(el)) el = el.parentElement;
      const control = el || target.closest(CONTROL_SELECTOR) || target;
      const emit = window.__jtEmit;
      if (!emit) return;
      emit([{
        kind: 'action', seq: next(), type, key,
        control: jt.controls.has(control) ? jt.controls.get(control) : null,
        screen: jt.screen,
        text: ownText(control),
        title: control.getAttribute('title'),
        ariaLabel: control.getAttribute('aria-label'),
        tag: control.localName,
        url: location.pathname + location.search + location.hash,
      }]);
    }, true);
  }

  /** Before a capture: fonts in, every finite animation and transition at its end state. Returns how many
   *  animations are endless and still run. The caller lets two frames pass after it, then calls `capturePage`. */
  const settlePage = async () => {
    await document.fonts.ready;
    let running = 0;
    for (const a of document.getAnimations()) {
      const timing = a.effect && a.effect.getComputedTiming();
      if (timing && timing.endTime !== Infinity && Number.isFinite(Number(timing.endTime))) {
        try { a.finish(); } catch { running += 1; }
      } else {
        running += 1;
      }
    }
    return running;
  };

  /** Two frames of the page, on its own clock, which a case may have paused (`pause_clock`). */
  const twoFrames = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));

  const capturePage = async (args) => {
    const SKIP = new Set(['script', 'style', 'link', 'noscript', 'template', 'base']);
    const VOID = new Set(['area', 'br', 'col', 'embed', 'hr', 'img', 'input', 'meta', 'param', 'source', 'track', 'wbr']);
    const text = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const attr = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
    const counts = { elements: 0, images: 0, canvases: 0, media: 0, blobUrls: 0, runningAnimations: args.runningAnimations };

    const dataUri = async (url) => {
      try {
        const blob = await (await fetch(url)).blob();
        return await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(reader.error);
          reader.readAsDataURL(blob);
        });
      } catch {
        return url;
      }
    };

    // The stylesheets, in cascade order. A `url(…)` is resolved against its own sheet, then inlined.
    let css = '';
    let unreadableSheets = 0;
    for (const sheet of Array.from(document.styleSheets)) {
      let rules;
      try { rules = sheet.cssRules; } catch { unreadableSheets += 1; continue; }
      const base = sheet.href || location.href;
      let sheetCss = '';
      for (const rule of Array.from(rules)) sheetCss += `${rule.cssText}\n`;
      const urls = new Set();
      sheetCss.replace(/url\((["']?)(?!data:)([^)"']+)\1\)/g, (_m, _q, u) => { urls.add(u); return ''; });
      for (const u of urls) {
        if (u.startsWith('#')) continue;
        const inlined = await dataUri(new URL(u, base).href);
        sheetCss = sheetCss.split(u).join(inlined);
      }
      css += sheetCss;
    }
    counts.unreadableSheets = unreadableSheets;

    const images = new Map();
    for (const img of Array.from(document.images)) {
      const src = img.currentSrc || img.src;
      if (src && !src.startsWith('data:')) images.set(img, await dataUri(src));
    }

    const focused = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;

    const out = [];
    const walk = (node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        out.push(text(node.data));
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      const el = node;
      let tag = el.localName;
      if (SKIP.has(tag)) return;
      counts.elements += 1;

      const attrs = new Map();
      for (const a of Array.from(el.attributes)) {
        if (a.name.startsWith('data-jt-')) continue;
        let value = a.value;
        if (value.startsWith('blob:')) { value = 'blob:'; counts.blobUrls += 1; }
        attrs.set(a.name, value);
      }
      if (tag === 'img') {
        counts.images += 1;
        const inlined = images.get(el);
        if (inlined) attrs.set('src', inlined);
        attrs.delete('srcset');
      }
      if (tag === 'audio' || tag === 'video') {
        counts.media += 1;
        const src = attrs.get('src');
        if (src !== undefined) { attrs.delete('src'); attrs.set('data-capture-src', src); }
      }
      if (tag === 'canvas') {
        counts.canvases += 1;
        try { attrs.set('src', el.toDataURL()); } catch { /* tainted: left empty */ }
        attrs.set('data-capture-was', 'canvas');
        tag = 'img';
      }
      if (el instanceof HTMLInputElement) {
        if (el.type === 'checkbox' || el.type === 'radio') { if (el.checked) attrs.set('checked', ''); else attrs.delete('checked'); }
        else if (el.type !== 'file' && el.type !== 'password') attrs.set('value', el.value);
      }
      if (el instanceof HTMLOptionElement) { if (el.selected) attrs.set('selected', ''); else attrs.delete('selected'); }
      if (el === focused) attrs.set('data-capture-focus', '');
      if (el.scrollTop !== 0 || el.scrollLeft !== 0) attrs.set('data-capture-scroll', `${Math.round(el.scrollTop)},${Math.round(el.scrollLeft)}`);
      if (el === document.documentElement) attrs.set('data-journey-screen', args.address);

      out.push(`<${tag}`);
      for (const [name, value] of attrs) out.push(value === '' ? ` ${name}` : ` ${name}="${attr(value)}"`);
      out.push('\n>');
      if (VOID.has(tag)) return;

      if (tag === 'head') {
        const meta = document.querySelector('meta[name="viewport"]');
        const viewport = (meta && meta.getAttribute('content')) || 'width=device-width, initial-scale=1';
        out.push(`<meta charset="utf-8"\n><meta name="viewport" content="${attr(viewport)}"\n><title\n>${text(args.title)}</title\n><link rel="stylesheet" href="__JOURNEY_CSS__"\n>`);
      } else if (el instanceof HTMLTextAreaElement) {
        out.push(text(el.value));
      } else {
        for (const child of Array.from(el.childNodes)) walk(child);
      }
      out.push(`</${tag}\n>`);
    };
    walk(document.documentElement);

    return { html: `<!doctype html>\n${out.join('')}\n`, css, counts, url: location.pathname + location.search + location.hash };
  };

  /** The visible controls of the page, stamped `data-jt-c="<i>"` so `journey.py` can ask Playwright for each
   *  one's accessible role and name, and remembered so an action that lands on one names it by index. */
  const listControls = () => {
    for (const stale of Array.from(document.querySelectorAll('[data-jt-c]'))) stale.removeAttribute('data-jt-c');
    const visible = (el) => {
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && el.checkVisibility({ visibilityProperty: true });
    };
    const controls = Array.from(document.querySelectorAll(CONTROL_SELECTOR)).filter(visible);
    const known = new Set(controls);
    // Clickable-looking elements that are no control: the innermost `cursor: pointer` boxes outside any control.
    const pointers = Array.from(document.body.querySelectorAll('*')).filter((el) => {
      if (el.closest(CONTROL_SELECTOR) || !visible(el)) return false;
      if (getComputedStyle(el).cursor !== 'pointer') return false;
      const parent = el.parentElement;
      return !parent || getComputedStyle(parent).cursor !== 'pointer';
    });
    const all = [...controls, ...pointers].sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
    jt.controls = new WeakMap();
    jt.screen += 1;
    return all.map((el, i) => {
      el.setAttribute('data-jt-c', String(i));
      jt.controls.set(el, i);
      return {
        i,
        tag: el.localName,
        text: ownText(el),
        title: el.getAttribute('title'),
        ariaLabel: el.getAttribute('aria-label'),
        testId: el.getAttribute('data-testid'),
        disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
        inDialog: el.closest('[role="dialog"]') !== null,
        pointerOnly: !known.has(el),
      };
    });
  };

  const clearControlStamps = () => {
    for (const el of Array.from(document.querySelectorAll('[data-jt-c]'))) el.removeAttribute('data-jt-c');
  };

  window.__jtLib = { settlePage, twoFrames, capturePage, listControls, clearControlStamps };
})();
