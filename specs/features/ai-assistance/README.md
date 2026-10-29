# AI assistance exploration and session handoff

Context saved on 2026-10-27 from a discussion begun on 2026-09-24. This folder belongs to the interface repository because the proposed feature is driven by the interface, even if later experiments or implementation require library changes.

**Status: exploratory discussion.** The user authorized creating this folder and preserving the conversation. No AI sandbox, benchmark runs, production integration, formal feature specification, or HTML mockups have been implemented or approved in this conversation. The proposals below are hypotheses to examine, not settled design decisions.

## Resume here

1. Read this document, then the current [architecture index](../../architecture/index.html), [mission](../../mission.md), and [constitution](../../constitution.md) as needed.
2. Continue as a thinking partner. The user's latest instruction is: **“Don’t make edits until I tell you explicitly. By default, we are discussion and I want your unbiased, constructive opinion. Don’t agree with me just to please me.”** This handoff-writing request does not authorize subsequent implementation or paid experiments.
3. The discussion started with `/spec-specify`, but the user explicitly deferred writing HTML files until they say to proceed. This Markdown context record is not a formal spec or plan.
4. The latest substantive question was how to design and prove this feature through an inexpensive AI experiment sandbox before investing in implementation. The assistant proposed an experiment brief and three reviewed cases as the next concrete deliverable; the user has not yet approved their creation.
5. Recheck current code and provider capabilities before making implementation choices. The interface has evolved since the initial discussion; its architecture entry point is now `specs/architecture/index.html`, replacing the earlier `specs/architecture.md` reference.

## User goals and constraints

The feature should dramatically reduce the time and expertise needed to create and interact with an e-footprint modeling. The interface is hosted by the Boavizta association, is free to use, and is itself a green IT tool: the assistance must be frugal, maintainable, and well ecodesigned.

The desired outcome is a complete, moderately complex modeling created in **3–6 iterations**, with a **mean AI cost around USD 0.01**. The user described **USD 0.10 as an absolute maximum for the mean cost**; this is not yet a defined per-session hard cap. They explicitly prefer experimentation over premature cost optimization, while using upfront orders of magnitude to assess feasibility. Do not depend on future price declines to establish feasibility.

The primary audience includes non-technical product people with no modeling background. Numerical plausibility alone is insufficient: the resulting model should remain understandable, editable, and honest about its assumptions.

## The user's initial approach

These were explicitly offered as ideas that could be challenged:

- Prefer a description space and explicit feedback button over a verbose free-form chat. Feedback could ask for volumes, main usage journeys, or other missing information.
- Use a low-cost classifier such as [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), supplied with e-footprint expertise and routing choices, to select feedback and clarifying questions. Distinguish what the user knows from what AI must hypothesize.
- Once the description is ready, have an LLM generate the object structure with defaults, potentially using the library's `from_defaults` behavior. Iterate on semantics and relationships before refining unknown values.
- Support assistance on existing models, possibly with a user-controlled draft state indicating whether the work concerns structure or numerical inputs.
- In a later mode, refine numerical assumptions, especially technical job characteristics, using compact model context and key figures. Update relevant fields only, with rationales in comments and evidence in sources.
- Keep server sizing deterministic where possible. Jev might also help select which fields need attention.

## UX proposals and challenges raised

The assistant suggested a persistent editable brief alongside the actual model canvas, with four activities:

| Activity | User interaction | Assistance |
| --- | --- | --- |
| Describe | Edit the brief and answer targeted questions | Identify gaps, ambiguities, and useful starting examples |
| Review structure | Inspect objects and relationships; request corrections | Generate and update a model structure |
| Improve assumptions | Review a short prioritized list of inputs | Propose values, questions, evidence, and explanations |
| Explore | Select objects or results and request help | Explain results, identify influential assumptions, propose comparisons |

A possible five-round journey is: check description → complete description and generate → correct structure → refine assumptions → review results. These are user rounds, not API-call counts.

### Interaction principles to test

