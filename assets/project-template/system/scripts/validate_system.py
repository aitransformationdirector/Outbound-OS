#!/usr/bin/env python3
"""Validate the static Codex SSP outreach project before a campaign runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "AGENTS.md",
    "START_HERE.md",
    "RUN.md",
    ".codex/config.toml",
    ".agents/skills/run-ssp-outreach/SKILL.md",
    ".agents/skills/run-ssp-outreach/agents/openai.yaml",
    ".agents/skills/run-ssp-outreach/scripts/campaign_engine.py",
    "system/defaults.json",
    "system/graph/campaign-graph.json",
    "system/schemas/manual-action.schema.json",
    "system/schemas/suppression-memory.schema.json",
)

FORBIDDEN_PATHS = (
    "AUTOMATION_PROMPT.md",
    ".agents/skills/sync-ssp-crm",
    "03_OUTPUTS/pipeline",
    "system/graph/crm-state-machine.json",
    "system/schemas/crm-event.schema.json",
    "system/schemas/crm-state.schema.json",
    "system/schemas/pipeline-opportunity.schema.json",
)

REQUIRED_AGENTS = (
    "provider-profiler",
    "ownership-resolver",
    "publisher-researcher",
    "evidence-verifier",
)


def discover_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    for candidate in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
        if (candidate / "system/defaults.json").is_file():
            return candidate
    raise ValueError("Could not locate system/defaults.json")


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: {exc}")
        return None


def validate_graph(root: Path, errors: list[str]) -> None:
    graph_path = root / "system/graph/campaign-graph.json"
    graph = load_json(graph_path, errors)
    if not isinstance(graph, dict):
        return
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("Campaign graph must contain nodes")
        return
    ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    if len(ids) != len(nodes) or any(not value for value in ids):
        errors.append("Every graph node must have an ID")
        return
    if len(ids) != len(set(ids)):
        errors.append("Campaign graph contains duplicate node IDs")
    node_by_id = {node["id"]: node for node in nodes}
    for node in nodes:
        for dependency in node.get("depends_on", []):
            if dependency not in node_by_id:
                errors.append(f"{node['id']} depends on unknown node {dependency}")
        output = node.get("output")
        if output and not (root / "system/schemas" / output).is_file():
            errors.append(f"{node['id']} references missing schema {output}")

    incoming = {node_id: set(node_by_id[node_id].get("depends_on", [])) for node_id in ids}
    ready = [node_id for node_id, dependencies in incoming.items() if not dependencies]
    visited: list[str] = []
    while ready:
        current = ready.pop()
        visited.append(current)
        for node_id, dependencies in incoming.items():
            if current in dependencies:
                dependencies.remove(current)
                if not dependencies and node_id not in visited and node_id not in ready:
                    ready.append(node_id)
    if len(visited) != len(ids):
        errors.append("Campaign graph contains a dependency cycle")

    gates = {node["id"] for node in nodes if node.get("human_gate") is True}
    if gates != {"smoke_review", "full_review"}:
        errors.append(
            "Campaign graph must contain exactly the smoke_review and full_review human gates"
        )
    draft_node = node_by_id.get("create_gmail_drafts", {})
    if draft_node.get("requires_explicit_item_action") is not True:
        errors.append("Gmail draft node must require explicit item-level action")

    def ancestors(node_id: str) -> set[str]:
        result: set[str] = set()
        stack = list(node_by_id.get(node_id, {}).get("depends_on", []))
        while stack:
            dependency = stack.pop()
            if dependency in result:
                continue
            result.add(dependency)
            stack.extend(node_by_id.get(dependency, {}).get("depends_on", []))
        return result

    if "full_review" not in ancestors("create_gmail_drafts"):
        errors.append("Gmail drafts must be downstream of the full review")
    if "gmail_draft_drift_check" not in ancestors("create_gmail_drafts"):
        errors.append("Gmail drafts must be downstream of the mailbox drift check")
    if "gmail_history_preflight" not in ancestors("full_review"):
        errors.append("Full review must be downstream of Gmail-history preflight")


def validate_defaults(root: Path, errors: list[str]) -> None:
    defaults = load_json(root / "system/defaults.json", errors)
    if not isinstance(defaults, dict):
        return
    outreach = defaults.get("outreach", {})
    review = defaults.get("review", {})
    if outreach.get("smoke_test_accounts") != 3:
        errors.append("Smoke-test account count must be 3")
    if review.get("planned_human_gates") != ["smoke_review", "full_review"]:
        errors.append("Defaults must declare exactly two planned human gates")
    if outreach.get("send_email") is not False:
        errors.append("send_email must remain false")
    if outreach.get("submit_forms") is not False:
        errors.append("submit_forms must remain false")
    threshold = defaults.get("selection", {}).get("minimum_monthly_pageviews")
    if not isinstance(threshold, int) or threshold <= 0:
        errors.append("Minimum monthly traffic must be a positive integer")
    verticals = defaults.get("selection", {}).get("target_verticals")
    if not isinstance(verticals, list) or not verticals:
        errors.append("At least one target vertical is required")
    if "automation" in defaults or "pipeline" in defaults:
        errors.append("Showcase defaults must not configure downstream systems")
    suppression_memory = defaults.get("suppression_memory", {})
    if suppression_memory.get("write_policy") != "dean_confirmed_only":
        errors.append("Shared suppression memory must require Dean confirmation")
    if suppression_memory.get("path") != "../_shared/suppression-memory.jsonl":
        errors.append("Shared suppression memory must use the project-family registry")


def validate_prepared_input(root: Path, errors: list[str]) -> None:
    input_path = root / "PROJECT_INPUT.json"
    if not input_path.is_file():
        return
    prepared = load_json(input_path, errors)
    if not isinstance(prepared, dict):
        return
    if prepared.get("status") != "ready":
        errors.append("PROJECT_INPUT.json must have status ready")
    if prepared.get("next_prompt") != "run":
        errors.append("PROJECT_INPUT.json must set next_prompt to run")
    memory_path = prepared.get("suppression_memory_path")
    if not memory_path or not Path(memory_path).is_file():
        errors.append("PROJECT_INPUT.json points to missing suppression memory")
    campaign_id = prepared.get("campaign_id")
    if not campaign_id:
        errors.append("PROJECT_INPUT.json lacks campaign_id")
    elif not (root / "01_CAMPAIGNS" / campaign_id / "state/campaign.json").is_file():
        errors.append("PROJECT_INPUT.json points to a missing campaign")


def validate_skill(path: Path, errors: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: {exc}")
        return
    if not text.startswith("---\n"):
        errors.append(f"{path} lacks YAML front matter")
        return
    parts = text.split("---", 2)
    if len(parts) < 3 or "name:" not in parts[1] or "description:" not in parts[1]:
        errors.append(f"{path} front matter needs name and description")


def validate_python(path: Path, errors: list[str]) -> None:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except (OSError, SyntaxError) as exc:
        errors.append(f"{path}: {exc}")


def validate_root(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    for relative in FORBIDDEN_PATHS:
        if (root / relative).exists():
            errors.append(f"Showcase project contains downstream-only path: {relative}")
    for agent in REQUIRED_AGENTS:
        if not (root / ".codex/agents" / f"{agent}.toml").is_file():
            errors.append(f"Missing custom agent: {agent}")

    for path in sorted((root / "system").rglob("*.json")):
        load_json(path, errors)
    validate_graph(root, errors)
    validate_defaults(root, errors)
    validate_prepared_input(root, errors)

    for relative in (".agents/skills/run-ssp-outreach/SKILL.md",):
        path = root / relative
        if path.is_file():
            validate_skill(path, errors)
    for relative in (
        ".agents/skills/run-ssp-outreach/scripts/campaign_engine.py",
        "system/scripts/validate_system.py",
    ):
        path = root / relative
        if path.is_file():
            validate_python(path, errors)

    placeholder_paths = [
        root / "AGENTS.md",
        root / "START_HERE.md",
        root / ".agents/skills/run-ssp-outreach/SKILL.md",
    ]
    for path in placeholder_paths:
        if path.is_file():
            lowered = path.read_text(encoding="utf-8").casefold()
            if "todo:" in lowered or "fixme:" in lowered:
                warnings.append(f"Placeholder marker found in {path.relative_to(root)}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args = parser.parse_args()
    try:
        root = discover_root(args.root)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    errors, warnings = validate_root(root)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: project structure, graph, safeguards, skills, and scripts are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
