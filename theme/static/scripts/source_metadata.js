/* Source metadata widgets — confidence badge dropdown and inline source editor.
   All interactions are local; values are written into hidden inputs that ride
   the existing edit form's Save button.

   Behavior is wired via a single delegated dispatcher: templates declare intent
   with `data-action="..."`, and only one name escapes to `window`
   (the reset listener via custom DOM event). See conventions.md → JavaScript. */
(function () {
    function _confWrap(fieldId) {
        return document.querySelector(`.confidence-wrap[data-field-id="${CSS.escape(fieldId)}"]`);
    }

    function _editor(fieldId) {
        return document.getElementById("editor-" + fieldId);
    }

    function _form(el) {
        return el.closest("form");
    }

    function _hiddenInput(fieldId, suffix) {
        return document.getElementById(`${fieldId}__${suffix}`);
    }

    function _fieldIdOf(target) {
        const el = target.closest("[data-field-id]");
        return el ? el.dataset.fieldId : null;
    }

    /* ===== Confidence badge ===== */

    function applyConfidenceToBadge(btn, level) {
        btn.classList.remove("conf-none", "conf-low", "conf-medium", "conf-high");
        btn.classList.add("conf-" + level);
        btn.dataset.level = level;
        const bars = btn.querySelector(".bars");
        bars.classList.remove("bars-low", "bars-medium", "bars-high");
        if (level !== "none") bars.classList.add("bars-" + level);
    }

    function closeAllConfidenceMenus(except) {
        document.querySelectorAll(".confidence-menu.open").forEach(m => {
            if (m !== except) m.classList.remove("open");
        });
    }

    function toggleConfidenceMenu(btn) {
        const menu = ensureConfidenceMenu(btn);
        if (!menu) return;
        const wasOpen = menu.classList.contains("open");
        closeAllConfidenceMenus();
        if (!wasOpen) {
            positionConfidenceMenu(btn, menu);
            menu.classList.add("open");
        }
    }

    function ensureConfidenceMenu(btn) {
        if (btn.nextElementSibling?.classList?.contains("confidence-menu")) {
            return btn.nextElementSibling;
        }
        const level = btn.dataset.level || "none";
        const template = document.getElementById("source-table-confidence-menu-template");
        if (!template) return null;
        const menu = template.content.firstElementChild.cloneNode(true);
        syncConfidenceMenuSelection(menu, level);
        btn.insertAdjacentElement("afterend", menu);
        return menu;
    }

    function syncConfidenceMenuSelection(menu, level) {
        menu.querySelectorAll(".menu-item").forEach(item => {
            item.classList.toggle("selected", item.dataset.level === level);
        });
    }

    /* Flip the dropdown above the badge if the row is too close to the bottom of its
       scroll container — otherwise the menu gets clipped (#source-block has overflow-y: auto). */
    function positionConfidenceMenu(btn, menu) {
        menu.classList.remove("menu-up");
        const btnRect = btn.getBoundingClientRect();
        const scroller = btn.closest("#source-block");
        const containerBottom = scroller
            ? scroller.getBoundingClientRect().bottom
            : window.innerHeight;
        const MENU_HEIGHT_ESTIMATE = 200;
        if (btnRect.bottom + MENU_HEIGHT_ESTIMATE > containerBottom) {
            menu.classList.add("menu-up");
        }
    }

    function setConfidence(menuItem, level) {
        const menu = menuItem.closest(".confidence-menu");
        const wrap = menu.closest(".confidence-wrap");
        const btn = menu.previousElementSibling;
        applyConfidenceToBadge(btn, level);
        menu.querySelectorAll(".menu-item").forEach(i => i.classList.remove("selected"));
        menuItem.classList.add("selected");
        menu.classList.remove("open");

        const fieldId = wrap.dataset.fieldId;
        const hidden = _hiddenInput(fieldId, "confidence");
        const stored = (level === "none") ? "" : level;
        if (hidden) hidden.value = stored;

        if (wrap.dataset.autosaveUrl) {
            autosaveConfidence(wrap, stored);
        } else if (typeof tagFormAsModified === "function") {
            tagFormAsModified();
        }
    }

    /* Inline (no-form) confidence edit: POST just the new confidence field.
       The badge is already updated locally; _apply_metadata patches in place,
       so source/comment aren't touched and no table refresh is needed. */
    function autosaveConfidence(wrap, confidenceValue) {
        const hidden = wrap.querySelector('input[type="hidden"]');
        if (!hidden || !hidden.name) return;
        const ds = wrap.dataset;
        htmx.ajax("POST", ds.autosaveUrl,
            {values: {[hidden.name]: confidenceValue}, swap: "none"});
    }

    function resetConfidenceForField(inputId) {
        const wrap = _confWrap(inputId);
        if (!wrap) return;
        const badge = wrap.querySelector(".confidence-badge");
        if (!badge || badge.dataset.level === "none") return;

        applyConfidenceToBadge(badge, "none");
        const menu = wrap.querySelector(".confidence-menu");
        if (menu) {
            menu.querySelectorAll(".menu-item").forEach(i => i.classList.remove("selected"));
            const noneItem = menu.querySelector('[data-level="none"]');
            if (noneItem) noneItem.classList.add("selected");
        }
        const hidden = _hiddenInput(inputId, "confidence");
        if (hidden) hidden.value = "";

        badge.classList.add("confidence-just-reset");
        setTimeout(() => badge.classList.remove("confidence-just-reset"), 1400);
    }

    /* When the user edits an input whose source is the e-footprint hypothesis
       sentinel, flip the source to the user-data sentinel: the value is no
       longer the canonical guess, it's the user's. Only triggers on the
       hypothesis sentinel — once the user has picked any other source, we
       don't second-guess them. */
    function swapHypothesisToUserDataForField(inputId) {
        const sourceIdInput = _hiddenInput(inputId, "source_id");
        if (!sourceIdInput || sourceIdInput.value !== "hypothesis") return;
        const editor = _editor(inputId);
        if (!editor) return;
        const userDataOpt = editor.querySelector('.source-editor-select option[value="user_data"]');
        if (!userDataOpt) return;
        const name = userDataOpt.dataset.name || userDataOpt.text;
        const link = userDataOpt.dataset.link || "";
        sourceIdInput.value = "user_data";
        _hiddenInput(inputId, "source_name").value = name;
        _hiddenInput(inputId, "source_link").value = link;
        const commentInput = _hiddenInput(inputId, "comment");
        _updateSourceDisplay(inputId, name, link, commentInput ? commentInput.value : "");
        editor.querySelector(".source-editor-select").value = "user_data";
    }

    /* ===== Source editor ===== */

    function openSourceEditor(fieldId) {
        document.querySelectorAll(".source-editor.open").forEach(ed => {
            if (ed.id !== "editor-" + fieldId) ed.classList.remove("open");
        });
        const editor = _editor(fieldId);
        if (!editor) return;
        _populateEditorFromHidden(fieldId);
        editor.classList.add("open");
    }

    function cancelSourceEditor(fieldId) {
        const editor = _editor(fieldId);
        if (!editor) return;
        _populateEditorFromHidden(fieldId);
        editor.classList.remove("open");
    }

    function applySourceEditor(fieldId) {
        const editor = _editor(fieldId);
        if (!editor) return;
        const select = editor.querySelector(".source-editor-select");
        const customName = editor.querySelector(".source-editor-custom-name");
        const customLink = editor.querySelector(".source-editor-custom-link");
        const comment = editor.querySelector(".source-editor-comment");

        let sourceId, sourceName, sourceLink;
        if (select.value === "__custom__") {
            sourceName = customName.value.trim();
            sourceLink = customLink.value.trim();
            const priorId = _hiddenInput(fieldId, "source_id").value;
            // Reuse the prior id only if the user is still editing the same custom
            // source (its id is set and not in the listed options); otherwise mint
            // a fresh one so a switch from a listed source to a custom one can't
            // overwrite the listed source's identity on the server.
            const priorIdIsListed = Array.from(select.options).some(
                opt => opt.value !== "__custom__" && opt.value === priorId);
            sourceId = (priorId && !priorIdIsListed) ? priorId : crypto.randomUUID().slice(0, 6);
            _broadcastNewSource(editor, sourceId, sourceName, sourceLink);
        } else {
            const opt = select.options[select.selectedIndex];
            sourceId = opt.value;
            sourceName = opt.dataset.name || opt.text;
            sourceLink = opt.dataset.link || "";
        }

        _hiddenInput(fieldId, "source_id").value = sourceId;
        _hiddenInput(fieldId, "source_name").value = sourceName;
        _hiddenInput(fieldId, "source_link").value = sourceLink;
        _hiddenInput(fieldId, "comment").value = comment.value;

        // In the source-table row editor, Apply also submits the wrapping form (one click ships
        // the change). In the side panel, the editor lives inside a much bigger form — leave
        // submission to the user's Save click.
        const rowForm = editor.closest("form[data-action='source-table-row-edit']");
        if (rowForm) {
            htmx.trigger(rowForm, "submit");
            return;
        }

        _updateSourceDisplay(fieldId, sourceName, sourceLink, comment.value);
        editor.classList.remove("open");
        if (typeof tagFormAsModified === "function") tagFormAsModified();
    }

    /* Each freshly-rendered in-form source editor (table row editor) needs the select / custom
       fields synced to its hidden inputs — same job _populateEditorFromHidden does on each
       openSourceEditor call in the side panel, but the table editor is rendered already-open. */
    function initInFormSourceEditorsIn(root) {
        (root || document).querySelectorAll(
            "form[data-action='source-table-row-edit'] .source-editor"
        ).forEach(editor => _populateEditorFromHidden(editor.dataset.fieldId));
    }

    function handleSourceSelect(select, fieldId) {
        const custom = document.getElementById("custom-fields-" + fieldId);
        if (select.value === "__custom__") custom.classList.add("open");
        else custom.classList.remove("open");
    }

    function checkCollision(input, fieldId) {
        const editor = _editor(fieldId);
        const notice = document.getElementById("collision-" + fieldId);
        if (!editor || !notice) return;
        const select = editor.querySelector(".source-editor-select");
        const typed = input.value.trim().toLowerCase();
        const hit = typed.length > 0 && Array.from(select.options).some(
            opt => opt.value !== "__custom__" && (opt.dataset.name || opt.text).toLowerCase() === typed);
        notice.classList.toggle("visible", hit);
    }

    function _populateEditorFromHidden(fieldId) {
        const editor = _editor(fieldId);
        const select = editor.querySelector(".source-editor-select");
        const customName = editor.querySelector(".source-editor-custom-name");
        const customLink = editor.querySelector(".source-editor-custom-link");
        const comment = editor.querySelector(".source-editor-comment");
        const customWrap = document.getElementById("custom-fields-" + fieldId);

        const sourceId = _hiddenInput(fieldId, "source_id").value;
        const sourceName = _hiddenInput(fieldId, "source_name").value;
        const sourceLink = _hiddenInput(fieldId, "source_link").value;
        comment.value = _hiddenInput(fieldId, "comment").value;

        const matchingOption = Array.from(select.options).find(
            opt => opt.value !== "__custom__" && opt.value === sourceId);
        if (matchingOption) {
            select.value = sourceId;
            customWrap.classList.remove("open");
            customName.value = "";
            customLink.value = "";
        } else {
            select.value = "__custom__";
            customWrap.classList.add("open");
            customName.value = sourceName;
            customLink.value = sourceLink;
        }
    }

    function _updateSourceDisplay(fieldId, name, link, comment) {
        const wrap = document.getElementById("source-" + fieldId);
        if (!wrap) return;
        const display = wrap.querySelector(".source-name-display");
        if (display) {
            if (link) {
                display.innerHTML = `<a href="${_escapeHtml(link)}" target="_blank" class="sources-label" onclick="event.stopPropagation();">${_escapeHtml(name)}</a>`;
            } else {
                display.innerHTML = `<span class="sources-label">${_escapeHtml(name)}</span>`;
            }
        }
        const commentLine = wrap.querySelector(".comment-line");
        if (commentLine) {
            commentLine.classList.toggle("d-none", !comment);
            const text = commentLine.querySelector(".comment-text");
            if (text) {
                text.textContent = comment;
                text.dataset.bsTitle = comment;
                // Bootstrap caches the title at init time; updating dataset alone
                // leaves the live tooltip stale. Refresh the cached content too.
                if (window.bootstrap && bootstrap.Tooltip) {
                    bootstrap.Tooltip.getInstance(text)?.setContent({ ".tooltip-inner": comment });
                }
            }
        }
    }

    function _escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, ch => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[ch]));
    }

    /* When a custom source is applied, inject it into every other source <select>
       in the same form so siblings can pick it (and end up sharing the same id). */
    function _broadcastNewSource(originatingEditor, id, name, link) {
        const form = _form(originatingEditor);
        if (!form) return;
        form.querySelectorAll(".source-editor").forEach(other => {
            if (other === originatingEditor) return;
            const select = other.querySelector(".source-editor-select");
            if (!select) return;
            const existing = Array.from(select.options).find(
                opt => opt.value === id);
            if (existing) {
                existing.dataset.name = name;
                existing.dataset.link = link;
                existing.text = name;
                return;
            }
            const opt = document.createElement("option");
            opt.value = id;
            opt.text = name;
            opt.dataset.name = name;
            opt.dataset.link = link;
            const customOpt = Array.from(select.options).find(o => o.value === "__custom__");
            if (customOpt) select.insertBefore(opt, customOpt);
            else select.appendChild(opt);
        });
    }

    /* ===== Delegated dispatchers ===== */

    document.addEventListener("click", e => {
        if (!e.target.closest(".confidence-badge") && !e.target.closest(".confidence-menu")) {
            closeAllConfidenceMenus();
        }
        const target = e.target.closest("[data-action]");
        if (!target) return;
        const action = target.dataset.action;
        const fieldId = _fieldIdOf(target);
        switch (action) {
            case "toggle-confidence-menu":
                toggleConfidenceMenu(target);
                break;
            case "set-confidence":
                setConfidence(target, target.dataset.level);
                break;
            case "open-source-editor":
                openSourceEditor(fieldId);
                break;
            case "cancel-source-editor":
                cancelSourceEditor(fieldId);
                break;
            case "apply-source-editor":
                applySourceEditor(fieldId);
                break;
            case "toggle-comment-expand":
                target.classList.toggle("expanded");
                break;
        }
    });

    document.addEventListener("input", e => {
        const target = e.target.closest("[data-action]");
        if (!target) return;
        if (target.dataset.action === "check-source-collision") {
            checkCollision(target, _fieldIdOf(target));
        }
    });

    document.addEventListener("change", e => {
        const target = e.target.closest("[data-action]");
        if (!target) return;
        if (target.dataset.action === "source-select-change") {
            handleSourceSelect(target, _fieldIdOf(target));
        }
    });

    document.addEventListener("keydown", e => {
        if (e.key !== "Enter" && e.key !== " ") return;
        const target = e.target.closest("[data-action]");
        if (!target) return;
        if (target.dataset.action === "open-source-editor"
            || target.dataset.action === "toggle-comment-expand") {
            e.preventDefault();
            target.click();
        }
    });

    /* Pick up freshly-rendered in-form source editors after the source table reloads
       (and once on initial DOMContentLoaded for the no-htmx case). Idempotent. */
    document.addEventListener("htmx:load", e => initInFormSourceEditorsIn(e.target));
    document.addEventListener("DOMContentLoaded", () => initInFormSourceEditorsIn());

    /* After the row form's POST succeeds, refresh the source table — the re-render
       collapses the row that submitted (no `show` class on the new markup). */
    document.addEventListener("htmx:afterRequest", e => {
        if (!e.detail.successful) return;
        const form = e.target.closest("form[data-action='source-table-row-edit']");
        if (!form) return;
        htmx.ajax("GET", form.dataset.sourceTableUrl, {target: "#source-block", swap: "innerHTML"});
    });

    /* Cross-module hook: dynamic_forms.js fires this when an input value changes,
       so we can react without sharing globals. Two reactions today: clear the
       confidence badge (per-value judgement) and swap the source from the
       hypothesis sentinel to user-data (so the value is owned by the user). */
    document.addEventListener("source-metadata:value-changed", e => {
        if (!e.target || !e.target.id) return;
        resetConfidenceForField(e.target.id);
        swapHypothesisToUserDataForField(e.target.id);
    });

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            applyConfidenceToBadge, toggleConfidenceMenu, setConfidence,
            openSourceEditor, cancelSourceEditor, applySourceEditor,
            handleSourceSelect, checkCollision,
            resetConfidenceForField, swapHypothesisToUserDataForField,
            autosaveConfidence,
            initInFormSourceEditorsIn,
        };
    }
})();
