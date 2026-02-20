# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.14.2] - 2026-02-20

### Fixed
- Upgraded to efootprint 16.0.4 to fix a deletion bug.

## [0.14.1] - 2026-02-20

### Fixed
- Job forms by adding external_api to attributes_to_skip_in_forms and adding a pre_create hook to rename form fields according to job type.
- Don’t include "install service" accordion for servers that don’t have any installable services.

### Changed
- Update to efootprint 16.0.3 for better EcoLogits impact units.

## [0.14.0] - 2026-02-19

### Changed
- The Add external API workflow now creates a native ExternalAPI e-footprint object instead of creating a server with a service. This allows for the integration of native EcoLogits genAI API modeling in the interface.
- Display of EcoLogits code in EcoLogits jobs calculated attributes section.
- Finished migration of all legacy tests.
- Minor UI adjustments.

## [0.13.2] - 2026-02-16

### Fixed
- Fix object ordering (saving model to json reversed object order).
- Make edge devices sortable by dragging and dropping.

### Changed
- Close server accordions when servers have jobs (used to be when they have installed services).

## [0.13.1] - 2026-02-06

### Fixed
- Use cache table instead of session table for calculus graph html caching.

## [0.13.0] - 2026-02-05

### Added
- Possibility to add recurrent server needs to edge functions, to model the interaction between edge devices and web servers.

### Fixed
- Apply initDynamicForm after htmx settle instead of swap, so that opening the same dynamic form twice in a row keeps hidden forms hidden.
- When opening a form that depends on hx-vals while a modified form is open, conserve hx-vals in request so that if user clicks "Yes, continue" in the unsaved warning modal, the initial request is complete and doesn’t result in an error.

## [0.12.2] - 2026-01-27

### Fixed
- Catch Redis write errors when saving system with calculated attributes to avoid breaking model computation and falling back to Postgres when Redis is down (or misconfigured and full).

## [0.12.1] - 2026-01-27

### Changed
- Update to e-footprint 14.3.0 for caching BoaviztAPI calls to reduce latency.

## [0.12.0] - 2026-01-27

### Changed
- Use Redis as hot cache for system with calculated attributes, with Postgres fallback that saves systems without calculated attributes. This greatly improves performance when computing models with many calculated attributes, while having a fallback in case load is too high for Redis or Redis is down.

## [0.11.1] - 2026-01-26

### Fixed
- Don’t save data returned by the ProgressiveImportService because it contains wrong calculus graph data. This service should only be used to estimate the model size and not to update the model data.

## [0.11.0] - 2026-01-26

### Fixed
- If the number of gpu required for a GenAI model is strictly equal to the amount needed, add a gpu to have some margin (otherwise available ram will be 0 on the gpu server, which creates errors).
- Fixed UsagePatternWebBaseClass container and accordion children properties so that usage patterns become deletable again.

### Added
- Json payload size limit set to 30 MB to avoid memory issues on the server when uploading too big models, or editing a model to make it bigger than the limit.

### Changed
- Set number of workers to 1 in production environment to reduce memory footprint.
- Recycle worker when 1.6GB RAM is reached to avoid memory leaks.

## [0.10.12] - 2025-12-19

### Fixed
- Timeseries from growth yearly and monthly limits logic. Updating unit didn’t trigger logic because of updateSource error.

### Changed
- Simplify object_factory.py by removing all its presenter concerns into the form data parser.
- Migrated all Cypress tests to Playwright for better maintainability and performance.

## [0.10.11] - 2025-12-15

### Changed
- Much clean architecture refactoring: improved code structure and separation of concerns for better maintainability and scalability, especially around presentation and form logic.

### Fixed
- Usage pattern edition context: devices should be converted to select_object field.
- Set base_ram_consumption and storage_capacity steps to 0.1.
- Only cleanup created object if it was actually added to system.

## [0.10.10] - 2025-12-08

