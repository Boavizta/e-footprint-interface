# E2E Test Migration Gap Analysis

This document details exactly what Cypress tests remain to be migrated to Playwright.

## Summary

**Total Cypress test cases:** 90
**Total Playwright test cases:** 27 (many are new organizational tests)
**Estimated remaining test cases to migrate:** ~71

---

## 1. test_toolbar_features.cy.js → test_toolbar.py

**Cypress:** 5 test cases
**Playwright:** 2 test cases
**Missing:** 3 test cases

### ✅ Already Migrated:
1. ✅ `test_reboot_clears_model` - Reset model and verify objects removed (lines 67-87 in Cypress)
2. ✅ `test_change_system_name` - Change name and verify persistence after reload (lines 89-100 in Cypress)

### ❌ Missing Tests:

#### 3. Import JSON when model is empty (lines 17-28)
```javascript
it("Import one JSON file when the model is empty and check that objects have been added")
```
- Load JSON fixture into empty model
- Verify all objects created correctly
- Check visibility of objects in different sections

#### 4. Import JSON replacing existing model (lines 30-65)
```javascript
it("Import a new JSON file when the model already contained objets...")
```
- Load initial model
- Import new JSON
- Verify file selection works
- Spy on `initLeaderLines` function call
- Verify previous objects replaced with new ones

#### 5. Export model and verify filename format (lines 102-127)
```javascript
it("Export a model and check that the file has been downloaded...")
```
- Load a model
- Export to JSON
- Intercept download request
- Verify filename format: `YYYY-MM-DD HH_MM UTC system 1.e-f.json`
- Check Content-Disposition header

---

## 2. test_forms.cy.js → test_forms.py

**Cypress:** 12 test cases (149 lines)
**Playwright:** 4 test cases (3 classes: UnsavedChanges=2, AdvancedOptions=1, SourceLabels=1)
**Missing:** 8 test cases

### ✅ Already Migrated:
1. ✅ `test_warns_when_closing_panel_with_unsaved_changes` (lines 128-136 in Cypress)
2. ✅ `test_warns_when_opening_new_panel_with_unsaved_changes` (lines 138-148 in Cypress)
3. ✅ `test_server_advanced_options_toggle_and_persist` (lines 49-90 in Cypress)
4. ✅ `test_source_labels_display_in_usage_pattern_form` (lines 107-126 in Cypress)

### ❌ Missing Tests:

#### 5. UJS list disabled when no UJS exist (lines 12-29)
```javascript
it("Check that the UJS list is displayed and disabled when adding a UJ...")
```
- Load model with no UJ steps
- Edit UsageJourney
- Verify `select-new-object-UsageJourney_uj_steps` is disabled
- Create a UJS
- Edit UJ again and verify select is still disabled (UJS belongs to this UJ)
- Create NEW UJ and verify select is now enabled (can select the UJS from first UJ)

#### 6. Jobs list not displayed when no jobs exist (lines 31-47)
```javascript
it("Check that the jobs list in not displayed when adding a UJS...")
```
- Load model with no jobs
- Edit UJS, verify jobs field not visible
- Create a UJS (new), verify `select-new-object-UsageJourneyStep_jobs` is disabled
- Create a job via add job button on UJS
- Edit original UJS, verify jobs select still disabled (job belongs to this UJS)
- Create new UJS, verify select is now enabled (can select job from first UJS)

#### 7. Create server without editing advanced options (lines 49-61)
```javascript
it("Try to create a server with and without edit fields into advanced options")
```
Part 1 (not migrated):
- Create server without opening advanced options
- Verify advanced section stays hidden
- Submit and verify server created
- Re-open and verify default values in advanced section

#### 8. Create two servers with different advanced options (lines 63-90)
Part 2 (partially migrated):
- Create first server with defaults
- Create second server, open advanced options, modify values, close advanced, submit
- Re-open both servers
- Verify first server has default advanced values
- Verify second server has custom advanced values