- Retain short free-text instructions such as “Add a nightly export,” while making accepted facts and model state authoritative instead of replaying an expanding conversation transcript.
- Ask a small group of useful questions, with an “I don’t know / use an assumption” option. Example: does “50,000 users” mean registered users, monthly active users, or daily visitors?
- Clarify purpose, scope, and journeys early. Permit an early sketch with visible gaps; classifier readiness should be guidance, not an opaque gate.
- Separate assistance modes, such as **Edit structure** and **Improve assumptions**, from actual model maturity. A model can contain both reviewed inputs and newly added uncertain components.
- Preserve numbers already supplied by the user during structure work. “Structure first” should defer unknown numbers, not discard known ones; some quantitative facts influence structure.
- Preserve established values and sources when switching modes. Flag assumptions affected by structural edits.
- Show proposed changes and support acceptance, editing, and undo. Make default-filled results visibly provisional.

### Separate web and edge paths (to explore)

Assistance will probably follow three independent paths rather than one generator covering everything:

- **Web**: usage journeys, steps, jobs, servers, and GenAI APIs, sized from demand.
- **Edge**: deployed devices, edge functions, and deployments, sized from fleet counts, ratios, and device footprints.
- **Connection**: linking edge functions to the server jobs they call, once both sides exist.

Each path keeps its prompt, vocabulary, and checks small, which suits small models; the two paradigms share few failure modes, and edge mistakes (device counts, devices per site) differ from web ones (journey volumes, session length). Separate entry points also match how users think about their product and keep each step understandable. The connection path stays narrow: it references objects the other two paths created rather than regenerating them. The sandbox has been web-only since 2026-10-29, as if the interface's edge toggle were off.

### Challenges to the proposed AI split

Structure generation may require substantial reasoning: choosing granularity, sharing infrastructure, and avoiding double counting can be harder than filling values. Compact output is desirable, but forcing minimal reasoning could increase correction rounds.

Jev is a candidate for selecting predefined questions/actions and assessing missing categories. Its documented Choice, Score, and Noul primitives do not generate arbitrary explanatory text; authored question templates or occasional LLM generation would still be needed. Type correctness does not establish semantic correctness, and classifier confidence is not confidence in an environmental estimate. Explicit actions often already identify the user's intent, making an additional routing call unnecessary.