### Fixed
- When loading a model generated with e-footprint, append its specific objects that have defaults in the interface (for example, countries) to the object list, instead of just retrieving the default object list. In this way, if a particular country has been created in the model, it will be available in the interface instead of only the default countries.

## [0.10.9] - 2025-12-05

### Added
- Static files cache busting for all environments: JS/CSS files now have content hashes in filenames, forcing browsers to fetch new versions on deployment.

### Fixed
- Remove sourcemap references from third-party libraries (chart.js, bootstrap) that were breaking collectstatic.

## [0.10.8] - 2025-12-05

### Fixed
- Robustify leaderline scroll areas event listeners. They would not be activated after json upload.
- Remove unnecessary event listeners in edge device and recurrent edge component need forms.

## [0.10.7] - 2025-12-04

### Fixed
- Stop multiplying event listeners every time initLeaderLines is called (which happens on every object addition/edit). This was causing performance issues and memory leaks when the model got bigger. Now event listeners are only added once thanks to the addition of listener addition tags.

## [0.10.6] - 2025-12-01

### Added
- Increased number of available countries through e-footprint upgrade to 14.1.0.

## [0.10.5] - 2025-11-21

### Changed
- Removed lifespan, power and idle power from EdgeApplianceComponentWeb calculated attributes because they are just copies of the EdgeApplianceWeb ones.

## [0.10.4] - 2025-11-20

### Fixed
- Delete object whose creation triggered an error so that it doesn’t exist without being shown to the user. When creating a RecurrentEdgeProcess that linked an EdgeDevice with lifespan inferior to the EdgeUsageJourney usage span, the RecurrentEdgeProcess wouldn’t be deleted but it wouldn’t be linked to the EdgeFunction either, hence being inaccessible from the user and triggering errors when trying to delete the EdgeDevice.

## [0.10.3] - 2025-11-20

### Fixed
- Update to e-footprint 14.0.4 to fix EdgeAppliance and EdgeComputer deletion bugs.

## [0.10.2] - 2025-11-18

### Fixed
- EdgeAppliance and EdgeComputer calculated attributes. Those objects have hidden components and the hidden components calculated attributes didn’t appear in the parent object calculated attributes list, even though they are important to understand the computation graph.

## [0.10.1] - 2025-11-17

### Fixed
- Fixed RecurrentEdgeComponentNeedWeb deletion logic. It had a legacy custom generate_delete_http_response that is now obsolete because ModelingObjectWeb has a generic self_delete() method that works for all objects. This caused issues when deleting such objects from the interface.

## [0.10.0] - 2025-11-17

### Added
- Upgrade to e-footprint 14.0.0 introduces a new custom edge device object that is made up of components. The edge device needs linking to such objects can specify needs for each component.
- Graph visualisation for timeseries generated with code.

### Changed
- Deleted all FromForm classes and replaced timeseries form creation with the introduction of ExplainableHourlyQuantitiesFromFormInputs and ExplainableRecurrentQuantitiesFromConstant. In this way, there is no need anymore to create a specific "FromForm" class for each object with timeseries attributes. This greatly simplifies the codebase and makes it more maintainable.
- Deleted all Mirrored object classes and replaced them with an automatic mirroring logic directly in the ModelingObjectWeb class. This greatly simplifies the codebase and makes it more maintainable.

## [0.9.4] - 2025-11-07

### Added
- Major improvements on result charts readibility and manipulation: add dynamic legend with element selection and improve tooltip structure and data.

## [0.9.3] - 2025-10-27

### Fixed
- Upgrade to e-footprint 13.0.0 to aggregate timeseries by sum or mean depending on unit. Fixed wrong aggregation by sum for concurrent resource use like number of server instances.

## [0.9.2] - 2025-10-22

### Changed
- Upgrade to e-footprint 12.0.0 introduces EdgeFunction objects that are analogous to UsageJourneyStep objects, and the choice to create either EdgeAppliances or EdgeComputers when creating EdgeDevices.

