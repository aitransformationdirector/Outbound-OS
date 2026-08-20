# Campaign contract

The confirmed brief is JSON with this shape:

```json
{
  "schema_version": 1,
  "campaign_name": "Northern Europe partnerships",
  "goal": "Book qualified introductory conversations",
  "desired_outcome": "A 30-minute discovery call",
  "offer": "A concise description of the relevant offer",
  "account_definition": "Organizations matching the confirmed audience",
  "team_profile": {
    "profile_name": "Primary team",
    "user_name": "Alex",
    "organization": "Example Co",
    "senders": [{"name": "Alex", "email": "alex@example.com"}],
    "default_offer": "Optional reusable offer",
    "preferred_channels": ["gmail", "outlook", "manual_export"],
    "connection_references": []
  },
  "save_team_profile": true,
  "channels": ["gmail", "outlook", "manual_export"],
  "targeting_rules": [
    {
      "rule_id": "market-uk",
      "kind": "must_match",
      "statement": "Operates in the United Kingdom",
      "metric": "market",
      "operator": "contains",
      "value": "United Kingdom",
      "unit": null,
      "evidence_requirement": "Current company website or supplied source data",
      "unknown_handling": "needs_review",
      "source": "user"
    }
  ],
  "accepted_recommendations": [],
  "unresolved_items": [],
  "confirmed": true
}
```

Rules use `must_match`, `exclude`, or `prioritize`. A suggested rule uses `source: "suggested"` but may enter `targeting_rules` only after explicit acceptance. Hard rules must use `unknown_handling: "needs_review"`.

`team_profile.user_name` is the preferred name used to address the person operating the campaign. It may differ from the sender. After it is captured, every workflow response must use it naturally at least once.

Allowed channels are `gmail`, `outlook`, and `manual_export`. Connections are references to app-managed connections, never secrets, passwords, tokens, cookies, or API keys.
