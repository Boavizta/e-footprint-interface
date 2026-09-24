# Spec-plan review feedback

Living notes from the Simplified inputs plan review, consolidated on 24 September 2026.
Keep updating these notes as review continues. They are input to a later, explicitly authorized
revision of the canonical spec-plan skill and its interface mirror, not changes to the skill itself.

## Reading experience

- The reviewer reads every sentence like code, assuming it carries meaningful implementation
  implications. Redundant prose is therefore misleading, not merely verbose: it suggests requirements
  that do not exist. Each sentence must convey a concrete change, constraint, necessary rationale or
  decision. Leave ordinary behavior implicit and clearly distinguish examples from special-case rules.
- The reviewer has the approved spec fresh in mind. Avoid a verbose introduction or repeating the
  feature's UX and requirements; link back to the spec when necessary.
- Make the plan feel like a high-level code review: the reviewer should be able to picture the
  resulting code, not just understand an architectural intention.
- Start with meaningful new data structures, then tell a logical story through the code changes in
  a deliberate reading order. This does not mean inventing new structures to fill that section.
- After the shared data, organize by functional surfaces and interactions, not by technical layers.
  The reviewer wants to picture an interaction and follow the code implementing it: Configure;
  author in Modeling/Sources; consume and edit; navigate and exchange models. Keep the Examples
  rename separate. Introduce shared helpers with their first consumer, then link back instead of
  repeating them. The reading order need not be the implementation dependency order.
- Remove low-value implementation asides rather than explaining them at length. Specific rejected
  example: “It excludes self, not fields merely hidden by a particular form.” The meaningful
  boundary was already explained by keeping form-specific display rules in the adapter.
- Omit statements of ordinary behavior: “Saving partway through curation is allowed” merely
  restates what Save does, without adding a requirement or implementation decision.
- Clarifying a passage should not continually expand it. State the purpose plainly, use one concrete
  example, and remove repeated wiring explanations and secondary caveats. For `FieldCatalog`, the
  approved shorter explanation is the two questions it answers (eligibility and required companion
  fields), one API/Resolution example, and its shared use by configuration/save/import. “Reverse
  dependent edges” and persistence/rendering caveats obscured that point in the main reading flow.
- Simplify verbose edge-case sections before adding labels such as “agent-only” or “optional”.
  Remove repeated spec rules, preserve the genuinely new implementation points, and leave review
  decisions visible. A collapsed section is not a substitute for editing.
- Prefer the feature's concrete vocabulary over unnecessary technical labels: “timeseries editor”,
  not “composite editor”. Describe loading it beside the Edit timeseries interaction, not in Configure.
- Describe UI transitions precisely: deselecting an object's last included input can hide that object;
  say “keyboard focus” and name its destination, not “moving focus before hiding the last selected object”.

## Files, code and visual navigation

- Replace the hard-to-read affected-files table with a filesystem-like hierarchy. The current tree
  is in the right direction; retain an accessible overview of the changed files.
- In this interface plan, paths in the walkthrough and code titles are relative to `model_builder/`.
  Use `adapters/forms/...`, not `forms/...`; explicitly mark paths outside the base. Tree labels can
  remain relative to their enclosing folders. A future generic format should state its chosen base.
- Every code block needs a small title naming its owning file. Split multi-file sketches rather
  than leaving ownership implicit; identify payload examples as payloads, not repository files.
- Show the structure of central return types, not just their names in signatures. The reviewer
  asked to see `FieldCatalog`: its field-address lookup and direct-dependent lookup explain the
  design more concretely than additional prose. Keep these sketches minimal and file-labelled.
- Surface new data structures and extensions to existing structures beside the interaction that uses
  them. Show the actual proposed shape, mark existing versus new fields, name the producer and consumer,
  and explain the behavior driven by the data. For creation-time required inclusion, extending an existing
  `dynamic_lists` entry with `simplified_required_by` made “attach required-selection context” concrete.
- Presenter examples should expose what the view needs explicitly. Replace the opaque
  `"definition": definition` with `title` and `guidance`; keep membership/help only beside each
  field rather than also passing the full configuration through a second path.
- Name concrete identifiers instead of saying “model and field identity”: System ID, field owner
  ID and attribute. Do not leave the reader guessing whether “model” means its name or workspace slot.