### Added
- New homepage design.

## [0.9.1] - 2025-10-20

### Changed
- Use Boavizta logo.
- Deploy to Clever-Cloud with Docker instead of to GCP with App Engine.

## [0.9.0] - 2025-09-24

### Added
- Edge objects: edge devices with storage, edge usage journeys, recurrent edge processes and edge usage patterns.

### Fixed
- Memory leak caused by keeping file open when updloading json.
- Recomputation issues: see e-footprint 11.2.3 upgrade and calculus graph update in default_system_data.json.
- Stop displaying form sections with only one object type in choices.

### Changed
- Major refactoring: web objects now have their own modules in model_builder/web_abstract_modeling_classes, model_builder/web_builders and model_builder/web_core for better maintenability and reflecting e-footprint structure.

## [0.8.18] - 2025-08-01

### Fixed
- Devices list in UsagePatternFromForm. Selected object didn’t appear.

### Changed
- Upgrade to e-footprint 10.1.15 for performance improvements.

## [0.8.17] - 2025-07-18

### Added
- Add external API functionality for gen AI models: now a model can be directly selected and a GPU server with just enough specs will be created to host it.

## [0.8.16] - 2025-07-11

### Added
- Add a new button in the toolbar to open the result panel.

### Fixed
- Add empty_explainable_object calculated attribute template.
- Update system data after objects have been deleted due to an edition
- Select multiple logic refacto and fixes: send null value if no option selected + fix htmx errors with event propagation stops in buttons.

### Changed
- Review SCSS rules and update CSS class in templates to unify styles.

## [0.8.15] - 2025-07-09

### Added
- A modal to warn users that changes might be discarded when trying to close an open side panel with unsaved inputs.

### Changed
- Names rules for JSON export files have been updated. Max 120 characters and sanitize characters to avoid issues with special characters in filenames.
- Update CSS to overwrite disabled style for buttons.

## [0.8.14] - 2025-07-08

### Changed
- Calculated attributes display now the formula used to compute them in the edit form. For explainableQuantity attributes, the formula is accessible on the side of the value. For ExplainableHourlyQuantity attributes, the formula is displayed with the chart of the timeseries.

## [0.8.13] - 20225-06-25

### Added
- Add a variant input field for disabled fields in forms.

### Fixed
- To fit with old usage patterns, results view now doesn’t raise an error when global start_date doesn’t start at midnight but rounds to the previous midnight global start_date.

## [0.8.12] - 2025-06-25

### Fixed
- Fix issue with usage pattern sources not being displayed in the side panel when adding/editing a usage pattern.

## [0.8.11] - 20225-06-19

### Changed
- Change notification background color to respect e-footprint chart.
- Remove use of pandas for source xlsx export, to reduce memory footprint.

### Fixed
- Fix notification after an object deletion.

#[0.8.10] - 2025-06-23

### Fixed
- Fix chart resize issue when panel result is opened during an edit.

### Changed
- Upgrade to e-footprint 10.1.11 for 2x lower memory footprint.
- Disable browsers zoom when users touch an input
- Scroll to top when sidePanel is displayed

## [0.8.9] - 2025-06-23

### Fixed
- Truncate system name to 50 characters + normalize characters when exporting it into JSON file.

### Added
- Sources for the UsagePattern form have been added.
- Sources for all attributes with ExplainableObject type (like genAI model and provider) have been added.

### Changed
- JS logic related to sources has been updated to take in account sources for value/unit fields in addition to simple fields.
- Put timeseries form at the end of usage pattern form.

## [0.8.8] - 2025-06-18

### Changed
- Upgrade to e-footprint 10.1.10 for massive performance improvements in 
  model computation (10x 🙌!).

### Fixed
- Device selection when editing UsagePatternFromForm.

## [0.8.7] - 2025-06-17

### Changed
- The select multiple field for UsageJourneyStep in UsageJourney and for 
  Jobs in UsageJourneyStep form has been updated to use a new component for a
  better user experience and allows user to re-organize the order of selected 
  items.

