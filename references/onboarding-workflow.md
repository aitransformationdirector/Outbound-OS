# Shared onboarding workflow

Use this workflow in every supported host. Host packaging and folder-opening instructions may differ; campaign meaning and safeguards may not.

## Start list-first

Inspect the message and attachments. If the user has not supplied the full intake, read [guided-intake.md](guided-intake.md), start with its welcome and support line exactly as written, prefill known information, and ask for the remainder in one compact message. Keep the example attached to every unanswered intake question; do not shorten the form into category labels without examples.

Accept:

- CSV, TSV, or XLSX attachments;
- a pasted list with at least an account name or website per row;
- a connected Google Sheet when the host has an appropriate connection.

If Google Sheets is unavailable, request an XLSX or CSV export without restarting the intake. Never guess an ambiguous account identity or website. Missing websites may be researched later; ambiguous matches remain `needs_review`.

Once the user supplies or confirms `team_profile.user_name`, address them by that name at least once in every subsequent user-facing response. Keep the name in the confirmed brief and reusable profile; do not infer it from an email address.

## Audit before building

Run the bundled `scripts/build_project.py audit --source <path> --context <campaign-context>` command after resolving the source into a local file. Report totals, duplicates, unusable rows, missing names or websites, and available columns.

Translate the targeting description into explicit rules using [campaign-contract.md](campaign-contract.md):

- `must_match` for mandatory eligibility;
- `exclude` for disqualifiers;
- `prioritize` for ranking signals.

Ask only when the difference materially affects eligibility. Unknown evidence for a hard rule defaults to `needs_review`, never exclusion.

## Recommend filters, then confirm

Recommend only filters relevant to the goal, account definition, source columns, and likely public evidence. Show each recommendation's rationale, evidence requirement, and expected coverage. Suggestions remain inactive until accepted.

Present the final brief with source, goal, offer, account totals, all three rule groups, accepted suggestions, channels, and unresolved items. End with:

> Do you want Outbound OS to apply any other filtering before I create the campaign? You can accept, remove, or edit any of the rules above.

Do not build until the user confirms the brief. Nothing in onboarding authorizes sending messages.
