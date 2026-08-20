# Outbound OS

Outbound OS is a local-first Codex workflow for turning a target-account list into an evidence-backed, reviewable outbound campaign. It is industry-neutral: the same onboarding and account model can support hospitality, tourism, software, media, marketplaces, agencies, and other teams without fixed vertical or size assumptions.

`Codex skill` · `Python 3.10+` · `CSV/XLSX/TSV/text inputs` · `Gmail, Outlook, or manual export` · `No automatic sending`

## What it does

The `$outbound-os` skill:

1. collects a target-account list and campaign context;
2. audits columns, duplicates, missing identifiers, and unusable rows;
3. separates targeting into `must_match`, `exclude`, and `prioritize` rules;
4. recommends optional context-specific filters without activating them automatically;
5. requires confirmation of the final targeting brief;
6. creates and validates a self-contained campaign folder under `~/Desktop/Codex/Outbound OS Projects/`; and
7. guides the user to open that exact folder as a new local Codex project before execution.

The generated project carries neutral account, evidence, message, approval, reply-monitoring, CRM-export, and channel-adapter contracts. It never authorizes sending, scheduling, form submission, posting, calling, or live CRM mutation.

## Install

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/aitransformationdirector/Outbound-OS.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/outbound-os"
```

Start a fresh Codex task and invoke:

```text
$outbound-os
```

## Intake

Outbound OS accepts:

- CSV, TSV, or XLSX files;
- pasted account names or websites; and
- connected Google Sheets, with a file-export fallback when the connection is unavailable.

Each row needs an account name or website. The guided intake asks how the list was selected, account types, markets, relevant size measures, must-haves and exclusions, numerical thresholds, the user and sender identity, offer, campaign goal, channel, and campaign name. Every question includes examples.

The user confirms a final targeting brief before anything is built. Unknown evidence for a hard rule becomes `needs_review`; it never silently excludes an account.

## Open and run the generated project

Building and running are deliberately separate phases.

1. Do **not** type `run` in the original builder task and do not attach the generated folder there.
2. In Codex, open **Projects** and choose **Add local project**.
3. Select the exact generated campaign folder—not the shared `Outbound OS Projects` parent.
4. Confirm it contains `AGENTS.md`, `PROJECT_INPUT.json`, and `.agents/skills/run-outbound-campaign/SKILL.md`.
5. Start a new task inside that local project.
6. Type exactly `run`.

The generated project checks its exact root and bundled hidden runtime before work. It will not substitute a global skill or external template when opened incorrectly.

## Reusable profiles

After confirmation, Outbound OS may save non-secret user, organization, sender, offer, and channel defaults in the local `_shared/team-profiles.json` file. Profiles remain on that computer and are not bundled with this repository or shared with other users. Credentials, tokens, cookies, passwords, and API keys are prohibited.

## Channel boundary

Campaign logic produces a channel-neutral proposed action. Adapters translate an explicitly approved action into:

- a Gmail draft;
- an Outlook draft; or
- a local manual-export item.

Mailbox connections and live connector behavior depend on the host Codex environment. The repository's offline tests validate the action contracts and no-send boundary; they do not exercise live accounts.

## Verification

Run the offline suite:

```sh
python3 -m unittest discover -s tests -v
```

The suite covers CSV, TSV, XLSX, and pasted-text imports; source aliases; duplicate and ambiguity handling; adaptive recommendations; hard-rule unknown handling; secret rejection; preferred-name persistence; reusable profiles; project-root handoff metadata; bundled runtime presence; all three action routes; reply normalization; and conversation-only CRM exports.

## Project map

```text
Outbound-OS/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── guided-intake.md
│   └── campaign-contract.md
├── scripts/build_project.py
├── tests/test_build_project.py
└── assets/project-template/
    ├── .agents/skills/run-outbound-campaign/
    ├── .agents/skills/monitor-outbound-replies/
    ├── .agents/skills/sync-outbound-crm/
    ├── system/adapters/
    ├── system/schemas/
    └── system/scripts/validate_system.py
```

## Limitations

- Live research quality, mailbox access, and draft creation depend on the connected Codex capabilities.
- Ambiguous account identities and unverifiable hard criteria require human review.
- The builder records the original local source path inside the generated project.
- No license file is currently included; public visibility does not grant reuse rights.