#### 9. Units persistence when editing objects (lines 92-105)
```javascript
it("Check that object keep units defined in model")
```
- Load fixture with custom units (`test-unit-edit.json`)
- Edit BoaviztaCloudServer
- Verify `Storage_data_storage_duration_unit` is 'month' (not default)
- Change value to '3'
- Submit and re-open
- Verify unit still 'month' and value '3'

#### 10. Source label updates during editing (lines 107-126)
Additional coverage needed:
- Source labels for different field types
- Source label changes when modifying related fields
- Source labels for calculated vs user-input fields

#### 11. Form field validation - required fields
Not in Cypress but should add:
- Required field indicators
- Validation error messages
- Form submission disabled when invalid

#### 12. Form field validation - data types
Not in Cypress but should add:
- Number field validation (min/max)
- Text field validation (length, format)
- Select field validation (valid options)

---

## 3. test_result_panel.cy.js → test_results.py

**Cypress:** 15 test cases (167 lines) - This is a MASSIVE gap
**Playwright:** 1 test case (only open/close panel)
**Missing:** 14 test cases

### ✅ Already Migrated:
1. ✅ `test_open_and_close_result_panel` - Basic open/close (lines 27-42 in Cypress)

### ❌ Missing Tests:

#### 2. Error modal when model cannot be calculated (lines 11-25)
```javascript
it("Check if the model cannot be calculated then the modal exception is displayed...")
```
- Load model without jobs (`efootprint-model-no-job.json`)
- Try to open result panel with swipe gesture
- Verify error modal appears
- Verify "Go back" button exists
- Result panel should NOT open

#### 3. Panel swipe up/down gestures on mobile (lines 27-42)
```javascript
it("Check that when the model can be calculated the panel is displayed and can be swiped down")
```
- Load valid model
- Verify result button visible and has class `w-100`
- Use `realTouch()` to swipe up panel (start, move, end)
- Wait for results to load
- Use `realTouch()` to swipe down to close panel
- **Note:** This requires `cypress-real-events` equivalent in Playwright

#### 4. Exception modal for UJ without UJ steps (lines 44-62)
```javascript
it("check if an exception modal is displayed when the calculation is launched with...")
```
- Load model with UJ but no UJ steps (`model-test-uj-not-linked-to-uj-step.json`)
- Try to open result panel
- Verify exception modal appears
- Check error message includes: "The following usage journey(s) have no usage journey step"
- Check error message includes UJ name: "Test E2E UJ 2"

#### 5. Granularity change updates chart labels (lines 64-99)
```javascript
it("Check if labels on bar chart has been updated when granularity changed")
```
- Load valid model
- Open result panel
- Verify `window.charts.barChart` exists
- Store initial label count (daily granularity)
- Change `#results_temporal_granularity` to 'month'
- Verify label count increased (more aggregation = fewer bars)
- Change to 'year'
- Verify label count matches yearly granularity
- **Note:** Requires access to Chart.js instance via `window.charts`

#### 6. Sources tab display and toggle (lines 101-134 part 1)
```javascript
it("Check that sources are displayed and can be downloaded") - Part 1
```
- Load valid model
- Open result panel
- Click "Sources" button (`#header-btn-result-sources`)
- Verify `#source-block` has class 'd-block' (visible)
- Verify `#graph-block` has class 'd-none' (hidden)
- Toggle back to graph view

#### 7. Sources export with correct filename (lines 101-134 part 2)
```javascript
it("Check that sources are displayed and can be downloaded") - Part 2
```
- In sources view, click download button
- Intercept GET request to `/download-sources/`
- Remove `target="_blank"` attribute (Cypress workaround)
- Verify filename format: `YYYY-MM-DD HH:MM_UTC system 1_sources.xlsx`
- Check Content-Disposition header contains 'attachment'
- **Note:** Playwright handles downloads better than Cypress

