# Research and copy rules

## Source and selection

- Preserve the supplied CSV byte-for-byte.
- Normalize URLs and hosts deterministically.
- Apply the configured monthly-traffic threshold.
- Apply the configured geography filter deterministically when source country data is present. Preserve missing-country rows as `unknown_geography`.
- Exclude unknown traffic by default while preserving the row and reason.
- Classify against the configured target vertical labels and retain `unresolved` explicitly.
- Audit a bounded sample of negative classifications.

## Provider evidence

- Build a current public profile for the named SSP/ad manager.
- Preserve exact publisher-specific evidence and checked dates.
- Treat ads.txt, sellers.json, scripts, or similar signals according to what they actually prove.
- Never infer the exact product, wrapper, placement, visible ad, or commercial relationship from a seller line alone.
- If the profile is incomplete, use generic `the company handling the advertising` wording or a question.

## Ownership and contacts

- Consolidate common owners and portfolios before contact research.
- Prefer one canonical commercial account and one primary route.
- Keep `canonical_domain`, the canonical publisher/account identity, and the
  reader-facing `publisher_brand` as separate fields.
- Resolve `publisher_brand` from the publisher's current public presentation,
  source site name, or a conservative normalized domain label, in that order.
  Preserve intentional casing. Do not include `www`, a scheme, path, or public
  suffix unless it is genuinely part of the public brand.
- Resolve and validate `publisher_brand` before selecting or rendering the
  smoke review.
- Prioritize monetization/ad operations, commercial leadership, small-publisher owners, advertising/sales routes, then official commercial forms.
- Never use guessed email patterns, paid enrichment, private databases, editorial forms, privacy routes, or access-control bypasses.
- Stop when one current public route is actionable.

## First-touch copy

- Plain text, normally 60–120 words.
- Use `publisher_brand` in the subject and body.
- Preserve paragraph breaks as double newlines in the canonical plain-text body.
- Create exactly one versioned canonical copy record per account and review
  stage. Reviews, Gmail intents, and manual-route outputs must derive from it
  without channel-specific rewriting.
- Do not tell the publisher what its own site, content, company, or audience does.
- Keep research mechanics and technical evidence internal.
- Do not use ads.txt, DIRECT, RESELLER, seller IDs, SSP, DSP, Prebid, header bidding, yield, inventory, integration, programmatic, or CPM.
- Ask whether the named provider is involved unless independently confirmed as the actual manager.
- Mention a secondary manager only with account-specific evidence.
- Present only the configured truthful TIKI routes and proof point.
- Use one primary ask and no more than two question marks.
- Never promise results, uplift, revenue, fill, latency, or performance.

## Standard branches

Generate deterministically after smoke approval:

- current provider signal;
- provider removed/absent/unknown;
- verified secondary manager;
- verified managed-provider complementary route;
- verified prior relationship;
- special current commercial context;
- general commercial routing.

Use model-written copy only for verified exceptions and validate it with the same rules.
