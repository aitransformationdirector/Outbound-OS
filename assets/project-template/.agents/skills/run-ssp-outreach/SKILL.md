---
name: run-ssp-outreach
description: Run or resume a TIKI SSP publisher outreach campaign from a CSV and a named SSP/ad manager. Use when the user drops or attaches a publisher CSV and asks Codex to research, qualify, consolidate, prepare outreach, create a three-publisher calibration review, build the complete VisualizeMe queue, or create specifically approved Gmail drafts. Enforce the two-gate graph, public-web research, campaign isolation, evidence contracts, Gmail-history suppression, and no-send boundary.
---

# Run SSP Outreach

Run the campaign as a resumable graph. Require only the CSV, target provider name, and any optional one-sentence instruction. Use defaults for missing campaign choices and do not open additional intake stops.

## Load the contracts

Read these files before starting or resuming:

- `references/graph-contract.md`
- `references/research-and-copy-rules.md`
- `references/review-and-execution-policy.md`
- `system/defaults.json`
- `system/graph/campaign-graph.json`

Read the relevant JSON Schema under `system/schemas/` before requesting a structured node result.

## Start or resume

1. If `PROJECT_INPUT.json` exists and has `status: ready`, treat it as the authoritative prepared launch. When the user's message is exactly `run`, use its `campaign_id`, provider, source, thresholds, verticals, geographies, and note without asking for intake.
2. Otherwise find the user-supplied CSV. Prefer an attached path; otherwise require exactly one `.csv` in `00_INBOX`.
3. Extract the named SSP/ad manager and optional instruction from the current request.
4. If no campaign exists for this exact source hash and provider, run:

   ```bash
   python3 .agents/skills/run-ssp-outreach/scripts/campaign_engine.py bootstrap \
     --source "<csv-path>" \
     --provider "<provider-name>" \
     --note "<optional instruction>"
   ```

5. If the source hash and provider already match a campaign, resume that campaign instead of duplicating it.
6. Run `status` and continue from the first incomplete node.

## Report progress without prompting

At each material checkpoint, and at least once per 60 seconds while automatic
work is still running, give Dean one compact update containing:

- current stage;
- completed and remaining account counts;
- the next automatic step.

Continue automatically between checkpoints. Pause only at the smoke review,
full review, a connector/permission confirmation, or a genuine blocker. Do not
require Dean to ask whether the run is still active or to type `continue`.

## Execute the pre-smoke graph

1. Have `provider_profiler` create `state/provider_profile.json`.
   - Research the exact named provider from current public evidence; never reuse assumptions from another provider.
   - Determine whether a publisher-to-account-manager introduction route is supported.
   - Where evidence supports the route, frame TIKI as bringing curated travel demand into the publisher's existing auction or wrapper, ask an interested publisher for a low-friction introduction, and state that TIKI owns the provider follow-through while keeping the publisher informed.
   - Never promise higher CPMs or revenue and never imply an integration or provider relationship already exists.
2. Apply the deterministic traffic and geography filters from the defaults snapshot.
3. Classify eligible candidates against the configured target vertical labels. Browse only uncertain or promising sites and audit the configured negative sample.
4. Seed ownership groups deterministically, then use `ownership_resolver` only for likely portfolios or ambiguities.
5. Fan in once to create `state/accounts.jsonl`. Account for every candidate as active, excluded, held, or failed. Keep the domain, canonical account identity, and natural reader-facing `publisher_brand` separate.
6. Resolve and validate every `publisher_brand` before smoke selection. Preserve intentional public casing and remove URL components or suffixes that are not genuinely part of the public brand.
7. Load `../_shared/suppression-memory.jsonl`, then merge confirmed shared facts with campaign-local suppressions. Only the primary agent may upsert Dean-confirmed facts into shared memory.
8. Select exactly three deliberately varied active accounts.
9. Run one `publisher_researcher` per selected account, with at most six concurrent agents.
10. Send only material ambiguity to `evidence_verifier`.
11. Generate standard copy deterministically. Use model judgment only for genuine exceptions.
12. Write exactly three versioned canonical copy rows to `state/outreach.jsonl`, validate their natural brands and paragraph formatting, and build the review:

   ```bash
   python3 .agents/skills/run-ssp-outreach/scripts/campaign_engine.py build-review \
     --campaign "<campaign-id>" --stage smoke
   ```

## Gate 1: three-publisher review

Use `$visualize-me` with the generated smoke `review.json`. Give the user the localhost URL and wait for submitted feedback.

Apply it:

