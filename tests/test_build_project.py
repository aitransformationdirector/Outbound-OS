from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts/build_project.py"
SPEC = importlib.util.spec_from_file_location("outbound_builder", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def brief(name: str = "Universal accounts", channels: list[str] | None = None) -> dict:
    return {
        "schema_version": 1,
        "campaign_name": name,
        "goal": "Book qualified conversations",
        "desired_outcome": "Introductory meeting",
        "offer": "A relevant service",
        "account_definition": "Organizations matching the supplied brief",
        "team_profile": {
            "profile_name": "Primary team",
            "user_name": "Alex",
            "organization": "Example Company",
            "senders": [{"name": "Alex", "email": "alex@example.com"}],
            "default_offer": "A relevant service",
            "preferred_channels": channels or ["gmail", "outlook", "manual_export"],
            "connection_references": [],
        },
        "save_team_profile": True,
        "channels": channels or ["gmail", "outlook", "manual_export"],
        "targeting_rules": [
            {
                "rule_id": "market-fit",
                "kind": "must_match",
                "statement": "Operates in the selected market",
                "metric": "market",
                "operator": "contains",
                "value": "selected market",
                "unit": None,
                "evidence_requirement": "Current website or supplied data",
                "unknown_handling": "needs_review",
                "source": "user",
            },
            {
                "rule_id": "scale",
                "kind": "prioritize",
                "statement": "Prioritize larger relevant organizations",
                "metric": "organization_scale",
                "operator": "descending",
                "value": None,
                "unit": None,
                "evidence_requirement": "Supplied or public evidence",
                "unknown_handling": "not_applicable",
                "source": "user",
            },
        ],
        "accepted_recommendations": [],
        "unresolved_items": [],
        "confirmed": True,
    }


def write_minimal_xlsx(path: Path) -> None:
    content_types = """<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>"""
    sheet = """<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Account Name</t></is></c><c r="B1" t="inlineStr"><is><t>Website</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>North Hotel</t></is></c><c r="B2" t="inlineStr"><is><t>north.example</t></is></c></row></sheetData></worksheet>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


class BuilderTests(unittest.TestCase):
    def test_imports_csv_tsv_text_and_xlsx(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            csv_path = root / "accounts.csv"
            csv_path.write_text("Company,Website\nAlpha,alpha.example\nAlpha duplicate,alpha.example\nBeta,\n,\n", encoding="utf-8")
            accounts, audit = MODULE.import_accounts(csv_path)
            self.assertEqual(audit["imported_accounts"], 2)
            self.assertEqual(audit["duplicates"], 1)
            self.assertEqual(audit["unusable_rows"], 1)
            self.assertEqual(accounts[1]["qualification_status"], "needs_review")

            tsv_path = root / "accounts.tsv"
            tsv_path.write_text("name\tdomain\nOne\tone.example\n", encoding="utf-8")
            self.assertEqual(MODULE.import_accounts(tsv_path)[1]["imported_accounts"], 1)

            text_path = root / "accounts.txt"
            text_path.write_text("Example One\nExample Two\n", encoding="utf-8")
            self.assertEqual(MODULE.import_accounts(text_path)[1]["missing_websites"], 2)

            xlsx_path = root / "accounts.xlsx"
            write_minimal_xlsx(xlsx_path)
            xlsx_accounts, _ = MODULE.import_accounts(xlsx_path)
            self.assertEqual(xlsx_accounts[0]["canonical_domain"], "north.example")

            observed_headers = root / "observed-export.csv"
            observed_headers.write_text("Publisher Domain,Business Name\ntravel.example,Travel Example\n", encoding="utf-8")
            observed_accounts, observed_audit = MODULE.import_accounts(observed_headers)
            self.assertEqual(observed_audit["name_column"], "Business Name")
            self.assertEqual(observed_audit["website_column"], "Publisher Domain")
            self.assertEqual(observed_accounts[0]["canonical_name"], "Travel Example")

    def test_adaptive_recommendations_are_contextual_and_inactive(self) -> None:
        hotels = MODULE.recommendations("Hotel groups in Europe", ["name", "website"])
        destinations = MODULE.recommendations("Tourism destination organizations", ["name"])
        technology = MODULE.recommendations("Technology platforms", ["company"])
        media = MODULE.recommendations("Audience-funded media websites", ["website"])
        self.assertIn("property-footprint", {row["recommendation_id"] for row in hotels})
        self.assertIn("geographic-remit", {row["recommendation_id"] for row in destinations})
        self.assertIn("technology-category", {row["recommendation_id"] for row in technology})
        self.assertIn("business-model", {row["recommendation_id"] for row in media})
        self.assertTrue(all(row["active"] is False for row in hotels + destinations + technology + media))

    def test_hard_rule_unknowns_cannot_exclude(self) -> None:
        payload = brief()
        payload["targeting_rules"][0]["unknown_handling"] = "exclude"
        with self.assertRaisesRegex(ValueError, "needs_review"):
            MODULE.validate_brief(payload)

    def test_credentials_are_rejected(self) -> None:
        payload = brief()
        payload["team_profile"]["api_token"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "Credentials are forbidden"):
            MODULE.validate_brief(payload)

    def test_preferred_user_name_is_required(self) -> None:
        payload = brief()
        del payload["team_profile"]["user_name"]
        with self.assertRaisesRegex(ValueError, "user_name"):
            MODULE.validate_brief(payload)

    def test_build_profiles_actions_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "accounts.csv"
            source.write_text("name,website\nAlpha,alpha.example\nBeta,beta.example\n", encoding="utf-8")
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief()), encoding="utf-8")
            output = root / "Outbound OS Projects"
            result = MODULE.build_project(source, brief_path, output, "codex")
            project = Path(result["project_path"])
            self.assertTrue((project / "PROJECT_INPUT.json").is_file())
            self.assertTrue((project / ".agents/skills/run-outbound-campaign/SKILL.md").is_file())
            self.assertTrue((project / ".claude/skills/run-outbound-campaign/SKILL.md").is_file())
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertTrue((project / "system/runtime/campaign_engine.py").is_file())
            self.assertTrue(result["handoff"]["do_not_run_in_builder_task"])
            self.assertTrue(result["handoff"]["do_not_attach_folder_to_builder_task"])
            self.assertEqual(result["handoff"]["user_name"], "Alex")
            self.assertEqual(result["supported_runtimes"], ["codex", "claude"])
            self.assertEqual(result["preferred_runtime"], "codex")
            project_input = json.loads((project / "PROJECT_INPUT.json").read_text(encoding="utf-8"))
            self.assertEqual(project_input["user_name"], "Alex")
            self.assertEqual(project_input["runtime_skill_paths"], {
                "codex": ".agents/skills/run-outbound-campaign/SKILL.md",
                "claude": ".claude/skills/run-outbound-campaign/SKILL.md",
            })
            self.assertEqual(project_input["next_prompts"], {"codex": "run", "claude": "/run-outbound-campaign"})
            self.assertIn("Alex", (project / "START_HERE.md").read_text(encoding="utf-8"))
            profiles = json.loads((output / "_shared/team-profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles["profiles"][0]["organization"], "Example Company")
            resumed = MODULE.build_project(source, brief_path, output, "codex")
            self.assertTrue(resumed["resumed"])

            campaign = result["campaign_id"]
            messages = root / "messages.jsonl"
            message_rows = [
                {"message_id": "message-1", "account_id": "acct-one", "recipient": "one@example.com", "subject": "Hello", "body": "A reviewed message.", "channel": "gmail"},
                {"message_id": "message-2", "account_id": "acct-two", "recipient": "two@example.com", "subject": "Hello", "body": "A reviewed message.", "channel": "outlook"},
                {"message_id": "message-3", "account_id": "acct-three", "recipient": "https://example.com/contact", "subject": None, "body": "A reviewed message.", "channel": "manual_export"},
            ]
            messages.write_text("".join(json.dumps(row) + "\n" for row in message_rows), encoding="utf-8")
            engine = project / "system/runtime/campaign_engine.py"
            prepared = subprocess.run([sys.executable, str(engine), "--root", str(project), "prepare-actions", "--campaign", campaign, "--messages", str(messages)], text=True, capture_output=True, check=False)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            actions = json.loads(prepared.stdout)["actions"]
            self.assertEqual({row["channel"] for row in actions}, {"gmail", "outlook", "manual_export"})
            self.assertTrue(all(row["sending_authorized"] is False for row in actions))
            self.assertTrue(all(row["approval_status"] == "pending" for row in actions))

            validation = subprocess.run([sys.executable, str(engine), "--root", str(project), "validate", "--campaign", campaign], text=True, capture_output=True, check=False)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

            relationships = project / "01_CAMPAIGNS" / campaign / "state/relationships.jsonl"
            relationships.write_text("\n".join([
                json.dumps({"campaign_id": campaign, "account_id": "acct-one", "account_name": "Alpha", "relationship_status": "substantive_reply", "evidence": [{"message_id": "reply-1"}]}),
                json.dumps({"campaign_id": campaign, "account_id": "acct-two", "account_name": "Beta", "relationship_status": "no_reply", "evidence": []}),
            ]) + "\n", encoding="utf-8")
            crm = project / "system/runtime/crm_export.py"
            exported = subprocess.run([sys.executable, str(crm), "--root", str(project), "--campaign", campaign], text=True, capture_output=True, check=False)
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertEqual(json.loads(exported.stdout), {"included": 1, "excluded": 1})

            replies = root / "replies.jsonl"
            replies.write_text(json.dumps({"adapter": "gmail", "account_id": "acct-one", "checked_at": "2026-08-20T10:00:00Z", "classification": "substantive_reply", "evidence": {"message_id": "reply-1"}}) + "\n", encoding="utf-8")
            monitor = project / "system/runtime/normalize_replies.py"
            normalized = subprocess.run([sys.executable, str(monitor), "--root", str(project), "--campaign", campaign, "--input", str(replies)], text=True, capture_output=True, check=False)
            self.assertEqual(normalized.returncode, 0, normalized.stderr)

            second_source = root / "second.csv"
            second_source.write_text("name,website\nGamma,gamma.example\n", encoding="utf-8")
            second = brief("Second campaign")
            second["team_profile"]["profile_name"] = "Another team"
            second["team_profile"]["user_name"] = "Morgan"
            second["team_profile"]["organization"] = "Another Company"
            second_brief = root / "second-brief.json"
            second_brief.write_text(json.dumps(second), encoding="utf-8")
            MODULE.build_project(second_source, second_brief, output)
            profiles = json.loads((output / "_shared/team-profiles.json").read_text(encoding="utf-8"))
            self.assertEqual({row["profile_name"] for row in profiles["profiles"]}, {"Primary team", "Another team"})

    def test_claude_preference_changes_handoff_not_campaign_core(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "accounts.csv"
            source.write_text("name,website\nAlpha,alpha.example\n", encoding="utf-8")
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief()), encoding="utf-8")
            result = MODULE.build_project(source, brief_path, root / "projects", "claude")
            project = Path(result["project_path"])
            payload = json.loads((project / "PROJECT_INPUT.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["preferred_runtime"], "claude")
            self.assertEqual(payload["next_prompt"], "/run-outbound-campaign")
            self.assertEqual(payload["shared_runtime_path"], "system/runtime/campaign_engine.py")
            self.assertIn("@AGENTS.md", (project / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertIn("system/runtime/campaign_engine.py", (project / ".agents/skills/run-outbound-campaign/SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("system/runtime/campaign_engine.py", (project / ".claude/skills/run-outbound-campaign/SKILL.md").read_text(encoding="utf-8"))

    def test_claude_plugin_and_codex_skill_share_builder(self) -> None:
        manifest = json.loads((SKILL / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "outbound-os")
        self.assertEqual(manifest["version"], MODULE.BUILDER_VERSION)
        claude_skill = (SKILL / "skills/new-campaign/SKILL.md").read_text(encoding="utf-8")
        codex_skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/build_project.py", claude_skill)
        self.assertIn("scripts/build_project.py", codex_skill)
        self.assertIn("references/onboarding-workflow.md", claude_skill)
        self.assertIn("references/onboarding-workflow.md", codex_skill)

    def test_host_packages_do_not_duplicate_runtime_logic(self) -> None:
        runtime = SKILL / "assets/project-template/system/runtime"
        host_roots = [
            SKILL / "assets/project-template/.agents/skills",
            SKILL / "assets/project-template/.claude/skills",
        ]
        for filename in ("campaign_engine.py", "normalize_replies.py", "crm_export.py"):
            shared = runtime / filename
            self.assertTrue(shared.is_file())
            lowered = shared.read_text(encoding="utf-8").casefold()
            self.assertNotIn(".agents", lowered)
            self.assertNotIn(".claude", lowered)
            self.assertNotIn("codex", lowered)
            self.assertNotIn("claude", lowered)
            for host_root in host_roots:
                self.assertEqual(list(host_root.rglob(filename)), [])

    def test_invalid_runtime_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "accounts.csv"
            source.write_text("name,website\nAlpha,alpha.example\n", encoding="utf-8")
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Preferred runtime"):
                MODULE.build_project(source, brief_path, root / "projects", "other")

    def test_empty_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "empty.csv"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty"):
                MODULE.import_accounts(path)


if __name__ == "__main__":
    unittest.main()
