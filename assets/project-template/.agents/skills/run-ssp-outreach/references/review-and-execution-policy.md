# Review and execution policy

## Planned gates

The campaign has exactly two planned human gates.

### Smoke review

- Show exactly three varied publishers through final copy.
- Approval authorizes freezing campaign-specific research and copy rules and continuing to the full queue.
- It authorizes no Gmail or manual-route action.

### Full review

- Show every canonical account, not only proposed emails.
- Include account/portfolio context, provider evidence and date, route, final copy, Gmail-history result, status, gaps, and exact proposed action.
- Render subject/body from the canonical copy record and preserve its paragraph
  breaks exactly.
- Use decision label `Approve shown action`.
- For an email route, approval authorizes creation of the exact displayed Gmail draft only.
- For a manual route, approval authorizes adding it to the local manual-action queue only.
- Nothing authorizes sending, scheduling, submitting, posting, or calling.

## Decision behavior

- `approved`: retain and perform only the action defined above.
- `needs_changes`: revise affected downstream nodes and rebuild the same review ID.
- `hold`: preserve with no action.
- `excluded`: terminate with the stated reason.
- `pending`: no action.

## Manual follow-up queue

- Build the local queue from the same canonical copy records used by review and
  Gmail.
- Show the natural publisher brand, direct route, subject when applicable, and
  preformatted paragraph-preserving copy.
- Provide a working one-click `Copy` control plus `Done` and `Hold`.
- Record `queued_at`, `updated_at`, and `completed_at` when done.
- Require a non-empty `hold_reason` before saving Hold.
- Keep queue changes local. Never submit a form, post, message, or call.

## Gmail preflight

Run before building the full review:

- search Sent, Inbox, and Drafts in grouped bounded queries;
- read complete matching threads;
- suppress opt-outs, active conversations, equivalent recent outreach, colleague-owned relationships, and already-sent first touches;
- preserve exact thread and message IDs and connector URLs;
- never use Gmail as publisher enrichment.

Immediately before any authorized Gmail draft creation or edit, perform a
second bounded draft-only listing for the exact campaign recipients and
subjects. Record the checked time and matching draft IDs, suppress duplicates,
and block only items whose mailbox state drifted. Approval still authorizes
draft creation only, never sending.

## Persistent suppression memory

- Load `../_shared/suppression-memory.jsonl` before smoke selection.
- Use only Dean-confirmed prior relationships, opt-outs, colleague-owned
  accounts, and unsuccessful prior outreach.
- Preserve the originating campaign ID, canonical domain, reason type, provider
  scope, provenance, note, and recorded/updated timestamps.
- Merge shared facts into campaign-local suppression; never copy Gmail-derived
  guesses or ambiguous matches into shared memory.
- Upsert shared memory only when Dean explicitly confirms the fact.

## Action receipts

Every authorized action must retain approval ID, account ID, campaign ID, exact recipient or route, action type, connector/local result, external ID/URL when available, timestamp, and error.

Draft creation is not Sent evidence.