- Name where proposed helpers are defined and show who passes or calls them. The phrase
  “server-wired boolean callback” hid the location and use of `can_edit_timeseries`; a short
  file-titled function plus the view/use-case/catalog call sequence made the proposal concrete.
  Prefer ordinary function/argument language to dependency-wiring jargon when that is all it means.
- Separate browser draft feedback from server enforcement and persistence. Name the use case instead
  of “the save use case”, and distinguish selecting an input for inclusion from editing its value.
  In Configure, dependency feedback updates the browser draft; Save and return calls
  `UpdateSimplifiedDefinitionUseCase`, not the consumption value-edit use case.
- Keep form values in the DOM, not a second JavaScript configuration object. The later decision to
  gate leaving Configure supersedes per-property dirty tracking and partial Configure submissions:
  one form-level dirty flag and a complete form submission are enough.
- Prefer a simple Save / Discard / Stay exit guard over preserving low-value Configure drafts and
  reconciling them with inline bookmark saves. Reopen saved settings with default layout/filter state;
  do not add scroll/expansion/filter restoration. Keep the useful per-model base-view choice separate.
- Describe rendering per interaction: Configure Save returns the complete Simplified inputs view;
  inline bookmark/value saves use targeted updates to preserve other unsaved controls. Do not imply
  field-change tracking is needed for a full-view response merely because the saves share a result type.
- Separate shared controls from their presentation wrapper. Configure includes `selection_controls.html`
  directly; creation/edit panels and Sources use the `bookmark.html` disclosure around it. Consumption
  includes neither. Shared markup does not imply shared save timing: Configure and creation defer their
  settings to their form save; existing-input bookmarks save immediately.
- Explicitly label defense-in-depth checks when the server re-enforces a rule already reflected in
  browser feedback. Explain the gap covered (bypassed or stale client state), while making clear that
  server enforcement is authoritative, not optional duplication.
- An arrow between two filenames is ambiguous. Do not use it as a decorative file-list separator.
  If an arrow expresses a call, import or data flow, make that meaning explicit.
- Remove the generic approach diagram from this plan: it repeated familiar spec concepts and was
  difficult to read. Diagrams are useful when they clarify a real code relationship or sequence.
- Still being tried, not a universal requirement: code-linked flow diagrams near relevant steps,
  links into the file tree, and highlighting the files associated with the current reading step.
  Non-code diagrams are also acceptable where they genuinely add understanding.

## Existing code, refactors and new behavior

- Ground proposed behavior in the affected code path, including relevant success, failure and
  cancellation handling—not architecture prose alone. Distinguish existing behavior, feature-required
  changes and optional improvements while planning; surface only the meaningful delta in the plan.
- Require a concrete agreed requirement for added state, queues, reconciliation, recovery or validation
  machinery. Compare against the simplest extension of existing behavior first. Generic robustness
  language must not silently authorize a refactor. This is a planning check, not another verbose audit
  section for the reviewer; lack of evidence requires inspection or an explicit uncertainty.
- Run that complexity audit before asking for human review. The user identified this as an important
  part of the eventual spec-plan update: trace the relevant existing paths, justify each added mechanism
  against the agreed behavior, and remove requirements accidentally introduced by prose. Do not make
  the reviewer discover these costs sentence by sentence.
- Applied audit outcomes for this plan:
  - Reuse side-panel discard protection on model switches; remove timeseries draft parking and
    preview teardown/restoration. Same-model Compare return already retains the resident panel.
  - Prevalidate incoming models before replacement, but defer transactional storage publication and
    cache-write reporting as SI-2. Do not present an existing storage gap as a feature-required refactor.
  - Keep one multi-owner value update, while reusing request-local metadata mutation and persist-on-success.
    A separate deferred-metadata layer adds no needed persistence protection here.
  - Guard simplified autosaves and Configure on export; do not invent an existing warning or add new
    unsaved-export behavior to ordinary Modeling panels.
  - Keep the required Examples rename independent; it is not a prerequisite for the eligible-field catalog.
  These are code-backed decisions for this feature, not universal prohibitions on draft retention or
  transactions. Synchronize the file tree, snippets, sequence, tests and spec when cutting a mechanism.
- Verify existing error behavior before promising draft preservation. Creation currently shows an
  error modal and clears the side panel; retain that flow here rather than silently adding recovery
  machinery. Pending simplified-input settings must not persist on failure. Any improved recovery UX
  needs explicit scope and implementation cost, not an incidental sentence.
