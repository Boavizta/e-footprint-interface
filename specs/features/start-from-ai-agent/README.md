# Start from a conversation with an AI agent — draft feature kickoff

Status: seed for a `spec-specify` session · 2026-11-23.
No spec, implementation plan or UI design has been approved for this feature.

## User outcome

A user who works with an AI agent of their own (Claude Code, GitHub Copilot, Codex, a web chat that can run Python)
starts a modeling there and views the result in the interface. The interface gives them a short prompt to paste into
their agent; the agent builds the model with the library and writes one file; the user opens that file in the
interface.

It is a path of its own, next to **Start with AI** and distinct from it:

| | Start with AI | Start from a conversation with an AI agent |
|---|---|---|
| Who runs the AI | The interface, on Boavizta's account | The user, in their own agent |
| Who it suits | Anyone with a description of their system | People who already work with an agent, or whose case exceeds what Start with AI builds |
| What it costs Boavizta | An inference per generation | Nothing |
| Where the model is written | In the interface | As Python in the user's own space, then loaded as a file |

## Where the idea comes from

- The library's `ai_skills/` folder held a kit for trying e-footprint with a web chat: two prompts, a spreadsheet
  template and a beginner page, all specific to GenAI video workflows. The kit is being removed from the library
  (`agent-guidance` feature there); git history keeps it. What carries over here is the idea, not the files: the kit
  could be rewritten without its GenAI video specifics.
- The library is getting a guide that ships in the package and that an agent fetches with one command
  (`e-footprint/specs/features/agent-guidance/README.md`). With it, the prompts of the kit collapse into an install
  line, the guide command and the user's description.
- The [local folder link seed](../local-folder-link/README.md) records the same pattern in a large company: Microsoft
  Copilot produces the modeling JSON and the user loads it in the interface.
- The [AI assistance roadmap](../ai-assistance/roadmap.md) records what Start with AI does not reach yet, such as
  groups nested in groups. A user's own agent with a stronger model is a way through those cases today.

## What it relies on

Both are library features, specified in `e-footprint/specs/features/`:

- **`agent-guidance`**: the guide and its command. Without it, this feature would have to carry modeling
  instructions itself.
- **`comparison-file`**: the library exports several systems to one file, in the format the interface already saves
  a comparison in. With it, an agent can hand over a reference and a variant that open here in comparison mode.

## Starting points for the spec

These are hypotheses, not decisions.

- **The interface carries no modeling instructions.** Its prompt says to install the library, run the guide command
  and export a file for the interface. Everything about how to model lives in the library guide, or the copy here
  drifts from the installed library.
- **The prompt can pin the library version.** The interface knows which `efootprint` it runs, so it can show
  `pip install efootprint==<that version>`. A file saved by another version still opens: it is upgraded and
  recomputed on load.
- **The prompt asks for what the interface edits well.** Usage volumes given as a start date, a duration, an initial
  volume and a growth rate stay editable here; a custom hourly series can only be viewed. The library guide
  recommends the former on its own grounds, so this may need no line of its own.
- **The entry sits where a modeling starts**, beside Start with AI, the examples and Start from scratch, and says in
  a sentence who it is for.
- **Opening the result is the existing "Open a file"**, which already detects a single model or a comparison.

## Open questions

- Which agents to name and test: coding agents with a shell, and which web chats can install the library in their
  sandbox.
- Whether the entry is a panel with a prompt to copy, a page of the documentation it links to, or both.
- Whether a rewritten kit (a generic input spreadsheet, a beginner page) has a place here, in the published
  documentation, or nowhere.
- Whether the prompt differs for a single modeling and for a comparison, or leaves that to the conversation.
- How this path is told apart from Start with AI on screen, so that the two do not compete for the same person.
- Whether to wait for the local folder link, which would remove the manual open of the file.
