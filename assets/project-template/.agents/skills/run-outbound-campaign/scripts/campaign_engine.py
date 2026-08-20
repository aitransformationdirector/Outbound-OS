#!/usr/bin/env python3
"""Deterministic validation and neutral action preparation for Outbound OS."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CHANNELS = {"gmail", "outlook", "manual_export"}
QUALIFICATIONS = {"pending_research", "qualified", "excluded", "needs_review", "failed"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def campaign_root(root: Path, campaign_id: str) -> Path:
    return root / "01_CAMPAIGNS" / campaign_id


def validate(root: Path, campaign_id: str) -> list[str]:
    errors: list[str] = []
    base = campaign_root(root, campaign_id)
    state_path = base / "state/campaign.json"
    accounts_path = base / "source/accounts.jsonl"
    if not state_path.is_file():
        return ["campaign state is missing"]
    state = read_json(state_path)
    if state.get("campaign_id") != campaign_id:
        errors.append("campaign ID mismatch")
    brief = state.get("brief", {})
    if brief.get("confirmed") is not True:
        errors.append("campaign brief is not confirmed")
    if not brief.get("team_profile", {}).get("user_name"):
        errors.append("campaign brief lacks the preferred user name")
    channels = brief.get("channels", [])
    if not channels or set(channels) - CHANNELS:
        errors.append("campaign has invalid channels")
    if state.get("external_actions", {}).get("sending_authorized") is not False:
        errors.append("campaign must not authorize sending")
    accounts = read_jsonl(accounts_path)
    if not accounts:
        errors.append("campaign has no accounts")
    seen: set[str] = set()
    for account in accounts:
        account_id = account.get("account_id")
        if not account_id or account_id in seen:
            errors.append("account IDs must be present and unique")
        seen.add(str(account_id))
        if not account.get("canonical_name"):
            errors.append(f"{account_id} lacks canonical_name")
        if account.get("qualification_status") not in QUALIFICATIONS:
            errors.append(f"{account_id} has invalid qualification_status")
        if not account.get("canonical_domain") and account.get("resolution_status") != "needs_review":
            errors.append(f"{account_id} without a website must need review")
    for action in read_jsonl(base / "state/proposed-actions.jsonl"):
        if action.get("channel") not in CHANNELS:
            errors.append(f"{action.get('action_id')} has invalid channel")
        if action.get("sending_authorized") is not False:
            errors.append(f"{action.get('action_id')} authorizes sending")
        if action.get("approval_status") == "approved" and action.get("execution_status") not in {"not_started", "draft_created", "manual_item_created", "held", "failed"}:
            errors.append(f"{action.get('action_id')} has invalid execution status")
    return errors


def prepare_actions(root: Path, campaign_id: str, messages_path: Path) -> list[dict[str, Any]]:
    state = read_json(campaign_root(root, campaign_id) / "state/campaign.json")
    selected_channels = set(state["brief"]["channels"])
    actions: list[dict[str, Any]] = []
    for message in read_jsonl(messages_path):
        required = ("message_id", "account_id", "recipient", "body", "channel")
        if any(not message.get(key) for key in required):
            raise ValueError("Each message requires message_id, account_id, recipient, body, and channel")
        channel = message["channel"]
        if channel not in selected_channels:
            raise ValueError(f"Message channel {channel} is not enabled for this campaign")
        fingerprint = f"{campaign_id}:{message['message_id']}:{channel}"
        actions.append({
            "schema_version": 1,
            "campaign_id": campaign_id,
            "action_id": "action-" + hashlib.sha256(fingerprint.encode()).hexdigest()[:12],
            "account_id": message["account_id"],
            "channel": channel,
            "recipient": message["recipient"],
            "subject": message.get("subject"),
            "canonical_message_id": message["message_id"],
            "body": message["body"],
            "approval_status": "pending",
            "execution_status": "not_started",
            "sending_authorized": False,
        })
    output = campaign_root(root, campaign_id) / "state/proposed-actions.jsonl"
    write_jsonl(output, actions)
    return actions


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--root", default=".")
    commands = root.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--campaign", required=True)
    prepare = commands.add_parser("prepare-actions")
    prepare.add_argument("--campaign", required=True)
    prepare.add_argument("--messages", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    try:
        if args.command == "validate":
            errors = validate(root, args.campaign)
            print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
            return 0 if not errors else 1
        actions = prepare_actions(root, args.campaign, Path(args.messages).expanduser().resolve())
        print(json.dumps({"created": len(actions), "actions": actions}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