- Inspect existing mechanisms before proposing new services, registries or discovery pipelines.
  The review question “Isn't there anything in the current code that does similar work?” exposed
  substantial overlap with existing form generation, timeseries support and input validation.
- Explain a refactor through three concrete parts: what currently happens, what changes or is
  extracted (and who uses it), and what genuinely new behavior is added. Identify what stays intact.
- Give concrete shapes/examples when a proposed contract is unclear. The question about
  `conditional` showed that `Mapping[str, Any]` obscured the existing `depends_on` and
  `conditional_list_values` structure. Do not imply a new declaration format where none is needed.
- Each new abstraction must earn its place. In this review, `describe_inputs()` and `InputDefinition`
  merely combined existing signatures, annotation normalization and class metadata. The user
  approved removing them rather than introducing another metadata representation.
- Approved narrower approach for section 1.2: read existing signatures/class metadata directly;
  share dotted-path resolution and lightweight timeseries builder lookup; keep new code focused on
  field addresses, eligibility and required dependent selections. Do not retain caller migrations
  or changed-file entries that were justified only by the rejected metadata wrapper.
- The catalog is an eligibility/dependency index, not a second schema or editor registry. Existing
  form dictionaries remain the rendering context. Show that distinction in the proposed code.

## Evidence and requirement fidelity

- Plan tests around meaningful behavior and regression risks, not every implementation detail.
  The reviewer rejected a spy assertion proving the small timeseries-support helper never calls
  `default_inputs()`. Keep supported/unsupported eligibility cases in catalog tests instead;
  do not add a separate internal-call prohibition without a concrete risk that justifies it.
- Support material edge-case questions with a concrete scenario from current code. The reviewer
  challenged the hypothetical “Modeling makes a required dependent ineligible” question and asked
  for an example. Do not turn an unproven hypothetical into a forced product decision.
- Distinguish existing validation from new checks before proposing more validation. Library value
  checks already handle unresolved conditional targets and allowed choices; simplified-selection
  validity is new. Blanket cycle rejection was not established and was removed from the proposal.
- Omit reminders about unchanged library value validation from the catalog/form-building flow.
  Explain new selection validation with configuration saves. Mention existing value validation only
  where our changes affect its invocation, such as one atomic batch of conditional value changes.
  Minor traversal details do not need their own review paragraph.
- Separate implementation complexity from UX tradeoffs. The user chose one-at-a-time autosave:
  temporarily block further edits/actions during saves rather than introducing a queue, manual batch
  commit or automatic/manual toggle. Extend existing request protection before inventing new machinery.
  Preserving failed simplified-input edits is required in every approach, not a comparative cost unique
  to autosave or permission to change ordinary creation/edit error handling.
- Record confirmed bugs with evidence and ownership, not a UI workaround. The shared-controller
  overwrite defect is tracked in `known-issues.md` as SI-1, including its reproduction and planned
  library regression; it remains unfixed during planning.
- Separate confirmed requirements, implementation proposals and unresolved product decisions.
  For example, automatic inclusion of a newly created video job's dependent Resolution was kept
  open until confirmed. The agreed refinement previews inclusion during creation, locks removal only
  while required, leaves help editable, and persists with successful creation. Update all outstanding
  review notes and spec exceptions together when a decision is made.
- Preserve the latest product decisions instead of carrying stale wording into implementation.
  Concrete correction during review: display custom help as authored, not forced lowercase.
  This is feature behavior; the general planning lesson is to avoid silently adding transformations.

## Iteration boundary

- Continue iterating on this feature's plan before updating spec-plan. The user explicitly asked
  not to update the skill yet, and subsequently asked to retain the feedback for that later pass.
- Respect discussion-only requests; explanations are not permission to edit. Apply changes when
  requested and keep the plan, file tree and related summaries consistent.
- The user subsequently authorized an editorial pass over the rest of this plan using the accumulated
  feedback, to reduce repetitive review rounds. Apply the lessons consistently, but do not silently
  resolve open product decisions or use this permission to implement code or update the skill.
- No application implementation or task generation is authorized by these review edits. On
  23 September the user requested a checkpoint commit before reorganizing the reading order;
  on 24 September they approved committing the interaction-led reorganization. The reusable skill
  is unchanged.
- When a skill revision is eventually authorized, use these notes and the reviewed plan together.
  Distinguish explicit preferences from still-experimental layout choices; do not mechanically
  promote every detail of this one feature into a universal planning rule.