```bash
python3 .agents/skills/run-ssp-outreach/scripts/campaign_engine.py apply-feedback \
  --campaign "<campaign-id>" --stage smoke --feedback "<feedback.json>"
```

- If feedback contains `needs_changes` or `pending`, revise only affected downstream records, rebuild the same review ID, and preserve decisions.
- Treat `hold` and `excluded` as resolved no-action decisions and persist them into campaign state.
- When every item is resolved and the smoke gate is approved, freeze the resulting campaign copy rules and continue automatically. Do not ask for another confirmation.

## Execute the full graph

1. Research every remaining active canonical account in bounded batches. Use one researcher per account.
2. Preserve explicit failed and excluded rows; never discard null results.
3. Verify only material exceptions.
4. Generate and validate the complete canonical outreach set. Treat each `state/outreach.jsonl` row as the sole source for publisher brand, subject, body, and paragraph breaks in reviews, Gmail intents, and manual routes.
5. Search Gmail history in grouped, bounded queries. Gmail is activity evidence, never enrichment.
6. Suppress active conversations, opt-outs, equivalent prior outreach, colleague-owned relationships, and already-sent first touches.
7. Ensure every canonical account is represented in the full review, including non-actionable outcomes.
8. Build the review:

   ```bash
   python3 .agents/skills/run-ssp-outreach/scripts/campaign_engine.py build-review \
     --campaign "<campaign-id>" --stage full
   ```

## Gate 2: complete review and exact action

Use `$visualize-me` with the generated full `review.json`. The scope note must explain that `Approve shown action` authorizes only:

- creation of the exact displayed Gmail draft for an email item; or
- addition of the displayed form/profile/phone route to the local manual follow-up list.

It never authorizes sending or submitting.

Before serving the full review, enforce this card and detail-view contract:

- Add a one-line, evidence-grounded description of what each site or verified publisher group is about.
- Show the canonical site's source traffic estimate as `estimated monthly pageviews`; do not describe it as unique visitors.
- For a currently verified multi-site ownership group, separately show the combined group estimate by summing source monthly-pageview estimates for the consolidated portfolio members. List the included domains in the detail view. Do not infer missing traffic or ownership.
- Put one-click `Approve shown action` and `Exclude` controls directly on each card so opening the detailed review is optional.
- Keep the deeper review available for evidence, exact recipient or route, subject/body, notes, `Needs changes`, hold, and uncertainty.
- Use plain labels such as `Add to manual follow-up list` instead of internal implementation language such as `manual-action queue`.
- Preserve stable account IDs, all saved decisions, comments, and fields across rebuilt rounds.
- Preserve the canonical body as formatted plain text with its paragraph breaks;
  never flatten it into a bold paragraph or reconstruct it in the review.

If the default VisualizeMe template does not show those traffic, description, and quick-decision elements on the card, create and serve a campaign-local VisualizeMe template that does. Preserve the standard feedback schema, autosave behavior, JSON import/export, and localhost-only binding. Validate both the review data and local template before giving the URL to the user.

Apply submitted feedback with `apply-feedback --stage full`.

- Revise `needs_changes` items and rebuild the same review.
- Take no action on held, excluded, pending, suppressed, or failed items.
- Immediately before any approved Gmail draft creation or edit, re-list the
  exact campaign drafts using the approved recipients and subjects. Record the
  checked time and matching draft IDs, suppress duplicates, and block only
  affected items when the mailbox has drifted.
- For each approved email item with clear Gmail history and a clear drift
  check, use the Gmail connector to create exactly the canonical
  recipient/subject/body draft. Do not send or schedule it.
- Record every connector result with `record-action`.
- For approved manual routes, build a production-ready local queue from the
  canonical copy record. It must show the direct route and preformatted copy,
  provide working `Copy`, `Done`, and `Hold` controls, preserve created/updated
  timestamps, and require a reason for Hold. Keep the action local and
  unsubmitted.
- Run `validate` and publish the final counts and paths.

After all approved Gmail draft actions have a recorded terminal result and
`validate` passes, finish with final counts, validation status, and the paths to
the campaign outputs and local manual follow-up list. This showcase workflow
ends there. Do not create downstream CRM records, opportunity exports, shared
handoffs, scheduled follow-up tasks, or production integrations.

## Failure behavior

- Do not ask routine clarifying questions.
- If an optional fact is unavailable, store `null`, `unknown`, or `unverified` and choose the safer route.
- If the CSV lacks any usable URL/domain column, stop as a malformed-input error; do not invent domains.
- If Gmail is unavailable, mark draft actions failed or blocked and report them after the full review without sending.
- Preserve the last valid state and explicit retry records.
