---
name: outbound-os
description: Create the canonical universal Outbound OS campaign from an account list or spreadsheet, a targeting brief, and confirmed inclusion, exclusion, and prioritization rules. Use for first-run onboarding or a new campaign; do not use to execute an already-created campaign.
---

# Outbound OS

Create a neutral, self-contained Outbound OS project. Do not assume an industry, account type, size metric, geography, seller, or email provider.

## Start list-first

Inspect the message and attachments. If the user has not supplied the full intake, read [references/guided-intake.md](references/guided-intake.md), start with its welcome and support line exactly as written, prefill known information, and ask for the remainder in one compact message. Keep the example attached to every unanswered intake question; do not shorten the form into category labels without examples.

Accept:

- CSV, TSV, or XLSX attachments;
- a pasted list with at least an account name or website per row;
- a connected Google Sheet. Use the Google Sheets connection to obtain the selected range and preserve a local source snapshot. If the connection is unavailable, request an XLSX or CSV export without restarting the intake.

Never guess an ambiguous account identity or website. Missing websites may be researched later; ambiguous matches remain `needs_review`.

Once the user supplies or confirms `team_profile.user_name`, address them by that name at least once in every subsequent user-facing response. Keep the name in the confirmed brief and reusable profile; do not infer it from an email address.

## Audit before building

Run `scripts/build_project.py audit --source <path> --context <campaign-context>` after resolving the source into a local file. Report totals, duplicates, unusable rows, missing names or websites, and available columns.

Translate the targeting description into explicit rules using [references/campaign-contract.md](references/campaign-contract.md):

- `must_match` for mandatory eligibility;
- `exclude` for disqualifiers;
- `prioritize` for ranking signals.

Ask only when the difference materially affects eligibility. Unknown evidence for a hard rule defaults to `needs_review`, never exclusion.

## Recommend filters, then confirm

Recommend only filters relevant to the goal, account definition, source columns, and likely public evidence. Show each recommendation's rationale, evidence requirement, and expected coverage. Suggestions remain inactive until accepted.

Present the final brief with source, goal, offer, account totals, all three rule groups, accepted suggestions, channels, and unresolved items. End with:

> Do you want Outbound OS to apply any other filtering before I create the campaign? You can accept, remove, or edit any of the rules above.

Do not build until the user confirms the brief.

## Build the project

Create a temporary JSON brief conforming to `references/campaign-contract.md`, then run:

```bash
python3 "<skill-dir>/scripts/build_project.py" build \
  --source "<resolved-source-path>" \
  --brief "<confirmed-brief.json>"
```

The default destination is `~/Desktop/Codex/Outbound OS Projects/<campaign-name-date>/`. Request scoped filesystem approval when needed. The builder is transactional, preserves the original input, saves reusable non-secret team defaults, creates neutral account records, and validates the generated project.

## Handoff

Do not begin account research or create mailbox drafts in the builder task. After a successful build, address the user by name and label the response `Phase 2 — open the generated project`.

Show the clickable exact generated folder, its full path, counts, confirmed rules, and selected channels. Then give these instructions without shortening them:

1. **Do not type `run` in this current builder task.** Do not attach or mention the generated folder here; attaching a folder is not the same as opening a local project.
2. In Codex, open **Projects** and choose **Add local project**.
3. In the folder picker, navigate to `Desktop` → `Codex` → `Outbound OS Projects`.
4. Select the exact generated campaign folder named in `project_folder_name`. Do not select the shared `Outbound OS Projects` parent folder.
5. Confirm the selected folder contains `AGENTS.md`, `PROJECT_INPUT.json`, and `.agents/skills/run-outbound-campaign/SKILL.md`.
6. Start a **new task inside that local project**. Verify the task's project/folder is the exact generated campaign folder before continuing.
7. Type exactly `run` in that new task.

If the user types `run` in the builder task, do not execute or fall back to the template. Address them by name and repeat the Phase 2 instructions with the exact generated path.

Nothing in onboarding authorizes sending messages.
