(function () {
    "use strict";

    const FLOAT32_MAX = 3.4028234663852886e38;
    const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const PREVIEW_DEBOUNCE_MS = 300;

    function controlsIn(panel) {
        return panel.querySelectorAll("input, select, textarea, button");
    }

    function setPanelActive(panel, active) {
        panel.hidden = !active;
        controlsIn(panel).forEach(function (control) {
            control.disabled = !active;
        });
    }

    function selectedBuilder(root) {
        return root.querySelector("[data-builder-selector]")?.value
            || root.querySelector("[data-builder-panel]")?.dataset.builderPanel;
    }

    function previewScope(root) {
        return root.closest("form") || document;
    }

    function activatePreview(root) {
        previewScope(root).querySelectorAll("[data-timeseries-builder]").forEach(function (candidate) {
            const preview = candidate.querySelector("[data-timeseries-preview-column]");
            if (!preview) return;
            const active = candidate === root && selectedBuilder(candidate) === "weekly_pattern";
            preview.hidden = !active;
            candidate.classList.toggle("weekly-preview-active", active);
        });
    }

    function activateSelectedBuilder(root, preferPreview) {
        const selector = root.querySelector("[data-builder-selector]");
        const selected = selectedBuilder(root);
        root.querySelectorAll("[data-builder-panel]").forEach(function (panel) {
            setPanelActive(panel, panel.dataset.builderPanel === selected);
        });

        const previewColumn = root.querySelector("[data-timeseries-preview-column]");
        const scope = previewScope(root);
        const activeRoot = scope.querySelector("[data-timeseries-builder].weekly-preview-active");
        if (selected === "weekly_pattern" && (preferPreview || !activeRoot || selectedBuilder(activeRoot) !== "weekly_pattern")) {
            activatePreview(root);
        } else if (previewColumn && activeRoot !== root) {
            previewColumn.hidden = true;
            root.classList.remove("weekly-preview-active");
        } else if (selected !== "weekly_pattern") {
            if (previewColumn) previewColumn.hidden = true;
            root.classList.remove("weekly-preview-active");
            if (activeRoot === root) {
                const fallback = Array.from(scope.querySelectorAll("[data-timeseries-builder]")).find(function (candidate) {
                    return candidate !== root && selectedBuilder(candidate) === "weekly_pattern";
                });
                if (fallback) activatePreview(fallback);
            }
        }
        if (selector && selected !== "weekly_pattern") setControlError(selector, "");
        root.querySelectorAll("[data-weekly-pattern-editor]").forEach(function (editor) {
            if (editor.closest("[data-builder-panel]").hidden) {
                clearEditorErrors(editor);
                editor.querySelector("[data-weekly-pattern-payload]").value = JSON.stringify(serializeEditor(editor));
            } else {
                validateAndSync(editor);
            }
        });
    }

    function numericValue(input) {
        if (!input || input.value.trim() === "") return null;
        const value = Number(input.value);
        return Number.isFinite(value) && Math.abs(value) <= FLOAT32_MAX ? value : null;
    }

    function profileElements(editor) {
        return Array.from(editor.querySelectorAll("[data-weekly-profile]"));
    }

    function rangeElements(profile) {
        return Array.from(profile.querySelectorAll("[data-weekly-range]"));
    }

    function readRange(range) {
        return {
            start: numericValue(range.querySelector("[data-range-start]")),
            end: numericValue(range.querySelector("[data-range-end]")),
            value: numericValue(range.querySelector("[data-range-value]")),
        };
    }

    function setControlError(control, message) {
        control.setCustomValidity(message || "");
        control.classList.toggle("is-invalid", Boolean(message));
        control.setAttribute("aria-invalid", String(Boolean(message)));
    }

    function clearEditorErrors(editor) {
        editor.querySelectorAll("input, select").forEach(function (control) {
            setControlError(control, "");
        });
        editor.querySelectorAll(
            "[data-profile-name-error], [data-profile-days-error], [data-profile-baseline-error], [data-range-error]"
        )
            .forEach(function (element) {
                element.textContent = "";
                if (element.matches("[data-profile-days-error], [data-range-error]")) element.classList.add("d-none");
            });
        const general = editor.querySelector("[data-weekly-error]");
        general.textContent = "";
        general.classList.add("d-none");
    }

    function showGeneralError(editor, messages) {
        const uniqueMessages = Array.from(new Set(messages.filter(Boolean)));
        const general = editor.querySelector("[data-weekly-error]");
        general.textContent = uniqueMessages.join(" ");
        general.classList.toggle("d-none", uniqueMessages.length === 0);
        const validityAnchor = editor.closest("[data-timeseries-builder]")?.querySelector("[data-builder-selector]")
            || editor.querySelector("[data-profile-name]");
        if (validityAnchor) setControlError(validityAnchor, uniqueMessages.join(" "));
    }

    function validateRange(editor, range, otherRanges) {
        const authored = readRange(range);
        const startInput = range.querySelector("[data-range-start]");
        const endInput = range.querySelector("[data-range-end]");
        const valueInput = range.querySelector("[data-range-value]");
        let message = "";
        let controls = [];

        if (!Number.isInteger(authored.start) || authored.start < 0 || authored.start > 23) {
            message = "Start must be an integer from 0 to 23.";
            controls = [startInput];
        } else if (!Number.isInteger(authored.end) || authored.end < 1 || authored.end > 24) {
            message = "End must be an integer from 1 to 24.";
            controls = [endInput];
        } else if (authored.start >= authored.end) {
            message = "Start must be earlier than end.";
            controls = [startInput, endInput];
        } else if (authored.value === null) {
            message = "Value must be a finite number representable as float32.";
            controls = [valueInput];
        } else if (editor.dataset.canBeNegative !== "true" && authored.value < 0) {
            message = "Value must be zero or greater for this field.";
            controls = [valueInput];
        } else {
            const overlap = otherRanges.find(function (candidate) {
                if (candidate === range) return false;
                const other = readRange(candidate);
                return Number.isInteger(other.start) && Number.isInteger(other.end)
                    && authored.start < other.end && authored.end > other.start;
            });
            if (overlap) {
                const other = readRange(overlap);
                message = `Overlaps the ${String(other.start).padStart(2, "0")}:00–${String(other.end).padStart(2, "0")}:00 range.`;
                controls = [startInput, endInput];
            }
        }

        controls.forEach(function (control) { setControlError(control, message); });
        const errorElement = range.querySelector("[data-range-error]");
        errorElement.textContent = message;
        errorElement.classList.toggle("d-none", !message);
        return !message;
    }

    function firstFreeHour(profile) {
        const ranges = rangeElements(profile).map(readRange);
        if (ranges.some(function (range) {
            return !Number.isInteger(range.start) || !Number.isInteger(range.end)
                || range.start < 0 || range.end > 24 || range.start >= range.end;
        })) return null;

        ranges.sort(function (left, right) { return left.start - right.start; });
        let cursor = 0;
        for (const range of ranges) {
            if (range.start - cursor >= 1) return cursor;
            cursor = Math.max(cursor, range.end);
        }
        return 24 - cursor >= 1 ? cursor : null;
    }

    function updateButtons(editor) {
        const profiles = profileElements(editor);
        profiles.forEach(function (profile) {
            profile.querySelector("[data-action='remove-weekly-profile']").disabled = profiles.length === 1;
            const addRange = profile.querySelector("[data-action='add-weekly-range']");
            addRange.disabled = firstFreeHour(profile) === null;
        });
        editor.querySelector("[data-action='add-weekly-profile']").disabled = profiles.length >= 7;
    }

    function reindexEditor(editor) {
        const fieldId = editor.dataset.fieldWebId;
        profileElements(editor).forEach(function (profile, profileIndex) {
            profile.querySelector("[data-profile-legend]").textContent = `Profile ${profileIndex + 1}`;
            profile.querySelector("[data-action='remove-weekly-profile']").setAttribute(
                "aria-label", `Remove profile ${profileIndex + 1}`
            );
            const name = profile.querySelector("[data-profile-name]");
            const baseline = profile.querySelector("[data-profile-baseline]");
            const nameId = `${fieldId}__profile_${profileIndex}_name`;
            const nameErrorId = `${nameId}_error`;
            name.id = nameId;
            name.setAttribute("aria-describedby", nameErrorId);
            profile.querySelector("[data-profile-name-label]").htmlFor = nameId;
            profile.querySelector("[data-profile-name-error]").id = nameErrorId;
            name.dataset.errorPath = `profiles[${profileIndex}].name`;

            const daysLabelId = `${fieldId}__profile_${profileIndex}_days_label`;
            const daysErrorId = `${fieldId}__profile_${profileIndex}_days_error`;
            profile.querySelector("[data-profile-days-label]").id = daysLabelId;
            const daysGroup = profile.querySelector("[data-profile-days-group]");
            daysGroup.setAttribute("aria-labelledby", daysLabelId);
            daysGroup.setAttribute("aria-describedby", daysErrorId);
            profile.querySelector("[data-profile-days-error]").id = daysErrorId;
            let selectedDayIndex = 0;
            const dayLabels = profile.querySelectorAll("[data-profile-day-label]");
            profile.querySelectorAll("[data-profile-day]").forEach(function (day, dayIndex) {
                const dayId = `${fieldId}__profile_${profileIndex}_day_${dayIndex}`;
                day.id = dayId;
                dayLabels[dayIndex].htmlFor = dayId;
                delete day.dataset.errorPath;
                if (day.checked) {
                    day.dataset.errorPath = `profiles[${profileIndex}].days[${selectedDayIndex}]`;
                    selectedDayIndex += 1;
                }
            });

            const baselineId = `${fieldId}__profile_${profileIndex}_baseline`;
            const baselineErrorId = `${baselineId}_error`;
            baseline.id = baselineId;
            baseline.setAttribute("aria-describedby", baselineErrorId);
            profile.querySelector("[data-profile-baseline-label]").htmlFor = baselineId;
            profile.querySelector("[data-profile-baseline-error]").id = baselineErrorId;
            baseline.dataset.errorPath = `profiles[${profileIndex}].baseline`;
            rangeElements(profile).forEach(function (range, rangeIndex) {
                const rangePrefix = `${fieldId}__profile_${profileIndex}_range_${rangeIndex}`;
                const errorId = `${rangePrefix}_error`;
                const error = range.querySelector("[data-range-error]");
                error.id = errorId;
                ["start", "end", "value"].forEach(function (part) {
                    const control = range.querySelector(`[data-range-${part}]`);
                    control.id = `${rangePrefix}_${part}`;
                    control.dataset.errorPath = `profiles[${profileIndex}].ranges[${rangeIndex}].${part}`;
                    control.setAttribute("aria-describedby", errorId);
                });
                range.querySelector("[data-action='remove-weekly-range']").setAttribute(
                    "aria-label", `Remove range from profile ${profileIndex + 1}`
                );
            });
        });
    }

    function serializeEditor(editor) {
        return {
            unit: editor.querySelector("[data-weekly-unit]").textContent.trim(),
            profiles: profileElements(editor).map(function (profile) {
                return {
                    name: profile.querySelector("[data-profile-name]").value,
                    days: Array.from(profile.querySelectorAll("[data-profile-day]:checked"))
                        .map(function (checkbox) { return Number(checkbox.value); }),
                    baseline: numericValue(profile.querySelector("[data-profile-baseline]")),
                    ranges: rangeElements(profile).map(readRange),
                };
            }),
        };
    }

    function setPreviewStatus(root, message) {
        const status = root.querySelector("[data-timeseries-preview-status]");
        if (!status) return;
        status.textContent = message || "";
        status.hidden = !message;
    }

    function schedulePreview(editor, delay) {
        const root = editor?.closest("[data-timeseries-builder]");
        const region = root?.querySelector("[data-timeseries-preview]");
        if (!root || !region) return;
        activatePreview(root);
        if (editor.closest("[data-builder-panel]")?.hidden || !validateAndSync(editor)) {
            region.dispatchEvent(new CustomEvent("timeseries-preview:cancel", {bubbles: true}));
            setPreviewStatus(root, "Fix the highlighted errors to refresh the preview; the last valid chart is retained.");
            return;
        }
        const fieldWebId = root.dataset.fieldWebId || "";
        const separator = fieldWebId.indexOf("_");
        region.dispatchEvent(new CustomEvent("timeseries-preview:request", {
            bubbles: true,
            detail: {
                delay: delay,
                waitingStatus: delay > 0 ? "Waiting for the current edit to finish…" : "",
                refreshingStatus: "Refreshing preview…",
                values: {
                    object_type: separator < 0 ? "" : fieldWebId.slice(0, separator),
                    field_name: root.dataset.fieldName || (separator < 0 ? "" : fieldWebId.slice(separator + 1)),
                    builder: "weekly_pattern",
                    form_inputs: editor.querySelector("[data-weekly-pattern-payload]").value,
                },
            },
        }));
    }

    function cancelPreview(root) {
        const region = root.querySelector("[data-timeseries-preview]");
        if (region) region.dispatchEvent(new CustomEvent("timeseries-preview:cancel", {bubbles: true}));
    }

    function validateAndSync(editor) {
        if (!editor) return false;
        clearEditorErrors(editor);
        reindexEditor(editor);
        const profiles = profileElements(editor);
        const names = new Map();
        const generalErrors = [];
        let valid = profiles.length >= 1 && profiles.length <= 7;

        profiles.forEach(function (profile) {
            const nameInput = profile.querySelector("[data-profile-name]");
            const name = nameInput.value;
            let nameError = "";
            if (!name.trim()) {
                nameError = "Profile name is required.";
            } else if (names.has(name)) {
                nameError = `Profile name '${name}' must be unique.`;
                setControlError(names.get(name), nameError);
            }
            if (nameError) {
                setControlError(nameInput, nameError);
                profile.querySelector("[data-profile-name-error]").textContent = nameError;
                valid = false;
            } else {
                names.set(name, nameInput);
            }

            const baselineInput = profile.querySelector("[data-profile-baseline]");
            const baseline = numericValue(baselineInput);
            let baselineError = "";
            if (baseline === null) baselineError = "Baseline must be a finite number representable as float32.";
            else if (editor.dataset.canBeNegative !== "true" && baseline < 0) {
                baselineError = "Baseline must be zero or greater for this field.";
            }
            if (baselineError) {
                setControlError(baselineInput, baselineError);
                profile.querySelector("[data-profile-baseline-error]").textContent = baselineError;
                valid = false;
            }

            const ranges = rangeElements(profile);
            ranges.forEach(function (range) {
                if (!validateRange(editor, range, ranges)) valid = false;
            });
        });

        DAY_LABELS.forEach(function (day, dayIndex) {
            const owners = editor.querySelectorAll(`[data-profile-day][value='${dayIndex}']:checked`).length;
            if (owners !== 1) {
                generalErrors.push(`${day} must be assigned to exactly one profile.`);
                valid = false;
            }
        });
        if (profiles.length < 1 || profiles.length > 7) {
            generalErrors.push("A weekly pattern must contain between 1 and 7 profiles.");
        }
        showGeneralError(editor, generalErrors);

        editor.querySelector("[data-weekly-pattern-payload]").value = JSON.stringify(serializeEditor(editor));
        updateButtons(editor);
        return valid;
    }

    function sortRangesIfValid(editor, profile) {
        if (!validateAndSync(editor)) return;
        const container = profile.querySelector("[data-profile-ranges]");
        rangeElements(profile)
            .sort(function (left, right) { return readRange(left).start - readRange(right).start; })
            .forEach(function (range) { container.appendChild(range); });
        validateAndSync(editor);
    }

    function createRange(editor, start) {
        const row = document.createElement("tr");
        const minValue = editor.dataset.canBeNegative === "true" ? "" : ' min="0"';
        row.dataset.weeklyRange = "";
        row.innerHTML = `
            <td><input class="form-control form-control-sm" type="number" min="0" max="23" step="1"
                       value="${start}" required aria-label="Range start hour" data-range-start>
                <div class="text-danger small d-none" role="alert" data-range-error></div></td>
            <td><input class="form-control form-control-sm" type="number" min="1" max="24" step="1"
                       value="${start + 1}" required aria-label="Range end hour" data-range-end></td>
            <td><input class="form-control form-control-sm" type="number" step="0.1" value="0" required
                       aria-label="Range value" data-range-value${minValue}></td>
            <td><button class="btn btn-sm btn-link text-danger p-1" type="button"
                        data-action="remove-weekly-range">Remove</button></td>`;
        return row;
    }

    function createProfile(editor) {
        const profile = document.createElement("fieldset");
        const minValue = editor.dataset.canBeNegative === "true" ? "" : ' min="0"';
        profile.className = "weekly-profile-card";
        profile.dataset.weeklyProfile = "";
        profile.innerHTML = `
            <legend class="weekly-profile-card__legend float-none w-auto" data-profile-legend></legend>
            <button class="btn btn-sm btn-link text-danger weekly-profile-card__remove" type="button"
                    data-action="remove-weekly-profile">Remove</button>
            <div class="weekly-profile-field"><label class="form-label" data-profile-name-label>Name</label>
                <input class="form-control form-control-sm" type="text" value="profile" required data-profile-name>
                <div class="invalid-feedback" data-profile-name-error></div></div>
            <div class="weekly-profile-field"><span class="form-label d-block" data-profile-days-label>Days</span>
                <div class="weekly-day-picker" role="group" data-profile-days-group>
                ${DAY_LABELS.map(function (day, index) {
                    return `<label class="weekly-day-option" data-profile-day-label>
                                <input type="checkbox" value="${index}" data-profile-day><span>${day}</span>
                            </label>`;
                }).join("")}
                </div><div class="text-danger small d-none" role="alert" data-profile-days-error></div></div>
            <div class="weekly-profile-field"><label class="form-label" data-profile-baseline-label>Baseline</label><div class="input-group input-group-sm">
                <input class="form-control" type="number" value="0" step="0.1" required data-profile-baseline${minValue}>
                <span class="input-group-text" data-weekly-unit>${editor.querySelector("[data-weekly-unit]").textContent.trim()}</span>
                <div class="invalid-feedback" data-profile-baseline-error></div></div></div>
            <div class="table-responsive"><table class="table table-sm align-middle weekly-ranges-table">
                <thead><tr><th scope="col">From</th><th scope="col">To</th><th scope="col">Value</th>
                    <th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead>
                <tbody data-profile-ranges></tbody></table></div>
            <div><button class="btn btn-sm btn-outline-primary weekly-add-range" type="button"
                         data-action="add-weekly-range">+ Add time range</button></div>`;
        return profile;
    }

    function markModified(element) {
        const root = element.closest("[data-timeseries-builder]");
        if (!root) return;
        if (typeof window.tagFormAsModified === "function") window.tagFormAsModified();
        const fieldId = root.dataset.fieldWebId;
        const metadataAnchor = fieldId ? document.getElementById(fieldId) : null;
        if (metadataAnchor) {
            metadataAnchor.dispatchEvent(new CustomEvent("source-metadata:value-changed", {bubbles: true}));
        }
    }

    function initialize(root) {
        if (root.dataset.timeseriesBuilderInitialized === "true") return;
        root.dataset.timeseriesBuilderInitialized = "true";
        activateSelectedBuilder(root);
        const activeEditor = root.querySelector("[data-builder-panel='weekly_pattern']:not([hidden]) [data-weekly-pattern-editor]");
        const preview = root.querySelector("[data-timeseries-preview-column]");
        if (activeEditor && preview && !preview.hidden) schedulePreview(activeEditor, 0);
    }

    function initializeAll(container) {
        const scope = container?.querySelectorAll ? container : document;
        if (scope.matches?.("[data-timeseries-builder]")) initialize(scope);
        scope.querySelectorAll("[data-timeseries-builder]").forEach(initialize);
    }

    function syncUnitsFromConstantInputs(form) {
        if (!form) return [];
        const changedEditors = [];
        form.querySelectorAll("[data-timeseries-builder]").forEach(function (root) {
            const fieldId = root.dataset.fieldWebId;
            const constantUnit = document.getElementById(`${fieldId}__constant_unit`);
            if (!constantUnit) return;
            const unitChanged = Array.from(root.querySelectorAll("[data-weekly-unit]")).some(function (unit) {
                return unit.textContent.trim() !== constantUnit.value;
            });
            root.querySelectorAll("[data-weekly-unit]").forEach(function (unit) {
                unit.textContent = constantUnit.value;
            });
            root.querySelectorAll("[data-weekly-pattern-editor]").forEach(function (editor) {
                if (!editor.closest("[data-builder-panel]").hidden) validateAndSync(editor);
                else editor.querySelector("[data-weekly-pattern-payload]").value = JSON.stringify(serializeEditor(editor));
                if (unitChanged) changedEditors.push(editor);
            });
        });
        return changedEditors;
    }

    document.addEventListener("timeseries-unit:changed", function (event) {
        syncUnitsFromConstantInputs(event.target.closest("form")).forEach(function (editor) {
            const root = editor.closest("[data-timeseries-builder]");
            if (root.dataset.timeseriesBuilderInitialized === "true"
                && !editor.closest("[data-builder-panel]").hidden) schedulePreview(editor, 0);
        });
    });

    document.addEventListener("submit", function (event) {
        const form = event.target;
        if (!form?.querySelectorAll) return;
        form.querySelectorAll("[data-timeseries-builder]").forEach(function (root) {
            activateSelectedBuilder(root);
        });
    }, true);

    document.addEventListener("change", function (event) {
        syncUnitsFromConstantInputs(event.target.closest("form"));
        const selector = event.target.closest("[data-builder-selector]");
        if (selector) {
            const root = selector.closest("[data-timeseries-builder]");
            activateSelectedBuilder(root, true);
            const activeEditor = root.querySelector(
                "[data-builder-panel='weekly_pattern']:not([hidden]) [data-weekly-pattern-editor]"
            );
            if (activeEditor) schedulePreview(activeEditor, 0);
            else cancelPreview(root);
            markModified(selector);
            return;
        }

        const editor = event.target.closest("[data-weekly-pattern-editor]");
        if (!editor) return;
        const day = event.target.closest("[data-profile-day]");
        if (day && day.checked) {
            editor.querySelectorAll(`[data-profile-day][value='${day.value}']`).forEach(function (candidate) {
                if (candidate !== day) candidate.checked = false;
            });
        }
        const profile = event.target.closest("[data-weekly-profile]");
        if (profile && event.target.matches("[data-range-start], [data-range-end]")) {
            sortRangesIfValid(editor, profile);
        } else {
            validateAndSync(editor);
        }
        schedulePreview(editor, 0);
        markModified(event.target);
    });

    document.addEventListener("input", function (event) {
        const editor = event.target.closest("[data-weekly-pattern-editor]");
        if (editor) {
            validateAndSync(editor);
            if (!event.target.matches("[data-range-start], [data-range-end]")) {
                schedulePreview(editor, PREVIEW_DEBOUNCE_MS);
            }
        }
        if (event.target.closest("[data-timeseries-builder]")) markModified(event.target);
    });

    document.addEventListener("focusin", function (event) {
        const editor = event.target.closest("[data-weekly-pattern-editor]");
        if (editor) activatePreview(editor.closest("[data-timeseries-builder]"));
    });

    document.addEventListener("click", function (event) {
        const action = event.target.closest("[data-action]")?.dataset.action;
        if (!action || !action.includes("weekly")) return;
        const editor = event.target.closest("[data-weekly-pattern-editor]");
        if (!editor) return;
        const builderRoot = editor.closest("[data-timeseries-builder]");

        if (action === "add-weekly-profile") {
            const profile = createProfile(editor);
            const existingNames = new Set(profileElements(editor).map(function (item) {
                return item.querySelector("[data-profile-name]").value;
            }));
            let suffix = profileElements(editor).length + 1;
            while (existingNames.has(`profile ${suffix}`)) suffix += 1;
            profile.querySelector("[data-profile-name]").value = `profile ${suffix}`;
            editor.querySelector("[data-weekly-profiles]").appendChild(profile);
        } else if (action === "remove-weekly-profile") {
            event.target.closest("[data-weekly-profile]").remove();
        } else if (action === "add-weekly-range") {
            const profile = event.target.closest("[data-weekly-profile]");
            const start = firstFreeHour(profile);
            if (start !== null) profile.querySelector("[data-profile-ranges]").appendChild(createRange(editor, start));
        } else if (action === "remove-weekly-range") {
            event.target.closest("[data-weekly-range]").remove();
        }
        validateAndSync(editor);
        schedulePreview(editor, 0);
        markModified(builderRoot);
    });

    document.addEventListener("timeseries-preview:response", function (event) {
        const root = event.target.closest?.("[data-timeseries-builder]");
        if (!root || event.detail?.success) return;
        const editor = root.querySelector(
            "[data-builder-panel='weekly_pattern']:not([hidden]) [data-weekly-pattern-editor]"
        );
        if (!editor) return;
        clearEditorErrors(editor);
        reindexEditor(editor);
        const generalMessages = [];
        (event.detail.errors || []).forEach(function (error) {
            const control = Array.from(editor.querySelectorAll("[data-error-path]")).find(function (candidate) {
                return candidate.dataset.errorPath === error.path;
            });
            if (control) {
                setControlError(control, error.message);
                const profile = control.closest("[data-weekly-profile]");
                if (control.matches("[data-profile-name]")) {
                    profile.querySelector("[data-profile-name-error]").textContent = error.message;
                } else if (control.matches("[data-profile-baseline]")) {
                    profile.querySelector("[data-profile-baseline-error]").textContent = error.message;
                } else if (control.closest("[data-weekly-range]")) {
                    const rangeError = control.closest("[data-weekly-range]").querySelector("[data-range-error]");
                    rangeError.textContent = error.message;
                    rangeError.classList.remove("d-none");
                }
                return;
            }
            const profileMatch = error.path.match(/^profiles\[(\d+)](?:\.days(?:\[\d+])?)?/);
            const profile = profileMatch ? profileElements(editor)[Number(profileMatch[1])] : null;
            if (profile && error.path.includes(".days")) {
                const daysError = profile.querySelector("[data-profile-days-error]");
                daysError.textContent = error.message;
                daysError.classList.remove("d-none");
                profile.querySelectorAll("[data-profile-day]").forEach(function (day) {
                    day.setAttribute("aria-invalid", "true");
                });
            } else {
                generalMessages.push(error.message);
            }
        });
        showGeneralError(editor, generalMessages);
    });

    document.addEventListener("htmx:afterSettle", function (event) {
        initializeAll(event.detail?.target || event.target);
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { initializeAll(document); }, {once: true});
    } else {
        initializeAll(document);
    }

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            activatePreview,
            activateSelectedBuilder,
            firstFreeHour,
            initializeAll,
            schedulePreview,
            serializeEditor,
            validateAndSync,
        };
    }
}());
