# Sankey Feature — Testing Strategy

## Guiding principle

`ImpactRepartitionSankey` computation is already well tested in e-footprint. Interface tests must not duplicate that. The interface tests cover three things only:
1. **Parameter mapping**: form data is correctly translated into `ImpactRepartitionSankey` constructor arguments
2. **Response structure**: views return the correct HTML shape (IDs, column headers with UI labels, title, Plotly JSON present)
3. **UI behaviour**: chip toggle wiring, live update firing, card add/remove, onboarding banner

---

## 1. Python unit tests — `tests/unit_tests/adapters/views/test_sankey_views.py`

Use Django's test client with a `minimal_model_web` fixture (or a custom one with a slightly richer system — server, device, network, storage — so the chip lists are non-trivial).

### `sankey_form()`

- Returns 200 with a form containing a hidden `card_id` input that is unique across successive calls
- Excluded types chips only contain classes present in `model_web.response_objs` that are impact sources
- Skipped types chips only contain classes present in `model_web.response_objs`
- Default skipped chips (UsagePattern, JobBase, etc.) are pre-selected **only if those classes are present in the system**; chips for absent classes do not appear at all
- Each pre-selected chip has a corresponding `<input type="hidden">` already present in the form

### `sankey_diagram()`

- Returns 200 with the `card_id` echoed in the `#sankey-diagram-area-{card_id}` element ID
- Response contains a `#sankey-plot-{card_id}` element with embedded Plotly JSON (`data-plotly` attribute or inline)
- Column header labels use UI strings from `ClassUIConfigProvider`, not raw efootprint class names (e.g., `"Server"` label comes from config, not hardcoded)
- Title contains the system name and a CO2 amount string
- **Parameter mapping — verify the correct kwargs are passed to `ImpactRepartitionSankey`** by patching the constructor and asserting the call arguments:
  - `lifecycle_phase_filter=None` when `"all_phases"` submitted
  - `lifecycle_phase_filter="Manufacturing"` when `"Manufacturing"` submitted
  - `skip_phase_footprint_split=True` when phase toggle is unchecked
  - `skip_phase_footprint_split=False` when phase toggle is checked
  - Same for `skip_object_category_footprint_split` and `skip_object_footprint_split`
  - `aggregation_threshold_percent` receives the float value from the slider
  - `excluded_object_types` receives the correct class strings from active exclude chips
  - `skipped_impact_repartition_classes` receives the correct class strings from active skip chips
  - `display_column_information=False` always (column headers are rendered as HTML)
- Column headers are absent from response when `show_column_headers=false` is submitted

**Fixture:** a system with at least one Server, Device, Network, Storage, UsagePattern, and Job so the chip lists are meaningful.

---

## 2. Jest unit test — `js_tests/sankey.test.js`

The only JS logic that warrants a unit test is the chip toggle, since a bug there silently breaks parameter submission (CSS changes but hidden input is missing). Everything else is HTMX/Plotly behaviour better covered by E2E.

### Chip toggle

```javascript
// Setup: a chip span + an empty form in jsdom
// Call toggleSkipChip(chipEl, form) / toggleExcludeChip(chipEl, form)

test('activating a skip chip adds CSS class and hidden input', () => { ... })
test('deactivating a skip chip removes CSS class and hidden input', () => { ... })
test('activating an exclude chip uses active-exclude class, not active', () => { ... })
test('deactivating an exclude chip removes CSS class and hidden input', () => { ... })
test('multiple chips produce multiple hidden inputs with same name', () => { ... })
```

No need to test `liveUpdate` debouncing or Plotly calls — those are integration concerns.

---

## 3. E2E tests — `tests/e2e/test_sankey.py`

Use a system fixture with Server, Device, Network, Storage, UsagePattern, and Job so all chip types are present. Build it programmatically following the existing fixture pattern.

### `SankeyPage` page object — `tests/e2e/pages/sankey_page.py`

Extract Sankey-specific Playwright interactions into a page object to keep tests readable:

```python
class SankeyPage:
    def first_card(self) -> SankeyCard
    def cards(self) -> list[SankeyCard]
    def add_card(self) -> SankeyCard          # clicks "+ Add another analysis view", returns new card
    def onboarding_banner_visible(self) -> bool
    def dismiss_onboarding_banner(self)

class SankeyCard:
    def diagram_area_locator(self) -> Locator   # #sankey-diagram-area-{card_id}
    def plot_locator(self) -> Locator            # the Plotly div
    def settings_visible(self) -> bool
    def set_lifecycle_filter(self, value: str)   # "all_phases" | "Manufacturing" | "Usage"
    def set_aggregation_threshold(self, value: float)
    def toggle_phase_split(self, enabled: bool)
    def toggle_category_split(self, enabled: bool)
    def toggle_object_split(self, enabled: bool)
    def open_advanced(self)
    def toggle_skip_chip(self, label: str)       # by UI label text
    def toggle_exclude_chip(self, label: str)
    def remove(self)
    def wait_for_diagram_update(self)            # waits for HTMX swap to settle
    def diagram_is_rendered(self) -> bool        # checks Plotly div has content
    def title_text(self) -> str
```

