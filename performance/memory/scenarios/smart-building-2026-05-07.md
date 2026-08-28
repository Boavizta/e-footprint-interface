# Smart-building shared-pattern stress case

External fixture: `2026-05-07 scenario C smart building system.json.json` (not copied into this repository).

The original 645 KiB JSON has two edge usage patterns sharing one usage journey, 154 recurrent edge workload needs,
154 recurrent edge workloads, 66 edge appliances, and 66 edge appliance components. Its 1,825-day duration expands to
43,800 hourly values per long array.

The profiler can duplicate the first usage pattern to three, four, or five patterns. These synthetic patterns share the
same journey. This is deliberately adversarial: serialized input size grows very little while pattern-keyed calculated
coordinates and their hourly explanation arrays grow approximately linearly with pattern count.

This case represents the production failure shape but not every topology. Future calibration should add independent
journeys, web-only systems, mixed web/edge systems, storage/cumulative calculations, and timezone/alignment cases.
