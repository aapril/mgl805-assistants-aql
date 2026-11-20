"""Tests of the rules that must survive any adaptation of the template. Run them before any model."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError
from assistant.agents import AGENTS
from assistant.artifact import as_text, digest, load
from assistant.contracts import AgentResult, Criterion, Evidence, Finding, ToolResult
from assistant.decision import decide
from assistant.evidence import collect
from assistant.grounding import check
from assistant.llm import DemoModel, Ollama, model_schema
from assistant.pipeline import run
from assistant.report import save

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "example/password_policy.py", ROOT / "example/tests/test_password_policy.py"]
REFERENCE = (ROOT / "example/reference/requirement.md").read_text()
ARTIFACT = load(FILES)
TEXT = as_text(ARTIFACT)
DIGEST = digest(ARTIFACT)


def evidence(*statuses):
    tools = [ToolResult(name=f"tool{i}", status=s) for i, s in enumerate(statuses or ("passed",))]
    return Evidence(artifact_digest=DIGEST, generated_at="2026-11-20T00:00:00Z", tools=tools)


def conformance(*criteria, findings=()):
    return AgentResult(agent="conformance", status="complete", summary="s",
                       criteria=list(criteria), findings=list(findings))


def finding(text, severity="high"):
    return Finding(severity=severity, title="t", evidence=text, recommendation="r")


class ContractTests(unittest.TestCase):
    def test_model_cannot_add_fields(self):
        with self.assertRaises(ValidationError):
            AgentResult.model_validate({"agent": "x", "status": "complete", "summary": "s", "approved": True})

    def test_program_fields_hidden_from_model(self):
        props = model_schema()["$defs"]["Finding"]["properties"]
        self.assertNotIn("grounded", props)
        self.assertNotIn("source", props)


class GroundingTests(unittest.TestCase):
    def test_three_locations(self):
        r = conformance(findings=[finding("`MIN_LENGTH = 8`"), finding("`at least 12 characters`"),
                                  finding("`MIN_LENGTH = 12`"), finding("prose only")])
        marks = [f.grounded for f in check([r], TEXT, REFERENCE)[0].findings]
        self.assertEqual(marks, ["artifact", "reference_only", "absent", None])

    def test_verdict_without_quotation_becomes_unknown(self):
        r = conformance(Criterion(id="REQ-1", text="t", status="supported", evidence="looks fine"),
                        Criterion(id="REQ-2", text="t", status="supported",
                                  evidence="`any(c.isdigit() for c in password)`"))
        statuses = [c.status for c in check([r], TEXT, REFERENCE)[0].criteria]
        self.assertEqual(statuses, ["unknown", "supported"])

    def test_extracted_criterion_must_copy_the_reference(self):
        r = AgentResult(agent="criteria", status="complete", summary="s", criteria=[
            Criterion(id="REQ-1", text="t", evidence="REQ-1: A password must contain at least 12 characters."),
            Criterion(id="REQ-9", text="t", evidence="REQ-9: passwords expire every 90 days")])
        r = check([r], TEXT, REFERENCE)[0]
        self.assertEqual([c.evidence != "" for c in r.criteria], [True, False])


class DecisionTests(unittest.TestCase):
    def supported(self):
        return conformance(Criterion(id="REQ-2", text="t", status="supported", evidence="`isdigit`"))

    def test_all_satisfied_still_needs_a_person(self):
        decision, reasons = decide([self.supported()], evidence(), DIGEST)
        self.assertEqual(decision, "ready_for_human_approval")
        self.assertIn("a person must still approve", reasons[0])

    def test_tool_failure_wins_over_the_model(self):
        self.assertEqual(decide([self.supported()], evidence("failed"), DIGEST)[0], "changes_recommended")

    def test_stale_evidence_goes_to_a_person(self):
        decision, reasons = decide([self.supported()], evidence(), "0" * 64)
        self.assertEqual(decision, "human_review_required")
        self.assertTrue(any("another version" in r for r in reasons))

    def test_missing_evidence_never_approves(self):
        self.assertEqual(decide([self.supported()], None, DIGEST)[0], "human_review_required")

    def test_ungrounded_finding_never_counts_and_never_approves(self):
        r = self.supported()
        r.findings = [finding("`MIN_LENGTH = 12`")]
        check([r], TEXT, REFERENCE)
        decision, reasons = decide([r], evidence(), DIGEST)
        self.assertEqual(decision, "human_review_required")

    def test_unmet_criterion_requests_changes(self):
        r = conformance(Criterion(id="REQ-1", text="t", status="not_met", evidence="`MIN_LENGTH = 8`"))
        self.assertEqual(decide(check([r], TEXT, REFERENCE), evidence(), DIGEST)[0], "changes_recommended")


class PipelineTests(unittest.TestCase):
    def test_example_evidence_passes_although_defects_are_seeded(self):
        # The seeded defects D1 and D2 are invisible to the tools: this is why the agents exist.
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            e = collect("assistant_config.json", FILES)
        finally:
            os.chdir(cwd)
        self.assertEqual([t.status for t in e.tools], ["passed", "passed"])
        self.assertEqual(e.artifact_digest, DIGEST)

    def test_demo_pipeline_requires_human_review(self):
        report = run("test", REFERENCE, ARTIFACT, evidence(), DemoModel())
        self.assertEqual([r.agent for r in report.results], [a.name for a in AGENTS])
        self.assertEqual(report.decision, "human_review_required")
        self.assertEqual(len(report.results[0].criteria), 4)
        with tempfile.TemporaryDirectory() as tmp:
            folder = save(report, tmp)
            self.assertIn("human_review_required", (folder / "report.md").read_text())
            json.loads((folder / "report.json").read_text())

    def test_model_failure_is_visible(self):
        class Broken:
            name = "broken"
            def analyze(self, agent, payload):
                raise TimeoutError("no answer")
        report = run("test", REFERENCE, ARTIFACT, evidence(), Broken())
        self.assertEqual(report.decision, "human_review_required")
        self.assertTrue(all(r.status == "incomplete" for r in report.results))

    def test_ollama_request_is_deterministic_and_schema_bound(self):
        body = Ollama("any-model").request(AGENTS[0], {"reference": "x"})
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertIn("UNTRUSTED", body["messages"][0]["content"])
        self.assertNotIn("grounded", json.dumps(body["format"]))

    def test_model_answer_is_validated_and_source_is_reset(self):
        answer = AgentResult(agent="whatever", status="complete", summary="s",
                             findings=[finding("`MIN_LENGTH = 8`")]).model_dump_json()
        model = Ollama("m")
        with patch.object(Ollama, "post", return_value={"message": {"content": answer}}):
            report = run("test", REFERENCE, ARTIFACT, evidence(), model)
        f = report.results[1].findings[0]
        self.assertEqual((f.source, f.grounded), ("model", "artifact"))
        self.assertEqual(report.decision, "changes_recommended")


if __name__ == "__main__":
    unittest.main()
