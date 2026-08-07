# Ready to run

This Codex project has been prepared from `{{SOURCE_NAME}}`.

- SSP/ad manager: `{{TARGET_PROVIDER}}`
- Minimum monthly traffic: `{{MINIMUM_MONTHLY_TRAFFIC}}`
- Target verticals: `{{TARGET_VERTICALS}}`
- Target geographies: `{{TARGET_GEOGRAPHIES}}`
- Campaign ID: `{{CAMPAIGN_ID}}`

## Start

1. Open this folder as a local Codex project.
2. Start or continue a task in this folder.
3. Type exactly:

   `run`

Codex will execute the prepared graph and pause only for:

1. the three-publisher VisualizeMe smoke review;
2. the complete VisualizeMe review showing every publisher, exact copy, Gmail-history result, and proposed action.

On the complete review, `Approve shown action` authorizes creation of the exact displayed Gmail draft for an email route. It never authorizes sending. Form, profile, and phone routes stay in the local manual follow-up list and are never submitted automatically.

Campaign files live under `01_CAMPAIGNS`. Review data appears under `02_REVIEW`. Campaign-local reports and manual follow-up outputs appear under `03_OUTPUTS`.

This showcase edition ends after approved Gmail drafts and local manual follow-up actions are reconciled and validated. It does not create downstream CRM records, opportunity exports, scheduled follow-up tasks, or production integrations.

See `ARCHITECTURE.md` for the graph design, safeguards, trade-offs, and limitations.