## [0.8.6] - 2025-06-12

### Fixed
- css issue of full height of the model between Safari and Chromium browsers.

## [0.8.5] - 2025-06-12

### Fixed
- scroll issue on small screen after adding a new object.

## [0.8.4] - 2025-06-12

### Fixed
- Remove all object highlighting when adding a new object.  

### Changed
- Update UI to implement responsive design. The interface now adapts to different screen sizes, ensuring a consistent user experience across devices.
- Updates HTML/CSS part to simplify the code and improve readability.

## [0.8 3] - 2025-06-11

### Fixed
- ModelWeb.to_json() to include objects not linked to any System when downloading json file.
- upgrade to e-footprint 10.1.7 to fix object deletion logic.

## [0.8.2] - 2025-06-10

### Fixed
- Call generic self_delete() method when deleting UsagePattern, to make sure that its Devices, Network and Country are deleted if they are not attributes of any UsagePattern anymore.

## [0.8.1] - 2025-06-10

### Fixed
- Save calculated attributes to json for objects not linked to system + upgrade to e-footprint 10.1.6 so that server and system recompute their attributes when a service is installed on a server.

## [0.8.0] - 2025-06-04

### Changed
- Cache calculated attributes and update model in real time as the user interacts with it.

## [0.7.23] - 2025-05-26

### Added
- Highlight the object in the model canvas when the user clicks on i. If it is a mirrored object, the corresponding objects are also highlighted in the model canvas.

### Changed
- Load e-footprint objects in settings.py so that they are already loaded even in the first user interaction.

## [0.7.22] - 2025-05-22

### Added

- Edit icon appears when hovering over an object name in object cards.

### Fixed
- Remove " ' " for exported json filename.

### Changed
- Minimum number of instances is set to 1 so that BoaviztaCloudServer doesn’t get reimported every time the first instance is created.

## [0.7.21] - 2025-05-15

### Changed

- UI has been updated to use d-flex components instead of row/col for more 
  flexibility.
- Updates in CSS to unify rules about object addition.

## [0.7.20] - 2025-05-15

### Fixed
- Provider edit when result panel is open. Now ModelingUpdate is used to update both provider and model name so that e-footprint doesn’t raise an error when provider is updated.

### Changed
- Datalist values (for example gen AI model name) now have same logic as name field: in the add panel when clicking the value is deleted.
- When opening the confirm delete modal, the side panel is not closed anymore so that clicking "go back" allows to go back to the side panel.

## [0.7.19] - 2025-05-12

### Changed
- Change behavior of the result panel to allow its display when side panel 
  is open. A side panel form submit if the result panel is open now triggers 
  a recomputation of the model.

## [0.7.18] - 2025-05-13

### Added
- On add/edit/delete object, a toast is displayed to inform the user that 
  the action has been successfully completed. For Add and Edit, related 
  objects are highlighted in the model canvas.

### Fixed
- Object name in edit panel remains after clicking on the name field.

## [0.7.17] - 2025-05-07

### Changed
- Simplify server labels but keep more descriptive labels for server type selection.
- In usage pattern form, for new usage patterns, the field initial_usage_journey_volume isn't set to a default value and the timeseries chart isn't diplayed. Once all informations are filled, the chart is displayed.
- Refactoring: In SCSS file, remove all references to property z-index and use bootstrap class instead. For leaderline, use z-index defined in bootstrap variables.

### Fixed
- Leaderline z-index is now below upload and download toolbar.

## [0.7.16] - 2025-05-06

### Fixed
- Backend and frontend updates to use form units in the edit/add views. This allows for uploading models with units different from default units and keep unit consistency.

### Changed
- In code, rename duplicated cards to mirrored cards.
- Round usage projection figures to 1.
- Form fields steps (for example, step is now 1 for electricity carbon intensity, instead of 0.1).
- Automatically round integer default values (to display 100.0 as 100 for example)
- In forms remove object type sections when there is a single object type to select (for example, job type in job form).

