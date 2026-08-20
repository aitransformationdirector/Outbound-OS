#!/usr/bin/env python3
"""Validate the generated Outbound OS project and its neutral contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED = (
    "AGENTS.md",
    "START_HERE.md",
    "RUN.md",
    "PROJECT_INPUT.json",
    "system/defaults.json",
    "system/graph/campaign-graph.json",
    "system/schemas/team-profile.schema.json",
    "system/schemas/campaign-brief.schema.json",
    "system/schemas/targeting-rule.schema.json",
    "system/schemas/target-account.schema.json",
    "system/schemas/proposed-action.schema.json",
    "system/adapters/gmail.json",
    "system/adapters/outlook.json",
    "system/adapters/manual_export.json",
    ".agents/skills/run-outbound-campaign/SKILL.md",
    ".agents/skills/run-outbound-campaign/scripts/campaign_engine.py",
    ".agents/skills/sync-outbound-crm/SKILL.md",
    ".agents/skills/sync-outbound-crm/scripts/crm_export.py",
    ".agents/skills/monitor-outbound-replies/SKILL.md",
    ".agents/skills/monitor-outbound-replies/scripts/normalize_replies.py",
)


def json_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if "01_CAMPAIGNS" not in path.parts)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")
    for path in json_files(root):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON in {path.relative_to(root)}: {exc}")
    input_path = root / "PROJECT_INPUT.json"
    if input_path.is_file():
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if payload.get("status") != "ready" or payload.get("next_prompt") != "run":
            errors.append("PROJECT_INPUT.json is not ready to run")
        if not payload.get("campaign_id") or payload.get("brief", {}).get("confirmed") is not True:
            errors.append("PROJECT_INPUT.json lacks a confirmed campaign")
        if not payload.get("user_name") or not payload.get("brief", {}).get("team_profile", {}).get("user_name"):
            errors.append("PROJECT_INPUT.json lacks the preferred user name")
        runtime_path = payload.get("runtime_skill_path")
        if runtime_path != ".agents/skills/run-outbound-campaign/SKILL.md":
            errors.append("PROJECT_INPUT.json has an invalid runtime skill path")
        elif not (root / runtime_path).is_file():
            errors.append("PROJECT_INPUT.json points to a missing bundled runtime skill")
    for adapter_id in ("gmail", "outlook", "manual_export"):
        path = root / "system/adapters" / f"{adapter_id}.json"
        if path.is_file():
            adapter = json.loads(path.read_text(encoding="utf-8"))
            if adapter.get("adapter_id") != adapter_id or adapter.get("may_send") is not False:
                errors.append(f"unsafe or invalid adapter: {adapter_id}")
    for relative in ("system/defaults.json", "system/graph/campaign-graph.json"):
        path = root / relative
        if not path.is_file():
            continue
        lowered = path.read_text(encoding="utf-8").casefold()
        legacy_terms = ("s" + "sp", "pub" + "lisher", "ti" + "ki", "de" + "an", "travel" + "_adjacent", "minimum_monthly" + "_traffic")
        for term in legacy_terms:
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                errors.append(f"legacy assumption in {relative}: {term}")
    for path in (root / "system/schemas").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for ref in re.findall(r'"\$ref"\s*:\s*"([^"#]+\.json)"', json.dumps(payload)):
            if not (path.parent / ref).is_file():
                errors.append(f"missing schema reference from {path.name}: {ref}")
    for path in (root / "START_HERE.md", root / "RUN.md"):
        if path.is_file() and "{{" in path.read_text(encoding="utf-8"):
            errors.append(f"unresolved template token in {path.name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    errors = validate(Path(args.root).expanduser().resolve())
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