The September discussion treated Jev as early access. Vendor speed and efficiency claims were not independently benchmarked. Compare it against deterministic rules and a small LLM before making it a required dependency. See [TypeSafe primitives](https://docs.typesafe.ai/introduction).

## Numerical assumptions and evidence

Distinguish **suggest an assumption** from **research evidence**. A plausible value and a persuasive rationale do not establish an improvement in modeling accuracy.

The library's [modeling-method roadmap](../../../../e-footprint/specs/modeling_logic_roadmap.md) already identifies unresolved workload-to-resource estimation problems, especially database queries. A real benchmark can still be poorly applicable to a different workload or environment. Preserve those limitations in assistance.

Proposed priorities:

- Prefer measured inputs, then applicable documented benchmarks, then explicit hypotheses.
- Keep origin (default, user supplied, measured, AI proposed) separate from evidence quality.
- Put reasoning in comments; sources should refer to evidence actually consulted, not invented citations.
- Prioritize assumptions that could change the conclusion or decision. Sensitivity checks can help, but cannot discover omitted components by themselves.
- Use deterministic sizing once workload, capacity, and service constraints are specified. Selecting those constraints still requires judgment.
- Explore a reusable curated evidence collection before adding repeated live web research.

## Historical token and cost estimates

**These are September 24 planning estimates, not measured results or current price quotations.** Refresh prices, availability, reasoning-token billing, and search fees before experiments. No inference calls or benchmark runs were made to validate these token counts.

The illustrative medium model had 3–5 journeys, 8–12 jobs, several infrastructure components, and roughly 25–40 objects overall.

| Operation across a session | Calls | Total input tokens | Total generated tokens |
| --- | ---: | ---: | ---: |
| Description checks and routing | 4 Jev | 12,000 | No billed output under the quoted pricing |
| Initial structure | 1 LLM | 6,000 | 2,000 |
| Structural correction | 1 LLM | 7,000 | 500 |
| Assumption proposals and short rationales | 1 LLM | 8,000 | 1,000 |
| Final refinement or explanation | 1 LLM | 6,000 | 500 |
| Generative subtotal | 4 LLM | 27,000 | 4,000 |

The input allowance includes repeated instructions, selected definitions, the brief, compact state, and selected evidence. It assumes incremental updates after creation and excludes full serialized arrays or calculation traces.

| Model for generative calls | Quoted input USD / million | Quoted output USD / million | Calculated session USD including Jev |
| --- | ---: | ---: | ---: |
| Gemini 2.5 Flash-Lite | 0.10 | 0.40 | 0.004804 |
| Mistral Small 4 | 0.15 | 0.60 | 0.006954 |
| Gemini 3.1 Flash-Lite | 0.25 | 1.50 | 0.013254 |
| Mistral Large 3 | 0.50 | 1.50 | 0.020004 |

The Jev allowance used USD 0.042 / million input tokens, giving USD 0.000504 for 12,000 tokens. For example:

`(27,000 × 0.15 + 4,000 × 0.60 + 12,000 × 0.042) / 1,000,000 = USD 0.006954`

Sources consulted in September: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing), [Mistral pricing](https://docs.mistral.ai/inference/pricing), and the [Jev announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev). These price comparisons do not imply equivalent modeling quality.

The estimate excludes external search and application hosting, assumes no free allowances or caching discounts, and requires billed reasoning tokens to fit within the output allowance or be added. Doubling the whole allowance as a rough contingency produced approximately USD 0.01–0.04, depending on the model. The assistant suggested initially planning for USD 0.01–0.03 on the normal path while testing toward one cent; this was not a user-approved revised target.

Live research can dominate cost. The September example used Google's quoted Gemini 2.5 grounding fee of USD 0.035 per grounded prompt beyond the allowance: three such prompts alone would exceed USD 0.10. Recheck the applicable product and billing unit before relying on this example.

## Ecodesign priorities

Optimize resource use **per useful completed modeling**, including failures, abandoned attempts, retries, deterministic computations, and correction effort. Proposed controls include explicit checks instead of inference on every keystroke, reuse of examples and evidence, compact state, grouped edits, avoiding unnecessary recalculation, bounded retries, and selective escalation to stronger models.

Measure mean cost and the expensive tail separately; an association-wide spending limit is another possible operational control. No limits or thresholds have been chosen yet.

Price, latency, and token count do not independently establish environmental impact. [EcoLogits](https://ecologits.ai/latest/methodology/) may help where models and providers are supported, with methodological limitations stated. Do not infer Jev's footprint from its price. The existing [reference modeling of the interface](../../e-footprint-modeling/README.md) provides a related place to connect future operational evidence.

## Proposed experiment sandbox

The user asked whether a sandbox could benchmark approaches and model types, enabling iteration and proof of concept without implementing the feature prematurely. The assistant recommended a bounded local experiment effort, evaluating both AI capability and user experience.

### Questions to resolve

| Hypothesis | Proposed comparison |
| --- | --- |
| Small LLMs can produce useful structures | Generate from complete descriptions and inspect actual models |
| Staging structure and assumptions helps | Compare staged generation with a single generation |
| Targeted clarification saves effort | Start with incomplete briefs and assess questions and resulting models |
| Jev earns its integration cost | Compare rules, a small LLM, and Jev on the same decisions |
| Compact edits preserve established work | Edit existing models containing known values and sources |
| Numerical assistance improves evidence quality | Use a fixed reference collection and review proposed assumptions |

Start with structure generation and editing; a good classifier cannot compensate for failure there. Probe numerical refinement early too, since its limitations may narrow the product promise.

### Cases and expected outcomes

Start with **three carefully reviewed cases**, then expand toward **12–20**. Suggested coverage: a conventional web service and substantial background processing; edge/IoT cases belong to the separate edge path (see [Separate web and edge paths](#separate-web-and-edge-paths-to-explore)).

Each case should contain a realistic description, omissions and ambiguities, facts available if asked, genuinely unknown facts, important modeling properties, follow-up edits, and applicable evidence. Expected outcomes should allow multiple valid structures. For example, require that two journeys share one database without double counting, rather than matching exact names or a single graph.

Reserve some cases from prompt development. Use scripted user facts for repeatable multi-round sessions, revealing facts only when requested. Later, observe real users; simulated users cannot establish usability or time savings.

### Minimal capabilities

The proposed sandbox is a local Python runner in the interface repository, using the real library:

- Case files and experiment configurations for workflow, model, prompt, and reasoning settings.
- Validation and application of proposed changes to disposable models.
- Run records containing inputs, outputs, errors, timings, tokens, costs, and relevant versions.
- Side-by-side comparison reports for expert review.
- Exported model files inspectable in the existing interface.
- Replay of recorded responses to improve validators and reports without another paid call.
- Per-run budgets, timeouts, bounded retries, and separate first-attempt versus repaired-success results.

No particular framework, directory layout for the runner, output schema, or provider adapter design has been selected. Avoid building a general experimentation platform before these needs are demonstrated.

### Comparison strategy

Use existing examples/manual modeling as a product baseline. Compare a small LLM workflow with a Jev-assisted workflow while holding the generative model constant. Use a stronger model on selected cases to diagnose whether failures arise from capability, instructions, or representation. Change one major variable at a time rather than exhaustively combining every model and prompt.

Evaluate individual operations first, then complete 3–6-round journeys. Repeat trials to expose variability. Walk a few users through example questions and proposals, potentially with a person operating the sandbox, before building the final interaction.

### Evaluation dimensions

| Dimension | Evidence |
| --- | --- |
| Technical validity | Models load, calculate, and accept edits |
| Modeling quality | Correct relationships, useful scope, omissions and double counting |
| Assumption quality | Applicable evidence, unsupported claims, visible uncertainty |
| Editing reliability | Requested changes achieved and established work preserved |
| User effort | Time, questions, expert corrections, completion in 3–6 rounds |
| Efficiency | Whole-session cost, latency, retries, supported resource estimates |

Use deterministic checks where possible and expert review for semantics initially. Model-based graders may help later after calibration against human review. Do not let low cost compensate for consequential modeling errors in a single aggregate score. Include failed attempts in the cost assessment. The small initial suite is a discovery tool, not proof of production reliability.

Reference discussed: [Anthropic on AI evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), covering repeated trials, outcome assessment, and complementary code, model, and human graders.

Illustrative experiment arithmetic: 12 cases × 2 workflows × 3 repetitions = 72 complete sessions. At an assumed USD 0.01–0.05 each, inference would cost USD 0.72–3.60, excluding stronger reference runs and research tools. This is not a spending authorization or a validated estimate. Case curation and expert review are likely to dominate effort.

## Open decisions and next discussion

- What qualifies as a useful completed modeling, and which errors are unacceptable?
- Which three initial cases best represent the target audience and intended first scope?
- Does initial scope include research, result explanation, and scenario comparison? (Edge/IoT is to be explored as a separate path.)
- How much user knowledge can the clarification process reasonably require?
- Does generation adapt examples, construct new structures, or combine both?
- Does Jev improve outcomes enough to justify another dependency?
- Should assistance modes and maturity indicators replace a global draft toggle?
- Which evidence sources are suitable for numerical refinement, and where must the tool abstain or preserve a hypothesis?
- What are the experiment budget, latency goals, retry limits, and decision thresholds?

The proposed next step is a short experiment brief and three reviewed cases, followed by a minimal runner if authorized. Results should determine the initial product scope and then inform the formal spec, plan, and UX. The [spec-driven workflow](../../workflow.md) permits investigations before shipping feature work; this handoff does not advance those gates.

## Relevant project references

- [Interface architecture](../../architecture/index.html), [mission](../../mission.md), [constitution](../../constitution.md), and [design hub](../../design/index.html).
- [Forms and relationships](../../architecture/forms-and-relationships.html) for current source metadata and simplified inputs; [onboarding](../../architecture/onboarding.html) for current starting examples.
- [Library architecture](../../../../e-footprint/specs/architecture/index.html) and [modeling-method roadmap](../../../../e-footprint/specs/modeling_logic_roadmap.md).
- [Interface reference modeling](../../e-footprint-modeling/README.md) and [user needs backlog](../../../user_research/needs-backlog.md), including operational data import and telemetry needs.
- [Canonical workflow](../../../../e-footprint/specs/workflow.md) and [local spec-specify skill](../../../../e-footprint/.agents/skills/spec-specify/SKILL.md).

These references supply current implementation context; this document preserves the conversation's ideas without asserting that they have since shipped elsewhere.
