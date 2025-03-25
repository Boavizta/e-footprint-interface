# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

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