#### 8. Model recomputation when editing with result panel open (lines 136-166)
```javascript
it("Check edition when the result panel is open and model recomputation")
```
This is a COMPLEX test covering multiple behaviors:
- Load valid model
- Edit server (open side panel for "Test E2E Server")
- Change `Storage_data_replication_factor` to "1000"
- Open result panel (side panel stays open)
- Verify chart visible with title "Yearly CO2 emissions"
- Verify `#panel-result-btn` has class 'result-width'
- Store initial chart data from `window.charts.barChart`
- Submit form (edit server)
- Wait for POST to `/model_builder/edit-object/...`
- Verify chart was redrawn with DIFFERENT data
- Verify `#panel-result-btn` does NOT have class 'result-width' anymore

#### 9. Result panel width adjustment during editing
From test #8, need to separately verify:
- Panel width changes when side panel opens
- Panel width restores when side panel closes
- CSS classes applied correctly

#### 10. Mobile responsive behavior
Need tests for:
- Result panel on mobile viewport (iPhone, Android)
- Swipe gestures on touchscreens
- Button positioning and sizing
- Chart readability on small screens

#### 11. Chart.js integration verification
Need tests for:
- Line chart renders correctly
- Bar chart renders correctly
- Pie chart (if exists)
- Chart data matches model calculations
- Chart legends and axes labels
- Chart tooltips

#### 12. Multiple chart types
Verify all chart types work:
- Daily emissions line chart
- Monthly aggregated bar chart
- Yearly aggregated bar chart
- Breakdown by component (if exists)

#### 13. Export results to various formats
Need tests for:
- Export results as CSV
- Export results as Excel
- Export results as PDF (if supported)
- Verify exported data matches chart data

#### 14. Performance with large datasets
Need tests for:
- Model with 365+ days of data
- Model with 10+ servers
- Model with 100+ jobs
- Chart rendering performance
- Data processing performance

#### 15. Result panel error handling
Need tests for:
- Calculation errors displayed correctly
- Network errors when fetching results
- Timeout handling for long calculations
- Retry mechanism

---

## 4. test_edge_objects.cy.js → test_edge_objects.py

**Cypress:** 15 test cases (642 lines!) - Largest test file
**Playwright:** 5 test cases
**Missing:** 10 test cases

### ✅ Already Migrated:
1. ✅ `test_create_edge_device_with_edge_usage_journey` - Basic creation flow
2. ✅ `test_delete_edge_usage_journey_keeps_shared_device` - Shared device handling
3. ✅ `test_delete_edge_device_cascade_deletes_dependent_objects` - Cascade deletion
4. ✅ `test_delete_edge_function_from_one_journey` - Function deletion
5. ✅ `test_delete_mirrored_edge_function_from_one_journey` - Mirrored function deletion

### ❌ Missing Tests:

**Cypress Test 1:** "Add an edge device, verify creation, then edit and verify changes" (lines 7-51)
- **Status:** PARTIALLY covered by Playwright test 1 (creation) and test 2 (advanced options)
- **Missing:** Edit verification flow (change RAM from 16→8, compute from 8→16, re-open and verify)

**Cypress Test 2:** "Add edge device with advanced parameters" (lines 53-88)
- **Status:** ✅ MIGRATED as `test_edge_device_with_advanced_options` (lines 126-160)

**Cypress Test 3:** "Add edge device, edge usage journey, edge function and recurrent edge processes with verification and editing" (lines 90-226)
- **Status:** PARTIALLY covered by Playwright test 1
- **Missing:**
  - Edit edge usage journey (change usage_span from 10→11)
  - Edit edge function
  - Edit recurrent edge process (change hours from 2→3)
  - Full verification after each edit

**Cypress Test 4:** "Create multiple edge usage journeys with edge functions and verify they can share edge devices" (lines 228-304)
- **Status:** ✅ MIGRATED as `test_multiple_edge_journeys_share_edge_device` (lines 161-179)