### Tests

```python
@pytest.mark.e2e
class TestSankeySection:

    def test_first_diagram_auto_renders_on_result_panel_open(self, sankey_system):
        """Opening the result panel generates the first Sankey with default settings."""
        page = sankey_system.open_result_panel()
        card = SankeyPage(page).first_card()
        assert card.settings_visible()
        assert card.diagram_is_rendered()
        assert card.title_text()  # non-empty

    def test_changing_lifecycle_filter_updates_diagram(self, sankey_system):
        """Changing the lifecycle filter triggers a live update of the diagram."""
        card = SankeyPage(sankey_system.open_result_panel()).first_card()
        title_before = card.title_text()
        card.set_lifecycle_filter("Manufacturing")
        card.wait_for_diagram_update()
        assert card.diagram_is_rendered()
        assert "manufacturing" in card.title_text().lower()
        assert card.title_text() != title_before

    def test_two_cards_are_independent(self, sankey_system):
        """Changing settings on one card does not affect the other."""
        sankey_page = SankeyPage(sankey_system.open_result_panel())
        card2 = sankey_page.add_card()
        card2.wait_for_diagram_update()
        card1 = sankey_page.first_card()
        title1_before = card1.title_text()

        card2.set_lifecycle_filter("Manufacturing")
        card2.wait_for_diagram_update()

        assert card1.title_text() == title1_before  # card1 unchanged

    def test_add_and_remove_cards(self, sankey_system):
        """Cards can be added and removed; removal is client-side only."""
        sankey_page = SankeyPage(sankey_system.open_result_panel())
        assert len(sankey_page.cards()) == 1

        card2 = sankey_page.add_card()
        card2.wait_for_diagram_update()
        assert len(sankey_page.cards()) == 2

        card2.remove()
        assert len(sankey_page.cards()) == 1

    def test_onboarding_banner_dismissal_persists(self, sankey_system):
        """Dismissing the onboarding banner stores the preference in localStorage."""
        page_obj = sankey_system.open_result_panel()
        sankey_page = SankeyPage(page_obj)
        assert sankey_page.onboarding_banner_visible()

        sankey_page.dismiss_onboarding_banner()
        assert not sankey_page.onboarding_banner_visible()

        # Re-open result panel: banner should remain dismissed
        page_obj.close_result_panel()
        page_obj.open_result_panel()
        assert not SankeyPage(page_obj).onboarding_banner_visible()

    def test_skip_chip_toggles_update_diagram(self, sankey_system):
        """Toggling a skip chip triggers a live update."""
        card = SankeyPage(sankey_system.open_result_panel()).first_card()
        card.open_advanced()
        card.toggle_skip_chip("Usage journey")   # enable skipping usage journey
        card.wait_for_diagram_update()
        assert card.diagram_is_rendered()

    def test_settings_panel_open_by_default(self, sankey_system):
        """Settings panel is visible when a new card is created."""
        sankey_page = SankeyPage(sankey_system.open_result_panel())
        card2 = sankey_page.add_card()
        assert card2.settings_visible()

    def test_chip_lists_filtered_to_system_classes(self, sankey_system):
        """Skip/exclude chip lists only show classes present in the current system."""
        card = SankeyPage(sankey_system.open_result_panel()).first_card()
        card.open_advanced()
        # Edge classes are not in this system — their chips must not appear
        assert not card.skip_chip_exists("Edge usage pattern")
        assert not card.exclude_chip_exists("Edge device")
```

### Fixture

```python
@pytest.fixture
def sankey_system(model_builder_page):
    """System with Server, Storage, Device, Network, UsagePattern and Job
    so all chip types are non-empty. Uses from_defaults() throughout."""
    storage = Storage.from_defaults("Test Storage")
    server = Server.from_defaults("Test Server", storage=storage)
    service = VideoStreaming.from_defaults("Test Service", server=server)
    device = Device.from_defaults("Test Device")
    network = Network.from_defaults("Test Network")
    country = country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz("Europe/Paris"))()
    uj_step = UsageJourneyStep.from_defaults("Test Step", jobs=[VideoStreamingJob.from_defaults("Job", service)])
    uj = UsageJourney("Test Journey", uj_steps=[uj_step])
    usage_pattern = UsagePattern("Test UP", usage_journey=uj, devices=[device],
                                 network=network, country=country,
                                 hourly_usage_journey_starts=create_hourly_usage())
    system = System("Test System", usage_patterns=[usage_pattern], edge_usage_patterns=[])
    system_dict = system_to_json(system, save_calculated_attributes=False)
    return load_system_dict_into_browser(model_builder_page, system_dict)
```

---

## 4. What is explicitly NOT tested here

- Whether the Sankey diagram produces correct nodes/flows for given parameters — covered by e-footprint's own test suite
- Plotly rendering correctness (node positions, colors, link widths) — out of scope
- The `liveUpdate` debounce timing — too flaky; covered implicitly by E2E update tests
- Mobile landscape hint — low priority; if added, test via `page.set_viewport_size()` in a separate test