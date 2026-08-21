# Outbound OS

Outbound OS 3 is a local-first, multi-runtime workflow for turning a target-account list into an evidence-backed, reviewable outbound campaign. One shared campaign engine supports both Codex and Claude Code; host-specific skills handle discovery, invocation, folder handoff, and available connections.

`Codex + Claude Code` · `Python 3.10+` · `CSV/XLSX/TSV/text inputs` · `Gmail, Outlook, or manual export` · `No automatic sending`

## What it does

Outbound OS:

1. collects a target-account list and campaign context;
2. audits columns, duplicates, missing identifiers, and unusable rows;
3. separates targeting into `must_match`, `exclude`, and `prioritize` rules;
4. recommends optional, context-specific filters without activating them automatically;
5. requires confirmation of the final targeting brief;
6. creates and validates a self-contained campaign folder under `~/Desktop/Outbound OS Projects/`; and
7. guides the user to open that exact folder in Codex or Claude Code before execution.

The generated project carries neutral account, evidence, message, approval, reply-monitoring, CRM-export, and channel contracts. It never authorizes sending, scheduling, form submission, posting, calling, or live CRM mutation.

## Install for Codex

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/aitransformationdirector/Outbound-OS.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/outbound-os"
```

Start a fresh Codex task and invoke:

```text
$outbound-os
```

## Install for Claude Code

Clone the same repository into Claude's personal skills directory:

```sh
mkdir -p "$HOME/.claude/skills"
git clone https://github.com/aitransformationdirector/Outbound-OS.git \
  "$HOME/.claude/skills/outbound-os"
```

Start a new Claude Code session. The repository is discovered as an `outbound-os` plugin; invoke:

```text
/outbound-os:new-campaign
```

For local development, launch Claude Code with `claude --plugin-dir /path/to/Outbound-OS` and use the same invocation. Run `/reload-plugins` after changing plugin components.

## Shared behavior, thin host adapters

The business workflow is defined once in `references/`, `scripts/`, schemas, and `system/runtime`. Codex and Claude entry points only describe how their host locates those files and opens the generated project.

Every generated campaign includes:

- `AGENTS.md` and `.agents/skills/` for Codex;
- `CLAUDE.md` and `.claude/skills/` for Claude Code; and
- one canonical `PROJECT_INPUT.json`, campaign state, schema set, and `system/runtime/` implementation shared by both.

A campaign can therefore move between Codex and Claude Code without rebuilding or translating its data.

## Intake and profiles

Outbound OS accepts CSV, TSV, XLSX, pasted account names or websites, and connected Google Sheets when the active host provides that capability. Otherwise it requests a file export without restarting onboarding.

Every unanswered intake question retains a concrete example. The user confirms a final targeting brief before anything is built. Unknown evidence for a hard rule becomes `needs_review`; it never silently excludes an account.

Confirmed non-secret user, organization, sender, offer, and channel defaults may be saved in the local `_shared/team-profiles.json` file. Profiles remain on that computer. Credentials, tokens, cookies, passwords, and API keys are prohibited.

## Open and run the generated project

Building and running are deliberately separate phases. Do not run the generated campaign from the builder conversation and do not open the shared `Outbound OS Projects` parent folder.

### Codex

1. Open **Projects** and choose **Add local project**.
2. Select the exact generated campaign folder.
3. Confirm it contains `AGENTS.md`, `PROJECT_INPUT.json`, and `.agents/skills/run-outbound-campaign/SKILL.md`.
4. Start a new task in that project and type `run`.

### Claude Code

1. Start a new Claude Code session rooted at the exact generated campaign folder. In a terminal, change into the folder and run `claude`; in Claude Code Desktop, choose that folder as the project.
2. Confirm it contains `CLAUDE.md`, `PROJECT_INPUT.json`, and `.claude/skills/run-outbound-campaign/SKILL.md`.
3. Start a new conversation and invoke `/run-outbound-campaign`.

## Channel capability boundary

Campaign logic produces a channel-neutral proposed action. A host may translate an explicitly approved action into a Gmail draft, Outlook draft, or local manual-export item only when the relevant capability is available. Missing mailbox capabilities hold only the affected action; manual export remains available. Adapters may not change canonical copy, and no adapter may send automatically.

## Verification

Run the offline suite:

```sh
python3 -m unittest discover -s tests -v
```

When Claude Code is installed, also validate its plugin package:

```sh
claude plugin validate . --strict
```

The suite covers imports, source aliases, duplicate and ambiguity handling, adaptive recommendations, hard-rule unknown handling, secret rejection, preferred-name persistence, reusable profiles, both generated runtimes, shared campaign execution, channel-neutral actions, reply normalization, CRM exports, and the no-send boundary.

## Project map

```text
Outbound-OS/
├── SKILL.md                         # Codex entry point
├── agents/openai.yaml               # Codex UI metadata
├── .claude-plugin/plugin.json       # Claude plugin manifest
├── skills/new-campaign/SKILL.md     # Claude entry point
├── references/                      # Shared onboarding and contracts
├── scripts/build_project.py         # Shared builder
├── tests/
└── assets/project-template/
    ├── AGENTS.md                    # Generated Codex instructions
    ├── CLAUDE.md                    # Generated Claude instructions
    ├── .agents/skills/              # Thin Codex runtime skills
    ├── .claude/skills/              # Thin Claude runtime skills
    ├── system/runtime/              # Shared executable campaign logic
    ├── system/adapters/
    └── system/schemas/
```

## Limitations

- Live research quality and mailbox access depend on the active host and its connected tools.
- Ambiguous account identities and unverifiable hard criteria require human review.
- The builder records the original local source path inside the generated project.
- Existing Outbound OS 2 campaign folders are not modified; version 3 creates new dual-runtime projects.
- No license file is currently included; public visibility does not grant reuse rights.
