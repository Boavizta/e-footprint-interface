# Usage-journey browser benchmark

This opt-in benchmark replays four sequential usage journeys in one isolated browser session: explore the maintained
e-commerce example, enrich it, duplicate and compare an alternative, then export/import, audit and export it again.
It uses the regular synchronous pytest/Playwright stack and records UTC action boundaries plus every browser request.
Request URLs retain only origin and path: query strings, bodies, response content and cookies are never written.
Opening Results is one browser action, but its automatically launched `/sankey-diagram/` request is labeled B6 in the
request dataset while `/result-chart/` remains B5, preserving the measurement contract's server-operation boundary.

Start the application, then run:

```bash
poetry run pytest specs/e-footprint-modeling/benchmarks/test_usage_journeys.py \
  --run-usage-benchmark \
  --base-url http://localhost:8000 \
  --usage-benchmark-output specs/e-footprint-modeling/benchmarks/results/local \
  -q -s
```

Use the same command with the production base URL (without a trailing slash) and `results/prod` only during a
coordinated calibration run. Each run writes a unique directory containing `benchmark.json`, `actions.csv`, and
`requests.csv`. The run id is also sent in the
`X-Efootprint-Benchmark-Run` request header; timestamps remain the fallback when the hosting logs do not retain it.

Raw run directories under `results/local/` and `results/prod/` are local evidence and are intentionally ignored by
Git. Keep them until the campaign has been reviewed, or archive them outside the repository if a later audit requires
the request-level traces. Run-id campaign manifests are local for the same reason.

Version the reviewed summary, journey summary, and compact per-action evidence instead. The operational-model generator
reads `results/2026-09-15-action-evidence.json`, which retains every local median, the production observation, the
common calibration factor, and the calibrated duration used in the generated models. Modeling generators and their
JSON outputs belong in the adjacent `../models/` folder.

For a warm-worker campaign, leave the local server running and repeat the pytest command. For example, ten
repetitions in zsh are:

```bash
for repetition in {1..10}; do
  poetry run pytest specs/e-footprint-modeling/benchmarks/test_usage_journeys.py \
    --run-usage-benchmark \
    --base-url http://localhost:8000 \
    --usage-benchmark-output specs/e-footprint-modeling/benchmarks/results/local \
    -q -s || break
done
```