## [0.7.15] - 2025-05-05

### Changed
- Re-put yearly emission breakdown as default + use CO2-eq as emission unit
- Update to e-footprint 10.0.11 gives better default units especially for carbon intensity of electricity (gCO2-eq/kWh and not kgCO2-eq/kWh)

### Fixed
- Result charts labels (sometimes cumulative emissions line chart had yearly labels when it should always be monthly).
- Use GPUJob instead of Job when making a request to a GPU server, to use the right compute unit.

## [0.7.14] - 2025-05-05

### Changed
- Result panel has been updated to have both dashboards on large screens and a single dashboard by row on small screens.
- Refactor HTML part in base/home/moder_builder/result to reduce useless 
  components and improve readability.
- Refactor CSS part to improve sizing(specifically for components height) 
  system.
- Update SCSS rules about popover to render tooltips more readable.

## [0.7.13] - 2025-04-28

### Changed
- Increase side panel width on small (<1200px) screens.
- Change CSS rules to improve the overall display
- Refactor the CSS part to be fully managed into SCSS files and re-organize 
  the custom SCSS file.
- Add custom labels for calculated attributes.

### Fixed

- Available job types show now the label instead of the class name in the 
  select field
- In Safari select multiple fields don’t have a visible hidden value anymore, while retaining the fact that the forms will always send a value for select multiple fields, even if no value has been selected.
- Number format in charts y axis (from indian to english format)
- Deletion logic for mirrored cards (for example, trying to delete a job that belongs to a mirrored user journey step would raise an error).

## [0.7.12] - 2025-04-23

### Fixed

- Fix charts in result panel and usage pattern time series form to always 
  start Y-axis at 0.
- Fix issue with tooltips on upload_and_download template. The tooltip now 
  is not persistent after the click and disappears.
- Remove accordion behavior from usage pattern card.

## [0.7.11] - 2025-04- 17

### Added

- Add Y-axis title "Number of usage journeys" and change label displayed in 
  the tooltip.
- Add a tooltip component for each field in the forms to give more details 
  when a tooltip key for this field is defined in the reference file.

### Changed
- Name field automatically empties when clicking but resets back to default when empty and unfocus.
- Usage pattern form fields order.

## [0.7.10] - 2025-04-17

### Fixed
- Fix usage pattern edition form to avoid accordion component into another 
  accordion.

### Changed
- A section in forms "Advanced options" has been added to included fields 
  which require more technicals knowledge. This section can be expanded or 
  hidden and all fields in this section can be edited.

## [0.7.9] - 2025-04-16

### Changed
- The page "Understand" has been removed due to outdated contents in this 
  section. fore more details about e-footprint, please refer to the documentation
- Object and field wordings have been updated.
- Empty multiple select lists are not displayed anymore (for example, when creating a new usage journey but there are no usage journey steps in the system, or when creating a new usage journey step but there are no jobs in the system).

### Fixed
- Result modal now always close side panels.

## [0.7.8] - 2025-04-15

### Fixed
- Use correct labels for objects in forms and sources.

### Changed

- Minimum set to 0 except for inputs that can be negative (job data stored attribute for example).
- Possibility to define custom numerical input step for each attribute (for example, the compute step is 1 in server form and the average carbon intensity step is 0.01, default is 0.1).

## [0.7.7] - 2025-04-14

### Fixed
- Harmonize usage pattern time series css with other object forms.

### Changed
- On result panel, the number of decimal digits is now set to 2 for tooltips in charts.
- for all charts, the month format is now always in english (Jan. Feb, Mar...)
- Add two reference files to overwrite fields label in forms additions and editions and give to users a better understanding of the fields.

## [0.7.6] - 2025-04-11

### Changed

- A source array is available in the results panel for all numerical inputs with the possibility to download it.
- In side panels, for each field, if a source is available, it is displayed bellow the field.

