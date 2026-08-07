# Codex SSP Outreach — operating rules

This folder is a reusable Codex project for turning a publisher CSV into researched, reviewable SSP outreach for TIKI.

## User experience

- Required run input: one CSV and the SSP/ad-manager name.
- Optional run input: one short instruction such as geography, traffic, or vertical emphasis.
- A project created by `$ssp-publisher-outreach-showcase` contains `PROJECT_INPUT.json`. When the user types exactly `run`, read that file, use its `campaign_id` and effective configuration, invoke `$run-ssp-outreach`, and begin without asking for intake again.
- Use system defaults for everything else.
- Do not interrupt the run for ordinary ambiguity. Record unknowns, choose the safer branch, or place the item in the next review.
- There are exactly two planned human gates:
  1. a three-publisher smoke-test review;
  2. a complete queue and exact-action review after Gmail-history suppression.
- After submitted smoke feedback is incorporated, continue automatically to the full queue.

## Authority and external actions

- Research uses public web sources only.
- Gmail may be read only for history suppression and draft preflight.
- The full review combines queue approval and execution preflight. Every card must show the exact recipient or manual route, final subject/body, evidence, and proposed action.
- On the full review, `Approve shown action` explicitly authorizes creation of the displayed Gmail draft for an email route or addition of the displayed manual route to the local manual follow-up list.
- Nothing in this system authorizes sending email, scheduling email, submitting a form, posting a message, or calling a publisher.
- A Gmail draft is not sent outreach. Only Gmail Sent proves an email first touch.
- Platform-level connector or permission confirmations may still appear and must not be bypassed.

## Campaign isolation

- Keep each run under `01_CAMPAIGNS/<campaign_id>/`.
- Every structured record must carry `campaign_id`.
- Never mix leads, approvals, exclusions, messages, or action state between campaigns.
- Reusable public provider profiles may be cached under `system/provider-cache/`, but copy the exact evidence used into the current campaign.

## Research invariants

- Consolidate common ownership and portfolios before contact research.
- Stop when one current, public, correctly scoped commercial route is actionable.
- Never guess contacts, email patterns, relationships, performance, or partner status.
- Preserve exact evidence URLs and checked dates.
- Treat ads.txt and similar signals as relevance evidence, not proof of the exact product, placement, wrapper, or current implementation.
- Keep `DIRECT`, `RESELLER`, seller IDs, SSP, DSP, Prebid, header bidding, yield, inventory, integration, and CPM out of first-touch copy.
- Ask whether the named manager is involved unless stronger independent evidence supports a factual statement.

## Graph execution

- Use `$run-ssp-outreach` for a new or resumed campaign.
- Use read-only subagents for independent research; the primary agent is the only canonical writer.
- Subagents return validated structured results. Never let several agents edit the same campaign artifact.
- Every expected account must end as completed, excluded, held, or explicitly failed. Never silently drop a failed result.
- Run deterministic validation before either review and before creating any Gmail draft.
- After approved Gmail draft and manual-route actions reach recorded terminal
  results and final validation passes, end with counts, validation status, and
  campaign-local paths. Do not create downstream records or scheduled tasks.
- Preserve the last valid state if a stage fails.

## Execution quality and continuity

- Treat the versioned record in `state/outreach.jsonl` as the canonical copy
  source. The reader-facing brand, subject, body, and exact paragraph breaks
  shown in reviews must feed Gmail draft intents and manual-route outputs
  without rewriting. Validate every derived action against that record.
- Keep the domain, account identity, and `publisher_brand` separate. Resolve the
  natural public brand before smoke review and use it consistently in the
  subject and body.
- Make the approved manual follow-up queue ready to use: direct route,
  paragraph-preserving copy, working `Copy`, `Done`, and `Hold` controls,
  created/updated timestamps, and a required hold reason. These controls record
  local state only; they never submit the route.
- During automatic work, report stage, completed/remaining counts, and the next
  automatic step at each material checkpoint and at least once per 60 seconds.
  Continue automatically except at the two planned gates or a genuine blocker.
- Immediately before any authorized Gmail draft creation or edit, re-list the
  exact campaign drafts and reconcile recipient, subject, draft ID, and checked
  time. Suppress duplicates and block only drifted items. Never infer send
  authority.
- Before smoke selection, load `../_shared/suppression-memory.jsonl`. Merge
  Dean-confirmed prior relationships, opt-outs, colleague ownership, and
  unsuccessful prior outreach with campaign-local Gmail suppression. Only the
  primary agent may upsert confirmed facts into this shared registry; preserve
  the originating campaign ID, provenance, timestamps, and provider scope.

## Showcase boundary

- This project ends after research, the two reviews, approved Gmail drafts,
  local manual follow-up actions, reconciliation, and validation.
- Do not create CRM state, opportunity exports, Pipeline bundles, shared
  handoffs, scheduled follow-up tasks, or production integrations.

## Review requirements

- Use VisualizeMe on localhost only.
- Smoke review contains exactly three deliberately varied publishers.
- Full review contains every canonical account, including excluded, held, failed, and non-actionable accounts.
- Every full-review card shows one concise, evidence-grounded line explaining what the site or verified publisher group is about.
- Every card shows the canonical site's source traffic estimate, explicitly labelled as estimated monthly pageviews rather than unique visitors.
- For a verified multi-site ownership group, also show a separate combined group estimate equal to the sum of the source monthly-pageview estimates for the consolidated portfolio members. List the included domains in the detail view. Never infer missing traffic or group ownership.
- Put one-click `Approve shown action` and `Exclude` controls directly on every card. The deeper review remains optional for evidence, exact copy, notes, `Needs changes`, and other decisions.
- Repeat the description, site estimate, and any verified group total in the detail view.
- Use plain user-facing wording such as `Add to manual follow-up list`; do not expose internal language such as `manual-action queue`.
- If the default VisualizeMe card template cannot surface these fields and controls, prepare and serve a campaign-local template that can while preserving the VisualizeMe feedback schema.
- Preserve stable account IDs between rounds.
- `Exclude` is a one-click card decision.
- Apply `Needs changes` feedback and rebuild the same review without losing prior decisions.
