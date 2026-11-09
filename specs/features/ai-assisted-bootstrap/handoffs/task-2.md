# Task 2 — Fresh-start and generation lifecycle

Repository and implementation range: `e-footprint-interface`, `406f21b0..781beeae`.
Companion library reference: `e-footprint` at `afc60887`, unchanged.

## Review pointers

- `views_ai_bootstrap.py` replaces the old endpoint with POST `start-ai-bootstrap` and `generate-ai-bootstrap`. `prepare_system_for_session` preserves the existing load path while allowing completeness validation before publication. Rejections render saved state through a fresh repository; storage failures retain ordinary exception handling.
- Task 3 integration: context availability is `AI_BOOTSTRAP_AVAILABLE`. Both response-local panels carry `data-ai-bootstrap-panel="input"` or `data-ai-bootstrap-panel="summary"`. Their existing shell opens `#sidePanel`; the input form targets `#main-content-block` and directly declares `hx-disabled-elt="button:not(:disabled)"`. Its submit block intentionally omits the shell's Results-recomputation onclick. Summary has no form or submit footer.
- Availability and inference read Django's configured `MISTRAL_API_KEY`; standalone evaluation retains environment-key resolution without configuring Django at import time. Test fixtures should set the flag and Django key together, and patch `views_ai_bootstrap.complete_mistral`.
- The former PoC test file now retains only developer edit/read-back helper checks for Task 4 removal. Durable architecture/AGENTS guidance and consolidated changelog remain Task 4's named documentation work.