## [0.7.5] - 2025-04-11

### Fixed

- Fix issue linked to click on the browser back button (loading bar not stopping and all buttons not working anymore).
- Result footprints unit conversion (kgs were displayed as tonnes).

## [0.7.4] - 2025-04-10

### Fixed
- Usage pattern time series chart JS options were those of result panel, now they are back to the 
  original ones. Fixes https://github.com/Boavizta/e-footprint-interface/issues/14
- When deleting modeling duration in usage pattern form, the time series chart is not updated so the field can be empty. It is still required for form submission though. Fixes https://github.com/Boavizta/e-footprint-interface/issues/16
- Update to efootprint 10.0.9 to fix date errors due to DST conversions.
- Round UsagePatternFromForm number of days to previous int to avoid having an extra day in next modeling year because pint year duration is 365.25 days.
- Select existing list attributes when updating parent object. For example, when editing a UsageJourney the UsageJourneyStep list had no object selected. Now the right objects are selected.

## [0.7.3] - 2025-04-07

### Changed
- UsagePatternFromForm form fields now have same formatting as other object fields.
- Name field is now included in object form section
- When changing value of filtering dynamic list, corresponding datalist value is erased.

## [0.7.2] - 2025-04-03

### Changed
- Exported JSON files now contain the mention 'UTC' in the filename.
- Change error message before computation relative to missing step in a 
  UsageJourney.
- Raise an error modal when the user tries to create a job with no servers.

### Fixed
- Fix CSS unalignment rules on timeseries part form in Usage pattern form.
- Fix max timeframe value when editing usage pattern time series with modeling duration initially setup in months. The max value for the timeframe field would keep being 10 instead of 120.

## [0.7.1] - 2025-04-02

### Changed
- Updated to e-footprint 10.0.6 so Boaviztapi calls are now done through the python package and not through the API anymore.

### Fixed
- Updated to e-footprint 10.0.6 so BoaviztaCloudServer compute and ram values are fixed (they used to be vastly overestimated which resulted in underestimation of environmental impact).

## [0.7.0] - 2025-03-31

### Changed
- In add end edit server panels, there is now a dedicated part of the form to define 
  storage attributes.
- In edit panel, storage calculated attributes are displayed when available.

## [0.6.8] 2025-03-27

### Fixed
- Make sure all footprint values share same period index and compute daily aggregation server side instead of client side. This fixes results in case the model is made of usage patterns with disjoint time periods.

## [0.6.7] 2025-03-25

### Changed
- In result panel time granularity can now only be chosen for bar chart and not for line chart anymore.
- In result panel monthly and yearly values are expressed in a calendar way (e.g. january 2025) instead of with dates.

### Fixed
- efootprint rounding error by upgrading to 10.0.4
- Possibility to have user journey with duration of 0 by upgrading to efootprint 10.0.4

## [0.6.6] 2025-03-20

### Changed

- Add a default UsageJourney and a default UsageJourneyStep 
  in default modeling.
- Display an exception modal when the model can't be computed due to usage journeys with no steps.

## [0.6.5] 2025-03-18

### Changed
- Model can now be named and the name can be changed.
- Tooltips now have hover text.
- JSON export filenames follow this pattern : "[date/time] [model name].e-f.json".

### Fixed
- SVG url for usageJourney in understand page has been fixed.

## [0.6.4] 2025-03-17

### Changed
- Add default object names for new objects (object type + object, e.g. UsageJourney 3).

## [0.6.3] 2025-03-17

### Fixed
- Initial number of visits on first day is now computed so that the sum of visits over the first initial usage journey volume timespan is equal to user input. For example, if modeling start date is 2025-04-01 (April is a month with exactly 30 days) and the user inputs 10000 initial visits monthly, the sum of visits for April should be 10000 (despite the fact that growth is computed daily).

### Changed
- Force usage pattern date format to YYYY/MM/DD.
- Update Cypress test structure.

