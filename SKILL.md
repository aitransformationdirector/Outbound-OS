---
name: ssp-publisher-outreach-showcase
description: Create a new, self-contained Codex SSP publisher-research and outbound project from a CSV, a named ad manager or SSP, and optional traffic, vertical, and geography criteria. Use when demonstrating or running the two-review publisher outreach workflow through approved Gmail drafts and local manual follow-up actions. This showcase edition excludes downstream CRM, Publisher Pipeline exports, scheduled follow-up syncs, and production integrations.
---

# SSP Publisher Outreach Showcase

Create a provider-neutral Codex project from the bundled template. Configure it from the initial request, validate it, and stop before research begins.

## Explain the two-phase setup

At the beginning of the first response, tell the user that setup has two phases:

1. **Build and seed:** this skill collects the short intake, creates a unique self-contained folder under `~/Desktop/Codex/SSP Projects/`, and validates it.
2. **Open and run:** after the build, the user adds the exact generated `<unique-project-name>` folder as a local Codex project, starts a new task inside it, and types `run`.

Make clear that the user should not create an empty campaign project beforehand and must not select the shared `SSP Projects` parent folder. Keep this explanation brief, then continue with the guided intake.

## Collect the launch values

First inspect the current message and attachments. Extract:

- required CSV path;
- required SSP/ad-manager name;
- minimum monthly traffic, default `50000`;
- target verticals, default `travel,travel_adjacent`;
- optional geographies and one-line note;
- optional project label.

If this is the first invocation and any launch value is absent, do not build yet. Read `references/guided-intake.md`, show its compact guided form with known values prefilled, and wait for the user's reply. Ask for every remaining launch choice in that one message so the user does not need to remember the input format.

- Detect an attached CSV automatically; do not ask the user to type its filesystem path when an attachment is available.
- Show the threshold, vertical, and geography defaults explicitly.
- Let the user reply `use defaults` for all optional choices.
- On later replies, ask only for required information that is still missing or for a supplied invalid threshold.
- Never infer the CSV or ad-manager name.

After the guided intake is complete, use the confirmed values. Read `references/input-contract.md` when resolving aliases, paths, or collision behavior.

## Build

Run `scripts/build_project.py` with the resolved values. The default destination is:

`~/Desktop/Codex/SSP Projects/<provider-date>/`

Request the normal scoped filesystem approval if the destination is outside the active writable project. Do not broaden the destination or overwrite an existing project.

Example:

```bash
python3 "<skill-dir>/scripts/build_project.py" \
  --source "<csv-path>" \
  --provider "ExampleManager" \
  --minimum-monthly-traffic "50k" \
  --verticals "travel,travel_adjacent"
```

Pass `--geographies`, `--note`, or `--project-label` only when supplied. The script must:

1. copy the provider-neutral asset template transactionally;
2. update project defaults and user-facing launch files;
3. preserve and audit the CSV with the campaign engine;
4. write `PROJECT_INPUT.json` and `BUILD_RECEIPT.json`;
5. validate the project and campaign;
6. return JSON containing `project_path`, `campaign_id`, `resumed`, and `next_prompt`.

Treat a nonzero exit as a build failure. Report the exact error and leave no half-created project.

## Preserve the full-review UX contract

The bundled project template must carry these requirements into every generated project's `AGENTS.md` and `$run-ssp-outreach` skill:

- Every full-review card shows one concise, evidence-grounded line explaining what the site or verified publisher group is about.
- Every card shows the source estimate for the canonical site's monthly traffic. Label it as estimated monthly pageviews, not unique visitors.
- When current public evidence verifies common ownership of multiple in-scope sites, also show the combined group estimate by summing the source monthly-pageview estimates for the consolidated portfolio members. Keep the site estimate and group total separate, list the included domains in the detail view, and never infer missing traffic or ownership.
- Put one-click `Approve shown action` and `Exclude` controls directly on every card. Opening the detailed review remains optional and is used for evidence, exact copy, notes, `Needs changes`, and other decisions.
- Show the same description and traffic facts in the detail view, preserve stable account IDs and prior decisions across rebuilt rounds, and validate the enhanced review before serving it.
- Use plain user-facing language for manual routes, such as `Add to manual follow-up list`; avoid internal phrases such as `manual-action queue`.

When the VisualizeMe default card template does not expose these fields or quick decisions, the generated project must prepare and serve a campaign-local VisualizeMe template that does. Keep it bound to `127.0.0.1` and preserve the normal VisualizeMe feedback schema.

## Preserve execution-quality contracts

Every generated project must carry these requirements into `AGENTS.md`, the
`$run-ssp-outreach` skill, its schemas, and deterministic validation:

- **One canonical copy record:** Store one versioned copy record per account and
  review stage. Its publisher brand, subject, plain-text body, and paragraph
  breaks must feed the review, Gmail draft intent, and manual route output
  without channel-specific rewriting. Validate derived outputs against it.
- **Natural publisher brand:** Keep `canonical_domain`, publisher/account
  identity, and reader-facing `publisher_brand` separate. Resolve and validate
  the natural brand before the smoke review; never expose a URL suffix as the
  brand unless it is genuinely part of the public brand.
- **Production-ready manual queue:** For every approved non-email route, provide
  the direct route, subject when applicable, preformatted paragraph-preserving
  copy, a working one-click `Copy` control, `Done` and `Hold` controls, created
  and updated timestamps, and a required reason when held. Keep all actions
  local until Dean performs and confirms them.
- **Continuous progress reporting:** During automatic work, report the current
  stage, completed and remaining counts, and the next automatic step at each
  material checkpoint and at least once per 60 seconds during long-running
  work. Continue automatically between the two planned gates; do not require
  `continue` messages.
- **Mailbox drift checks:** Re-list the exact campaign draft set immediately
  before any authorized Gmail draft creation or edit. Reconcile recipients,
  subjects, draft IDs, and a checked timestamp; suppress duplicates and block
  only affected items on unexpected drift. This does not authorize sending.
- **Persistent suppression memory:** Use the shared project-family suppression
  registry for Dean-confirmed prior relationships, opt-outs, colleague-owned
  accounts, and unsuccessful prior outreach. Load it before smoke selection and
  merge it with campaign-local Gmail suppression without weakening evidence or
  campaign-isolation rules. Only confirmed facts may update the shared registry.

## Preserve the showcase boundary

Every generated project must stop after the approved Gmail-draft and local
manual-follow-up actions are reconciled and validated.

- Do not install or invoke a scheduled follow-up task.
- Do not create CRM state, opportunity exports, Pipeline bundles, shared
  handoffs, or production-import instructions.
- Do not include downstream systems in the completion criteria.
- Finish with final action counts, validation status, and campaign-local paths.

## Handoff

Do not start publisher research, browse sites, read Gmail, build a VisualizeMe review, or create drafts in this builder task.

After a successful build, label the handoff **Phase 2 — open and run** and give the user:

- the clickable project folder;
- the effective provider, threshold, verticals, and geographies;
- the parsed and eligible source counts;
- the exact generated folder path returned as `project_path`;
- these specific Codex instructions:
  1. open **Projects** and choose **Add local project**;
  2. select the exact generated `<unique-project-name>` folder shown in `project_path`;
  3. do not select its shared `SSP Projects` parent;
  4. start a new task inside that local project;
  5. type exactly `run`.

The generated project interprets the exact message `run` as authority to execute the prepared graph. Its only planned human gates are the three-publisher smoke review and the complete post-Gmail-preflight VisualizeMe review.
