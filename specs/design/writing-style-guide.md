# e-footprint writing style guide

Scope: interface labels, docs, and training material. English (US spelling).

## Words

- The name **e-footprint**: always fully lowercase — even at the start of a sentence, and even
  where all-caps styling is otherwise applied (exempt it from `text-transform`).
- **UI element labels: initial capital only, always** — "Source: …", "Usage journey",
  "Add your usage journey", "Edge computer", "Edge storage calculated attributes".
  The object is a *Usage* journey, never "User journey".
- **Object names in running prose: lowercase** — "open the usage journey", "each job".
  Capital only when quoting the on-screen label.
- When pointing at the screen, quote labels **verbatim**, even where they deviate from this
  guide.
- Lifecycle phases in prose: **manufacturing** and **use**.
- **model vs modeling**: reserve **model** for AI models (veo-3.0, gpt-4o); the thing you build
  in e-footprint is a **modeling** ("you do not need an e-footprint modeling", "your
  modeling"). Never let a bare "model" mean the e-footprint one where AI models are in
  scope — which in this material is everywhere.

## Units

- **CO₂eq** for CO₂ equivalent — subscript ₂, no hyphen.
- **t** (lowercase) for metric tons.
- Otherwise ISO units with their exact capitalization: kg, g, Wh, kWh, GB — including in table
  headers (never apply uppercase transforms to units).
- One space between number and unit ("10 kg", "44 g/kWh"), non-breaking where possible.
  No space before % ("85%").

## Numbers

- Format: **1,345,000.10** — comma as thousands separator, period as decimal separator.
- Precision: **3 significant figures**, trailing zeros trimmed — the convention implemented in
  the core repo's `efootprint/utils/display.py` (`sig_figs=3`).
- Unit choice: pick the unit that makes the number read **≥ 1** ("3 mg", not "0.003 g") — also
  the core code's behavior (`best_display_unit`). Exception: a comparison table may fix one
  unit for the whole column, even if small values go below 1.
- Multiplication sign: **×** (never the letter x) — "×5", "10–100×".
- Ranges: en dash without spaces — "10–100×".
- Approximation: **~** before a number ("~2,000×"); **≈** between quantities ("1 clip ≈ 400
  prompts"). Pick one per document if both would appear side by side.

## Dates

- Fields, filenames, exports, anything machine-adjacent: **ISO — 2026-08-20** (what the
  interface already uses everywhere).
- Chart axes: abbreviated month + year ("Jan 2026") — the charting library's default; keep it.
- Running prose: **18 June 2026**.

## Localization note

These separators and date formats are the EN convention. A French version localizes them
(1 345 000,10 · le 18 juin 2026) — do not carry EN formats into FR text.
