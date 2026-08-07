#!/usr/bin/env python3
"""Exercise the SSP project builder in a disposable directory."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    skill_root = Path(__file__).resolve().parent.parent
    builder = skill_root / "scripts/build_project.py"
    with tempfile.TemporaryDirectory(prefix="ssp-builder-test-") as temporary:
        temp = Path(temporary)
        source = temp / "publisher-source.csv"
        source.write_text(
            "Domain,Monthly Visitors,Country,Category,Domain Manager\n"
            "travelone.example,100000,United Kingdom,Travel,ExampleManager\n"
            "traveltwo.example,75k,United States,Travel,ExampleManager\n"
            "eurotravel.example,90000,France,Travel,ExampleManager\n"
            "smalltravel.example,49999,United Kingdom,Travel,ExampleManager\n"
            "unknowntravel.example,N/A,France,Travel,ExampleManager\n",
            encoding="utf-8",
        )
        output_root = temp / "Desktop/Codex/SSP Projects"
        base_command = [
            sys.executable,
            str(builder),
            "--source",
            str(source),
            "--provider",
            "Raptive",
            "--minimum-monthly-traffic",
            "50k",
            "--verticals",
            "travel,travel adjacent",
            "--geographies",
            "United Kingdom,United States",
            "--project-label",
            "Raptive-Travel-Test",
            "--output-root",
            str(output_root),
        ]
        first = json.loads(run(base_command).stdout)
        assert first["resumed"] is False
        assert first["counts"]["parsed_rows"] == 5
        assert first["counts"]["eligible"] == 2
        assert first["counts"]["below_threshold"] == 1
        assert first["counts"]["unknown_traffic"] == 1
        assert first["counts"]["excluded_geography"] == 1
        project = Path(first["project_path"])
        assert project.is_dir()

        defaults = read_json(project / "system/defaults.json")
        assert defaults["selection"]["minimum_monthly_pageviews"] == 50000
        assert defaults["selection"]["target_verticals"] == [
            "travel",
            "travel_adjacent",
        ]
        assert defaults["selection"]["target_geographies"] == [
            "United Kingdom",
            "United States",
        ]
        prepared = read_json(project / "PROJECT_INPUT.json")
        assert prepared["status"] == "ready"
        assert prepared["next_prompt"] == "run"
        suppression_memory = Path(prepared["suppression_memory_path"])
        assert suppression_memory == (
            output_root / "_shared/suppression-memory.jsonl"
        ).resolve()
        assert suppression_memory.is_file()
        campaign_id = prepared["campaign_id"]
        state = read_json(project / "01_CAMPAIGNS" / campaign_id / "state/campaign.json")
        assert state["target_provider"] == "Raptive"
        preserved = project / "01_CAMPAIGNS" / campaign_id / "source/original.csv"
        assert hashlib.sha256(preserved.read_bytes()).hexdigest() == hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
        assert "{{" not in (project / "START_HERE.md").read_text(encoding="utf-8")
        assert "{{" not in (project / "RUN.md").read_text(encoding="utf-8")
        assert not (project / "03_OUTPUTS/pipeline").exists()
        assert not (project / ".agents/skills/sync-ssp-crm").exists()
        assert not (project / "AUTOMATION_PROMPT.md").exists()
        graph = read_json(project / "system/graph/campaign-graph.json")
        assert [
            node["id"] for node in graph["nodes"] if node.get("human_gate") is True
        ] == ["smoke_review", "full_review"]
        run_skill = (
            project / ".agents/skills/run-ssp-outreach/SKILL.md"
        ).read_text(encoding="utf-8")
        assert "This showcase workflow" in run_skill
        assert "scheduled follow-up tasks" in run_skill
        project_agents = (project / "AGENTS.md").read_text(encoding="utf-8")
        assert "Showcase boundary" in project_agents
        assert "scheduled follow-up tasks" in project_agents
        assert "canonical copy" in project_agents.casefold()
        assert "publisher_brand" in project_agents
        assert "working `Copy`, `Done`, and `Hold` controls" in project_agents
        assert "at least once per 60 seconds" in project_agents
        assert "re-list the" in project_agents
        assert "exact campaign drafts" in project_agents
        assert "../_shared/suppression-memory.jsonl" in project_agents
        outreach_schema = read_json(project / "system/schemas/outreach.schema.json")
        assert "copy_record_id" in outreach_schema["required"]
        assert "publisher_brand" in outreach_schema["required"]
        graph_ids = {node["id"] for node in graph["nodes"]}
        assert "resolve_publisher_brand" in graph_ids
        assert "gmail_draft_drift_check" in graph_ids

        second = json.loads(run(base_command).stdout)
        assert second["resumed"] is True
        assert second["project_path"] == first["project_path"]
        assert len(
            [
                path
                for path in output_root.iterdir()
                if path.is_dir() and path.name != "_shared"
            ]
        ) == 1

        changed = list(base_command)
        threshold_index = changed.index("50k")
        changed[threshold_index] = "80k"
        third = json.loads(run(changed).stdout)
        assert third["resumed"] is False
        assert third["project_path"].endswith("-2")
        assert third["counts"]["eligible"] == 1

        print(
            "PASS: fresh Raptive build, parameters, transactional project, "
            "two gates, execution-quality contracts, Pipeline-free boundary, "
            "resume safety, and project validation"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
