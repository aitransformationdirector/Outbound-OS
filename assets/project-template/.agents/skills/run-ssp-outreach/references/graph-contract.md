# Graph contract

## State ownership

- Treat `01_CAMPAIGNS/<campaign_id>/state/` as canonical campaign state.
- Treat each versioned `state/outreach.jsonl` row as the canonical copy record
  for its account and review stage; reviews and action outputs are derived
  projections and must validate byte-for-byte subject/body equality.
- Let only the primary Codex agent write canonical state.
- Have subagents return JSON conforming to the node's schema.
- Write with the deterministic campaign engine after validation.
- Preserve raw inputs and append decision/activity events.
- Treat `../_shared/suppression-memory.jsonl` as the only cross-campaign state.
  It may contain only Dean-confirmed facts with originating campaign ID and
  provenance; campaign-local state remains isolated.

## Node result envelope

Every agent result must identify:

- `campaign_id`;
- entity ID (`candidate_id` or `account_id`);
- completion status;
- checked timestamp;
- exact evidence URLs;
- explicit gaps or errors.

Never represent failure as a missing item or filtered null.

## Fan-out and barriers

- Fan out independent candidate or account work with at most six concurrent agents.
- Stream each account through research, conditional verification, disposition, and copy without waiting for unrelated accounts.
- Use barriers only for ownership consolidation, negative-audit evaluation, smoke review, full review, and final reconciliation.

## Routing

- Route obvious source filtering and state transitions deterministically.
- Route provider claim strength, contact route, copy branch, product family, and onboarding phase from validated structured values.
- Escalate to a verifier only when the result changes account scope, route safety, claim strength, or external action.

## Cycles

- Bound route discovery by `max_route_attempts_per_account`.
- Dedupe against every checked route, including rejected routes.
- Rebuild only review items affected by feedback.
- Stop repeated research when no new evidence appears or the attempt limit is reached.

## Invalidation

- Ownership change invalidates contact, disposition, copy, Gmail preflight, and action intent.
- Contact change invalidates copy recipient, Gmail preflight, and action intent.
- Provider-evidence change invalidates claim wording and copy validation.
- Copy-only feedback invalidates copy validation and review data only.
- Exclusion terminates downstream action nodes.

## Completeness

At every barrier, reconcile expected entities against completed, excluded, held, and failed/retry required. Block the next gate when any entity is unexplained.