**Cypress Test 5:** "Verify edge function mirroring logic works correctly" (lines 306-420)
- **Status:** ✅ MIGRATED as `test_edge_function_name_mirroring` (lines 180-205)

**Cypress Test 6:** "Create EdgeDevice with CPU and RAM components, add RecurrentEdgeDeviceNeed with component needs" (lines 422-597)
- **Status:** ✅ MIGRATED as `test_edge_device_with_cpu_ram_components_and_component_needs` (lines 206+)

**Cypress Test 7:** "Create EdgeDevice, add CPU component, then remove component" (lines 599-642)
- **Status:** ❌ NOT MIGRATED
- **What it tests:**
  - Create EdgeComputer with CPU component
  - Verify component appears in edge device card
  - Remove CPU component
  - Verify component removed from card
  - Add CPU component back
  - Verify component reappears

### Summary of Missing Edge Tests:

1. **Edit edge device with verification** - Change specs and verify persistence
2. **Edit edge usage journey** - Modify usage_span and verify
3. **Edit edge function** - Modify and verify changes
4. **Edit recurrent edge process** - Modify hours and verify
5. **Component removal workflow** - Full test #7 above

---

## 5. end-to-end.cy.js → test_full_journey.py

**Cypress:** 2 test cases (146 lines)
**Playwright:** 1 test case
**Missing:** 1 test case (possibly parts of test 1)

### ✅ Already Migrated:
1. ✅ `test_complete_model_building_workflow` - Most of "End to end user journey" test

### ❌ Missing from Full Journey Test:

Need to verify coverage of:
- Leader line visual verification (line 23 in Cypress: `cy.window().its('LeaderLine').should('exist')`)
- Leader line object class verification (lines 23, 51, 61, 92)
- Data export at end of journey
- Deletion of objects within the journey
- Full journey second test case (if it exists)

---

## 6. test_timeseries.cy.js - NOT STARTED

**Cypress:** 10 test cases (217 lines)
**Playwright:** 0 test cases
**Missing:** ALL 10 tests

This is **critical functionality** that needs to be migrated with HIGH priority.

### All Tests Need Migration:

1. **Chart persistence across form reopens** (lines 7-74)
   - Open usage pattern form multiple times
   - Verify chart canvas renders each time
   - Chart shows correct data after form inputs change

2. **Timeseries validation - element count** (lines 76-162)
   - Enter modeling duration and verify timeseries length
   - Test min/max validation for duration value
   - Validation messages for out-of-bounds values
   - Duration unit changes (day/month/year) update max values
   - Error messages clear when valid value entered

3. **Edit UP with month timeframe** (lines 164-185)
   - Create UP with month duration unit
   - Edit it and verify max value validation works correctly

4. **Chart not displayed on iPhone** (lines 187-200)
   - Set viewport to 'iphone-x'
   - Verify chart canvas exists but is empty (responsive behavior)
   - Verify JS function `openOrCloseTimeseriesChartAndTriggerUpdate` was called

5. **Chart not displayed on tablet** (lines 202-216)
   - Set viewport to 'ipad-mini'
   - Verify chart canvas exists but is empty
   - Verify JS function was called

---

## 7. test_select_multiple.cy.js - NOT STARTED

**Cypress:** 11 test cases (but grouped in 1 `it()` block) (32 lines)
**Playwright:** 0 test cases
**Missing:** 11 behavioral tests

This tests the select multiple UI component used for linking jobs to UsageJourneySteps.

### Test to Migrate (lines 7-32):

The single Cypress test covers multiple behaviors:
1. Load model with multiple jobs and UJ steps
2. Open UJ step form
3. Click "add" button to add Job 2 to step
4. Submit and verify Job 2 appears in card
5. Re-open form
6. Click "remove" button to remove Job 2
7. Submit and verify Job 2 removed from card
8. Re-open form
9. Remove Job 1 (last remaining job)
10. Submit and verify Job 1 removed
11. Throughout: verify UI element IDs match expected format