## [0.6.2] 2025-03-14

### Changed
- Side panel template has been introduced to have similar structure between all  
  creations/editions objects.
- Simplify the html structure of the model-canvas div.

### Fixed
- When results can’t be computed a modal is displayed to inform the user that the model is 
  incomplete but it was covered by the empty result panel which wasn't hidden.

## [0.6.1] - 2025-03-13

### Fixed
 - Updating modeling duration value in usage pattern form updates time series graph.
 - Start date is internally converted into local timezone start date in UsagePatternFromForm so that when it is converted to UTC it is the same date as the one selected by the user.
 - Make sure form inputs don’t overlay result chart.

## [0.6.0] - 2025-03-13

### Added
- Calculated attributes section in object edit panel to allow the user to explore computation graphs.

## [0.5.0] - 2025-02-24

### Changed
- Explode the navbar into a new navbar and a dedicated toolbar for the model 
  builder.
- Add a swipe effect to open and visualize the result panel.

## [0.4.5] - 2025-03-12

### Fixed
- Usage pattern time series form is now tested and usage pattern are now fully editable.
- fload input values in forms.

### Changed
- New usage journey, usage journey step and server cards are now open by default.

## [0.4.4] - 2025-02-24

### Fixed
- Leaderline updates when a model exists and user imports a new model.

### Changed
- js logic trigger management (code refactoring).

## [0.4.3] - 2025-02-21

### Fixed
- Temporary fix that increases precision of timeseries data for results, to avoid rounding effects. Will be better fixed when e-footprint’s to_json method is updated to have rounding depth as parameter.

## [0.4.2] - 2025-02-21

### Fixed
- Add usage pattern panel was broken (clicking on Add buttons didn’t open Devices Network Country or UsageJourney panels) when there was more than one usage journey in the model.
- Don’t use uuid-System-1 hardcoded anymore to allow for generic System ids in the model (useful when importing a model generated with e-footprint).

### Changed
- Don’t add default usage journey step to new usage journey anymore. 

## [0.4.1] - 2025-02-19

### Fixed
- Set input type as number and step as 0,1 for usage journey step duration, instead of type text.

## [0.4.0] - 2025-02-18

### Added
- Test suite and better release process

### Changed
- All model manipulation logic. Now the user has full freedom to create, edit and remove objects, and can visualize model results.

## [0.3.0] - 2024-11-20

### Changed
- Switch from the framework front-end Tailwind to Bootstrap.
- Minor changes in views and templates to match the new front-end framework.
- Fix python version to 3.11.10.
- Update README.md, INSTALL.md, RELEASE_PROCESS.md, DEPLOY_TO_PROD.md with new instructions.

## [0.2.0]  - 2024-11-07

### Updated
- Upgrade e-footprint version from 6.0.2 to 8.0.0. Objects relation and structure have changed, so the interface has been updated to match the new e-footprint version.

## [0.1.0] - 2024-10-01
- Upgrade e-footprint version from 2.1.6 to 6.0.2.

## [0.0.4] - 2024-06-17

### Added
- htmx request optimisation everywhere possible
- Loaders for almost every user interaction

### Fixed
- CI testing

## [0.0.3] - 2024-05-28

### Added
- Loaders in quiz flow

### Fixed
- Make global loader insensitive to mouse events with pointer-events: none.

## [0.0.2] - 2024-05-28

### Fixed
- Model reference setting logic

## [0.0.1] - 2024-05-24

### Added
- Global loader for navigation from left tab

### Fixed
- Remove current object creation or edition panel when opening a new one

## [0.0.0] - 2024-05-23

### Added
- Put first version of the interface in production !
- Basic quiz with service type selection
- Raw model builder interface with e-footprint object cards
- Possibility to set model as reference and compare with new version
- Put first version of the interface in production !
- Basic quiz with service type selection
- Raw model builder interface with e-footprint object cards
- Possibility to set model as reference and compare with new version
