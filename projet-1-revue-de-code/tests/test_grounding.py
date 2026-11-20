"""Replays the 1.5B reviews of November 20, 2026.

Agent 3 quoted a diff it had corrected; agent 2 validated a claim about the diff
with a name that only the issue contains.
"""
from pathlib import Path
import unittest
from review.models import AgentResult, Finding, Criterion
from review.grounding import check, missing
from review.agents.agent7_synthesis import recommendation
from review.llm import model_schema
from tests.test_review import context, clean_evidence

LAB = Path(__file__).resolve().parent.parent / "lab"
DIFF = (LAB / "pr-subtract.patch").read_text()
ISSUE = (LAB / "issue-subtract.md").read_text()

# Excerpt returned by agent 3: the diff, except that `substract` became `subtract`.
FABRICATED = DIFF.split("diff --git a/tests")[0].replace("def substract", "def subtract")
FAITHFUL = DIFF.split("diff --git a/tests")[0]


def lab_context():
    return context(issue_subject="Add a subtraction function", issue_description=ISSUE,
                   diff=DIFF, evidence=clean_evidence())


def agent(n, *findings, criteria=()):
    return AgentResult(agent=n, status="complete", summary="Analysis",
                       findings=list(findings), criteria=list(criteria))


def finding(evidence, severity="high", **kw):
    return Finding(severity=severity, title="New function subtract added",
                   evidence=evidence, recommendation="Check.", **kw)


class GroundingTests(unittest.TestCase):
    def test_corrected_excerpt_is_not_grounded(self):
        self.assertEqual(missing(FABRICATED, DIFF), ["def subtract(a, b):"])

    def test_faithful_excerpt_is_grounded(self):
        self.assertEqual(missing(FAITHFUL, DIFF), [])

    def test_backtick_span_checked_against_issue_and_diff(self):
        results = check([agent(2, finding("The diff adds `substract` but `test_subtract` is absent."))], lab_context())
        self.assertEqual(results[0].findings[0].grounded, "absent")
        results = check([agent(2, finding("The diff adds `substract` and `square_root`."))], lab_context())
        self.assertEqual(results[0].findings[0].grounded, "diff")

    def test_prose_stays_unverified(self):
        results = check([agent(2, finding("No unit test exercises the subtraction."))], lab_context())
        self.assertIsNone(results[0].findings[0].grounded)

    def test_model_cannot_declare_itself_grounded(self):
        self.assertNotIn("grounded", model_schema()["$defs"]["Finding"]["properties"])
        results = check([agent(2, finding("No test.", grounded="diff"))], lab_context())
        self.assertIsNone(results[0].findings[0].grounded)

    def test_file_outside_the_diff(self):
        results = check([agent(3, finding("No test.", file="example_app/parser.py"))], lab_context())
        self.assertEqual(results[0].findings[0].grounded, "absent")

    def test_ungrounded_finding_goes_to_a_person(self):
        results = [agent(n) for n in range(1, 8)]
        results[3] = agent(4, criteria=[Criterion(id="AC-1", text="subtract", status="not_met")])
        results[2] = agent(3, finding(FABRICATED))
        results = check(results, lab_context())
        decision, reasons = recommendation(lab_context(), results)
        self.assertFalse(any("agent 3 to verify" in r for r in reasons))
        self.assertTrue(any("Agent 3: evidence not found" in r for r in reasons))
        self.assertTrue(any("Ungrounded evidence" in x for x in results[2].limitations))
        # Another reason still requests changes: grounding never makes a review more favorable.
        self.assertEqual(decision, "changes_recommended")

    def test_alone_ungrounded_finding_never_approves(self):
        results = [agent(n) for n in range(1, 8)]
        results[3] = agent(4, criteria=[Criterion(id="AC-1", text="subtract", status="supported")])
        results[2] = agent(3, finding(FABRICATED))
        decision, _ = recommendation(lab_context(), check(results, lab_context()))
        self.assertEqual(decision, "human_review_required")

    def test_agent1_criterion_must_quote_the_issue(self):
        exact = Criterion(id="AC-1", text="t", status="unknown",
                          evidence="`subtract(a, b)` is added to `example_app/calculator.py` and returns `a - b`.")
        invented = Criterion(id="AC-2", text="t", status="supported", evidence="subtract handles complex numbers")
        r = check([agent(1, criteria=[exact, invented])], lab_context())[0]
        self.assertEqual([c.status for c in r.criteria], ["unknown", "unknown"])
        self.assertEqual(sum("not found" in x for x in r.limitations), 1)


AGENT2 = ("The diff adds a new function `subtract` but does not include any unit tests for it. "
          "This is a critical issue as it will prevent the function from being tested and verified.")


class LocationTests(unittest.TestCase):
    def test_requirement_name_does_not_ground_a_claim_about_the_diff(self):
        r = check([agent(2, finding(AGENT2))], lab_context())[0]
        self.assertEqual(r.findings[0].grounded, "issue_only")
        self.assertTrue(any("'subtract'" in x and "not in the diff" in x for x in r.limitations))

    def test_issue_only_surfaces_the_misspelling_for_a_person(self):
        results = [agent(n) for n in range(1, 8)]
        results[3] = agent(4, criteria=[Criterion(id="AC-1", text="subtract", status="supported")])
        results[1] = agent(2, finding(AGENT2))
        decision, reasons = recommendation(lab_context(), check(results, lab_context()))
        self.assertTrue(any("Agent 2: cites names found in the issue but not in the diff" in r for r in reasons))
        # The finding is real text, so it still counts; the decision is never more favorable.
        self.assertEqual(decision, "changes_recommended")

    def test_excerpt_from_the_diff(self):
        self.assertEqual(check([agent(3, finding(FAITHFUL))], lab_context())[0].findings[0].grounded, "diff")