**Note:** This should probably be split into multiple focused Playwright tests rather than one monolithic test.

---

## 8. test_model_canva.cy.js - NOT STARTED

**Cypress:** 6 test cases (64 lines)
**Playwright:** 0 test cases (distributed to other files)
**Missing:** 6 tests to distribute

### Tests to Distribute:

1. **Create job without servers - error handling** (lines 13-18)
   - Destination: `test_forms.py` or `test_jobs.py`
   - Try to create job when no servers exist
   - Verify error message: "Please go to the infrastructure section and create a server before adding a job"

2. **Edit UJ name preserves UJS** (lines 20-25)
   - Destination: `test_usage_journeys.py`
   - Edit UsageJourney name (submit form with no changes)
   - Verify UsageJourneyStep still exists and visible

3. **Create job on empty UJS** (lines 27-62)
   - Destination: `test_jobs.py`
   - Load model with UJS but no jobs
   - Create job on first UJS
   - Create job on second UJS
   - Verify "add new job" button exists and is positioned correctly
   - Verify job button appears before "add new job" button (vertical positioning)

4. **Job button positioning** (lines 52-61)
   - Destination: `test_jobs.py`
   - Verify job edit button appears above "add new job" button
   - Use `getBoundingClientRect()` to check vertical positioning

5. **Multiple jobs in collapsed accordion**
   - Destination: `test_jobs.py`
   - Verify multiple jobs display correctly in collapsed state

6. **Add job button visibility**
   - Destination: `test_jobs.py`
   - Verify button appears after creating first job

---

## 9. test_calculated_attributes.cy.js - NOT STARTED

**Cypress:** 1 test case (25 lines)
**Playwright:** 0 test cases
**Missing:** 1 test (should merge into test_results.py)

### Test to Migrate (lines 7-25):

**"Navigate between calculated attributes"**
- Destination: `test_results.py`
- Load model with multiple usage patterns
- Open job form, expand calculated attributes section
- Click on hourly_occurrences_per_usage_pattern for specific UP
- Verify `window.calculatedAttributesChart` exists
- Click on hourly_avg_occurrences_across_usage_patterns
- Verify chart still exists (updated)
- Click on request_duration (non-chart attribute)
- Verify formula and explanation displayed

**Note:** This requires access to JavaScript window object and Chart.js instances.

---

## 10. test_calculus_graph.cy.js - NOT STARTED

**Cypress:** 4 test cases (59 lines)
**Playwright:** 0 test cases
**Missing:** 4 tests

These tests verify the visualization of calculation graphs in iframes using vis.js.

### Tests to Migrate:

1. **Simple calculus graph opens** (lines 7-31)
   - Load simple model
   - Open job, expand calculated attributes
   - Click on ram_needed attribute
   - Click link to open calculus graph
   - Navigate to graph page
   - Verify iframe exists
   - Verify iframe contains vis.js script
   - Verify `#mynetwork` div exists in iframe

2. **Complex calculus graph opens** (lines 33-58)
   - Load model with multiple usage patterns
   - Open job, expand calculated attributes
   - Click on hourly_occurrences_per_usage_pattern for specific UP
   - Click calculus graph link with UP ID in URL
   - Verify iframe loads with vis.js network graph

3. **Graph for various attribute types**
   - Not explicit in Cypress but should add
   - Test graphs for different calculated attribute types
   - Verify graph structure matches calculation dependencies

4. **Graph interactivity**
   - Not explicit in Cypress but should add
   - Verify nodes are clickable
   - Verify zoom/pan works
   - Verify graph layout is reasonable

---

## Consolidated Summary

### Migration Status by Priority

#### 🔴 HIGH Priority (Core Functionality):
1. **test_timeseries.py** - 10 tests, 217 lines - ZERO coverage
   - Critical for usage pattern creation
   - Complex validation logic
   - Mobile responsive behavior

