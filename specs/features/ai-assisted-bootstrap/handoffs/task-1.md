# Task 1 — Shared generation, provider and metrics

Repository and implementation range: `e-footprint-interface`, `497fe2c77209e03877c7a0a5a62f3fa6db8c429a..73b07951`.
Companion library reference: `e-footprint` at `afc60887fa05c34d18d5969a45276bb08d3dace0`, unchanged.

## Review pointers

- `application/ai_bootstrap/service.py` exposes `generate(description, complete)`, `build_answer(text)` and the request-local contracts from the plan. `adapters/ai_provider.py` exposes `complete_mistral(system_prompt, description)`, `ProviderError` and the lazy flag-plus-environment-key helper `is_available()`.
- `estimate_call()` returns usage/latency, nullable `cost_usd`, `rate_card_date`, `cache_discount_unknown`, nullable scalar/range `impact_kg`, and explicit `impact_provider`/`impact_model`. The summary consumer must present the unknown-cache caveat and qualify the unscaled parent estimate. The SDK receives `NoOpLogger` explicitly because its default otherwise honors `MISTRAL_DEBUG`.
- Evaluation uses the shared builder; Flash dispatch delegates to the bounded adapter. Other providers retain developer-only completion metadata. The CLI stops launching calls if cost becomes unavailable and marks its known subtotal incomplete. Snapshot refresh remains `python -m ai_sandbox.catalogs refresh`; ordinary CLI entry is now `python -m ai_sandbox.run`.
- The still-live PoC view/edit helper/tests use moved package imports until their planned retirement. Task 4 owns durable architecture/AGENTS routing documentation and the consolidated production changelog.
