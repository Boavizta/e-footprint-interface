# AI assistance roadmap

Updated 2026-11-06. Interface-owned. This roadmap records direction, not implementation approval.
Each extension gets its own specification before planning and implementation.

## First production feature — AI-assisted bootstrap (spec approved; planning pending)

[AI-assisted bootstrap](../ai-assisted-bootstrap/spec.html) turns a description into a first web modeling,
then hands refinement to the existing manual editor. Bootstrap works independently for the reference
and comparison modelings, targeting only the active modeling. One configured model: `zai-glm-5-3-flash`, hosted by
Mistral. Synchronous execution is an explicit first-release choice; other requests may wait. No overlap
monitoring, concurrency experiment, background job system or AI editing is required for this release.

The feature includes guided description entry, beta and AI disclosures, an inference summary with cost
and a clearly qualified EcoLogits parent-model impact estimate, and a small toolbar cleanup. It remains
approved at the specification stage on 2026-11-06; the draft plan still requires a fresh spec-plan session and approval.
The summary is shown once after generation and is discarded when its side panel is closed or replaced.
Users save their own prompt; there is no summary-reopening action or report retention.

The [PoC](../ai-assistant-poc/spec.html) established the experimental generation/edit paths. Production
delivery must extract reusable generation code, keep useful generation evaluation tools, remove the
AI editing/read-back path and experimental UI, and stop logging prompts and responses. Git history
preserves the removed experiment. Close/archive the PoC only after the replacement ships and its
remaining lessons are promoted; creating this roadmap does not mean that close-out has happened.

## Ordered follow-ups

### 1. Extend bootstrap to edge modelings

Build on the shipped web bootstrap. Support descriptions of edge devices and fleets, edge usages,
deployment counts and the infrastructure those usages depend on. Reuse the library's modeling truth
and preserve explicit assumptions. Evaluate edge-specific failures such as devices per site versus
total fleet count, shared equipment and repeated deployment quantities.

Specification must settle whether web, edge and mixed descriptions use separate guided paths, and
how edge functions connect to server workloads without double counting. The earlier separate-path
idea in [the exploration](README.md#separate-web-and-edge-paths-to-explore) is a hypothesis, not an
already approved architecture. Extending bootstrap does not authorize editing an existing modeling.

### 2. Handle AI provider I/O asynchronously

Remove occupation of a synchronous web worker while waiting for the provider. Preserve the guided
bootstrap, failure feedback and review summary. Specify the execution and user lifecycle before
choosing infrastructure: freeing worker capacity during an open request is different from durable
background jobs that survive navigation, restarts or deployments.

The first production release knowingly permits other requests to wait. No overlapping-request
monitoring or concurrency experiments are prerequisites for it. This follow-up is planned direction;
its relative position follows the user's chosen order, not an automatic traffic threshold.

### 3. Confirm Boavizta API ownership and provider contract

After asynchronous processing, coordinate with Boavizta to use a Boavizta-owned provider account
and API key. Clarify who holds the provider contract, owns billing and manages credentials, and
confirm that the agreed terms cover the service's use and handling of submitted data. Record the
outcome and align the application's provider disclosure with it.

## Later possibilities — unordered, no commitment

- Narrow AI value changes, using shared editor mutation rules and preserving hand-entered values,
  sources, comments, weights, dates and Simplified-input selections.
- Broader structural editing only when object identity, unlink/delete semantics, shared children,
  ordering and save behavior are explicit. Coordinate with
  [Clean Architecture refactoring](../clean-architecture-refactoring/README.md); a complete wrapper
  relocation is not a prerequisite for bootstrap.
- More targeted description guidance or clarification, only when it earns its extra interaction
  and inference cost. No chat, classifier or conversation memory is implied by this roadmap.

Retain the editing experiment's lessons rather than unused production code: the DSL read-back is
lossy, names are imperfect identities, re-lists can create orphans, shared children and relationship
weights must survive, and failed batches must not partly change saved state.

## Historical context

[The exploration](README.md) preserves earlier ideas and historical cost hypotheses. Its multi-round
assistant, provider comparisons and classifier proposals do not define the first production scope.
Current choices come from the production feature's reviewed specification and plan.