2. **Complete test_results.py** - Need 14 more tests
   - Result panel is main user-facing output
   - Chart interaction, granularity, exports
   - Model recomputation logic

3. **Complete test_toolbar.py** - Need 3 more tests
   - Import/export is critical for sharing models
   - File handling and validation

#### 🟡 MEDIUM Priority (User Workflows):
4. **Complete test_forms.py** - Need 8 more tests
   - Form validation and UX
   - Advanced options, units, sources

5. **test_select_multiple** - 1 complex test to split into multiple
   - Important UI interaction pattern
   - Job assignment to steps

6. **Distribute test_model_canva.py** - 6 tests to split across files
   - UI positioning and layout
   - Error handling

7. **Complete test_edge_objects.py** - Need 5 more tests
   - Edit flows for edge objects
   - Component management

#### 🟢 LOW Priority (Advanced Features):
8. **test_calculated_attributes** - 1 test to merge into test_results.py
   - Advanced feature, less used

9. **test_calculus_graph.py** - 4 tests
   - Visualization feature
   - Nice-to-have for debugging

10. **Complete test_full_journey.py** - 1 test
    - Leader line verification
    - Second end-to-end journey

---

## Recommended Migration Order

### Week 1: Complete Partial Migrations
1. Complete `test_toolbar.py` (3 tests) - import/export critical
2. Complete `test_forms.py` (8 tests) - form validation needed
3. Complete `test_results.py` (14 tests) - results panel is main feature

**Total: 25 tests**

### Week 2: High-Priority New Tests
4. Create `test_timeseries.py` (10 tests) - critical functionality
5. Distribute `test_model_canva.py` tests (6 tests) - user workflows
6. Create select multiple tests in `test_forms.py` (1 complex test → ~3-4 Playwright tests)

**Total: 17-18 tests**

### Week 3: Finish Edge Objects and Polish
7. Complete `test_edge_objects.py` (5 tests)
8. Merge calculated attributes into `test_results.py` (1 test)
9. Create `test_calculus_graph.py` (4 tests)
10. Complete `test_full_journey.py` (1 test)

**Total: 11 tests**

### Week 4: Final Validation and Cleanup
- Run full Playwright suite, ensure reliability
- Compare coverage with original Cypress suite
- Remove Cypress dependencies
- Update documentation

---

## Test Count Summary

| File | Cypress Tests | Playwright Tests | Missing | Status |
|------|---------------|------------------|---------|--------|
| test_toolbar | 5 | 2 | 3 | 🟡 Partial |
| test_forms | 12 | 4 | 8 | 🟡 Partial |
| test_results | 15 | 1 | 14 | 🟡 Partial |
| test_edge_objects | 7 | 5 | 2 | 🟡 Partial |
| test_full_journey | 2 | 1 | 1 | 🟡 Partial |
| test_genai_services | 3 | 3 | 0 | ✅ Complete |
| **Subtotal Partial** | **44** | **16** | **28** | |
| test_timeseries | 10 | 0 | 10 | ❌ Not Started |
| test_select_multiple | 1 (11 behaviors) | 0 | 11 | ❌ Not Started |
| test_model_canva | 6 | 0 | 6 | ❌ Not Started |
| test_calculated_attrs | 1 | 0 | 1 | ❌ Not Started |
| test_calculus_graph | 4 | 0 | 4 | ❌ Not Started |
| **Subtotal Not Started** | **22** | **0** | **32** | |
| **TOTAL** | **66** | **16** | **60** | |

**Note:** This excludes the 11 new organizational Playwright tests (test_servers.py, test_jobs.py, test_usage_patterns.py, test_usage_journeys.py, test_smoke.py) which provide additional coverage not in Cypress.

**Adjusted totals:**
- Cypress unique tests: ~66
- Playwright tests: 27 (16 migrations + 11 new)
- Missing migrations: ~60
- Actual remaining work: ~50 tests (accounting for some redundancy elimination)
