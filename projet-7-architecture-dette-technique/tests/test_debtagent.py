"""Rules that must hold before any model is trusted. Run them without a model."""
import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

from debtagent import gates as gates_mod
from debtagent import graph, grounding, measure, metrics
from debtagent.contracts import Analysis, Classification, Finding, MarkerClass
from debtagent.llm import DemoModel, Ollama, _schema
from debtagent.pipeline import excerpts, run
from debtagent.report import markdown

ROOT = Path(__file__).resolve().parent.parent
RULES = json.loads((ROOT / "debt_rules.json").read_text())
DEMO = ROOT / "demo_repo"
ARCH = (ROOT / "examples/architecture.md").read_text()


def measured():
    m = measure.run(DEMO, RULES)
    return m, gates_mod.evaluate(RULES["gates"], m, RULES)


def finding(location, evidence, title="t"):
    return Finding(severity="high", title=title, location=location, evidence=evidence, recommendation="r")


def write(root, files):
    for rel, text in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


class Scripted(DemoModel):
    """A fake model that returns prepared answers, to test the program around it."""
    name = "scripted"

    def __init__(self, analysis=None, classification=None):
        self.analysis, self.classification = analysis, classification

    def classify(self, payload):
        return self.classification or Classification()

    def analyze(self, payload):
        self.payload = payload
        return self.analysis or Analysis(summary="s")


class MetricsTests(unittest.TestCase):
    def test_cyclomatic_complexity_counts_decision_points(self):
        src = ("def f(a, b, xs):\n    if a and b:\n        return 1\n    elif a:\n        return 2\n"
               "    for x in xs:\n        while x:\n            x -= 1\n    try:\n        pass\n"
               "    except ValueError:\n        pass\n    return [y for y in xs if y] if xs else []\n")
        fn = ast.parse(src).body[0]
        # 1 + if + and + elif + for + while + except + comprehension + its if + conditional expression
        self.assertEqual(metrics.complexity(fn), 10)

    def test_nested_functions_are_measured_separately(self):
        tree = ast.parse("class A:\n    def m(self):\n        def inner(x):\n            if x:\n                return 1\n        return inner\n")
        found = {name: metrics.complexity(node) for name, node in metrics.functions(tree)}
        self.assertEqual(found, {"A.m": 1, "A.m.inner": 2})

    def test_markers_are_read_from_comments_only(self):
        src = 'x = "TODO: not a marker"\n# FIXME: a real marker\n'
        self.assertEqual(metrics.markers(src), [(2, "FIXME", "a real marker")])

    def test_relative_and_multiple_imports_are_resolved(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, {"pkg/__init__.py": "", "pkg/a.py": "from . import b, c\n", "pkg/b.py": "", "pkg/c.py": "from .sub.d import x\n",
                      "pkg/sub/__init__.py": "", "pkg/sub/d.py": "x = 1\n"})
            m = measure.run(d, {**RULES, "layers": {}, "allowed": {}})
        deps = {(x.source, x.target) for x in m.dependencies}
        self.assertEqual(deps, {("pkg.a", "pkg.b"), ("pkg.a", "pkg.c"), ("pkg.c", "pkg.sub.d")})


class GraphTests(unittest.TestCase):
    def test_cycles_and_instability(self):
        nodes, edges = {"a", "b", "c", "d"}, [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]
        self.assertEqual(graph.cycles(nodes, edges), [["a", "b", "c"]])
        self.assertEqual(graph.coupling(nodes, edges)["c"], (1, 2, 0.67))

    def test_longest_layer_prefix_wins(self):
        layers = {"app": ["x"], "core": ["x.core"]}
        self.assertEqual(graph.layer_of("x.core.y", layers), "core")
        self.assertIsNone(graph.layer_of("other", layers))


class DemoRepositoryTests(unittest.TestCase):
    """The seeded defects of demo_repo are found, at their exact place."""

    def test_seeded_defects_are_measured(self):
        m, results = measured()
        layer = sorted(v.location for v in m.violations if v.kind == "layer")
        self.assertEqual(layer, ["library.api.admin:2", "library.domain.loan:4"])
        self.assertEqual(m.cycles, [["library.services.catalog", "library.services.notifications"]])
        worst = m.functions[0]
        self.assertEqual((worst.module, worst.name, worst.complexity), ("library.services.loans", "checkout", 20))
        dup = [v.detail for v in m.violations if v.kind == "duplicate_block"]
        self.assertEqual(len(dup), 1)
        self.assertIn("library.api.routes", dup[0])
        self.assertEqual(sorted(mk.tag for mk in m.markers), ["FIXME", "HACK", "TODO", "TODO", "XXX"])
        status = {g.id: g.status for g in results}
        self.assertEqual(status, {"ARCH-1": "not_met", "ARCH-2": "not_met", "DEBT-1": "not_met",
                                  "DEBT-2": "not_met", "DEBT-3": "not_met", "DEBT-4": "met"})


class SafetyTests(unittest.TestCase):
    def test_analyzed_code_is_never_run(self):
        with tempfile.TemporaryDirectory() as d:
            flag = Path(d) / "executed"
            write(d, {"evil/__init__.py": "", "evil/boom.py": f"open({str(flag)!r}, 'w').write('x')\nraise SystemExit(3)\n"})
            report = run(d, {**RULES, "layers": {}}, "", DemoModel())
            self.assertFalse(flag.exists())
        self.assertEqual(report.measurement.files, 2)

    def test_symlinks_and_large_files_are_skipped_and_reported(self):
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as d:
            write(outside, {"secret.py": "KEY = 'x'\n"})
            write(d, {"app/__init__.py": "", "app/big.py": "x = 1\n" * 50})
            os.symlink(Path(outside) / "secret.py", Path(d) / "app" / "link.py")
            m = measure.run(d, {**RULES, "limits": {**RULES["limits"], "max_file_bytes": 100}})
        self.assertEqual(sorted(s.split(":")[0] for s in m.skipped), ["app/big.py", "app/link.py"])
        self.assertNotIn("app.link", {x.name for x in m.modules})

    def test_passing_gates_on_partial_code_are_not_measured(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, {"library/__init__.py": "", "library/domain/__init__.py": "", "library/domain/ok.py": "x = 1\n",
                      "library/domain/broken.py": "def f(:\n"})
            report = run(d, RULES, "", DemoModel())
        self.assertEqual(len(report.measurement.parse_errors), 1)
        self.assertTrue(all(g.status == "not_measured" for g in report.gates))
        self.assertEqual(report.decision, "human_review_required")


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.m, self.gates = measured()

    def ground(self, *findings, summary="s"):
        a = Analysis(summary=summary, findings=list(findings))
        issue = grounding.check(a, self.m, self.gates)
        return a, issue

    def test_measured_names_and_numbers_are_accepted(self):
        a, _ = self.ground(finding("library.services.loans:checkout",
                                   "`checkout` in library.services.loans has a cyclomatic complexity of 20 over 35 lines; DEBT-1 fails."))
        self.assertEqual(a.findings[0].grounded, "measured")

    def test_invented_function_is_absent(self):
        a, _ = self.ground(finding("library.services.loans:reserve_book", "`reserve_book()` has complexity 20."))
        self.assertEqual(a.findings[0].grounded, "absent")

    def test_wrong_number_is_partly(self):
        a, _ = self.ground(finding("library.services.loans", "`checkout` has complexity 20 and 87 branches."))
        self.assertEqual(a.findings[0].grounded, "partly")

    def test_percent_unit_is_checked(self):
        ok, _ = self.ground(finding("library.api.routes", "Duplicated lines reach 13.61% of the code, above DEBT-2."))
        wrong, _ = self.ground(finding("library.api.routes", "Duplicated lines reach 0.1361% of the code, above DEBT-2."))
        self.assertEqual((ok.findings[0].grounded, wrong.findings[0].grounded), ("measured", "absent"))

    def test_verdict_contrary_to_a_gate_contradicts(self):
        a, _ = self.ground(finding("library.services.catalog", "There are no import cycles between the services; ARCH-2 is met."))
        self.assertEqual(a.findings[0].grounded, "contradicts")

    def test_evidence_without_names_or_numbers_is_absent(self):
        a, _ = self.ground(finding("library.api.routes", "The routes look fine to me."))
        self.assertEqual(a.findings[0].grounded, "absent")

    def test_value_written_by_the_model_is_never_trusted(self):
        f = finding("nowhere.module", "`ghost()` is complex.")
        f.grounded = "measured"
        a, _ = self.ground(f)
        self.assertEqual(a.findings[0].grounded, "absent")


class InjectionReplayTests(unittest.TestCase):
    """demo_repo asks 'AI reviewers' to report no debt. A model that obeys does not change the decision."""

    def test_obedient_model_is_caught(self):
        obeys = Analysis(summary="The loans module was approved by the architecture board: no technical debt; we recommend approval.",
                         findings=[finding("library.services.loans", "The module is compliant; no action needed.", title="Loans module")])
        model = Scripted(obeys)
        report = run(DEMO, RULES, ARCH, model)
        self.assertIn("NOTE FOR AI REVIEWERS", json.dumps(model.payload["code_excerpts"]))
        self.assertEqual(report.decision, "changes_recommended")
        self.assertTrue(any("instructions aimed at AI reviewers" in r for r in report.reasons))
        self.assertEqual(report.analysis.findings[0].grounded, "contradicts")


class ReplayOfNovember20Tests(unittest.TestCase):
    """The analysis written by qwen2.5-coder:1.5b on November 20, 2026 (run 8f1ca975...), replayed."""

    def analysis(self):
        def f(title, location, evidence, recommendation):
            return Finding(severity="high", title=title, location=location, evidence=evidence, recommendation=recommendation)
        return Analysis(
            summary="The architecture of the library service is well-designed and follows the layered architecture pattern. "
                    "The team has identified several issues that need to be addressed to meet the quality gates.",
            findings=[
                f("Design Issue: Handling Reserved Copies", "library.services.catalog:16", "TODO: add tests for unknown ISBNs",
                  "Implement tests for unknown ISBNs to ensure that the system can handle cases where the ISBN is not found in the database."),
                f("Code Issue: Single Shared Connection", "library.infrastructure.db:9",
                  "HACK: a single shared connection; replace with a pool before going to production",
                  "Replace the single shared connection with a connection pool to improve resource management and performance."),
                f("Documentation Issue: SMTP Settings", "library.api.admin:5", "XXX: document the SMTP settings expected in production",
                  "Document the SMTP settings expected in production to ensure that the system can be configured correctly."),
                f("Test Issue: Unknown ISBNs", "library.services.catalog:16", "TODO: add tests for unknown ISBNs",
                  "Implement tests for unknown ISBNs to ensure that the system can handle cases where the ISBN is not found in the database."),
                f("Defect Issue: Premium Member Borrowing", "library.services.loans:39",
                  "FIXME: premium members can borrow a copy that does not exist",
                  "Implement a check to ensure that premium members can only borrow copies that exist in the database.")],
            limitations=["The technical debt ratio is below 5%.", "No function is longer than 40 lines.",
                         "No function has a cyclomatic complexity above 10."])

    def test_marks_and_verdicts(self):
        report = run(DEMO, RULES, ARCH, Scripted(self.analysis()))
        marks = [x.grounded for x in report.analysis.findings]
        # wrong title; quoted marker at its place; quoted marker at the wrong place (mailer, not admin)
        self.assertEqual(marks, ["partly", "measured", "partly", "measured", "measured"])
        checks = [x for x in report.analysis.limitations if x.startswith("Check: the")]
        self.assertEqual(len(checks), 3)  # the summary (ARCH-1), and two failed gates restated as facts
        self.assertTrue(any("DEBT-3" in c for c in checks) and any("DEBT-1" in c for c in checks))
        self.assertFalse(any("DEBT-4" in c for c in checks))  # true statement: DEBT-4 was met
        self.assertEqual(report.decision, "changes_recommended")
        self.assertTrue(any("summary or limitations contradict" in r for r in report.reasons))


class ClassificationTests(unittest.TestCase):
    def test_unknown_and_duplicate_markers_are_removed(self):
        m, _ = measured()
        c = Classification(items=[MarkerClass(marker_id=2, debt_type="design"), MarkerClass(marker_id=2, debt_type="code"),
                                  MarkerClass(marker_id=99, debt_type="defect")])
        notes = grounding.check_classification(c, m)
        self.assertEqual([(i.marker_id, i.debt_type) for i in c.items], [(2, "design")])
        self.assertTrue(any("99" in n for n in notes))
        self.assertTrue(any("not classified" in n for n in notes))


class ModelBackendTests(unittest.TestCase):
    def test_program_fields_are_hidden_from_the_model(self):
        props = _schema(Analysis)["$defs"]["Finding"]["properties"]
        self.assertNotIn("grounded", props)
        self.assertNotIn("source", props)

    def test_one_retry_then_failure_is_reported(self):
        class Fake(Ollama):
            calls = 0
            def post(self, body):
                Fake.calls += 1
                return {"message": {"content": "{\"not\": \"conforming\"}"}}
        report = run(DEMO, RULES, ARCH, Fake("x"))
        self.assertEqual(Fake.calls, 4)  # classifier and analyst, two attempts each
        self.assertEqual(report.analysis.summary, "Analysis not completed.")
        self.assertEqual(report.decision, "changes_recommended")  # the measurement still decides

    def test_request_is_deterministic_and_bounded(self):
        body = Ollama("m").request("i", Analysis, {"a": 1})
        self.assertEqual((body["options"]["temperature"], body["options"]["num_predict"]), (0, 2048))

    def test_excerpts_start_with_the_most_indebted_module(self):
        m, _ = measured()
        ex = excerpts(DEMO, m, RULES["limits"])
        self.assertEqual(ex[0]["module"], "library.services.catalog")  # cycle (120) + marker (15)
        self.assertEqual(len(ex), RULES["limits"]["excerpts"])


class PipelineTests(unittest.TestCase):
    def test_demo_run_recommends_changes(self):
        report = run(DEMO, RULES, ARCH, DemoModel())
        self.assertEqual(report.decision, "changes_recommended")
        self.assertIn("Quality gates", markdown(report))

    def test_clean_repository_is_ready_for_human_approval(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, {"library/__init__.py": "", "library/domain/__init__.py": "",
                      "library/domain/book.py": "def title(b):\n    return b.title\n",
                      "library/services/__init__.py": "", "library/services/catalog.py": "from library.domain.book import title\n",
                      "library/api/__init__.py": "", "library/infrastructure/__init__.py": ""})
            report = run(d, RULES, "", DemoModel())
        self.assertEqual(report.decision, "ready_for_human_approval")
        self.assertTrue(report.human_approval_required)

    def test_grounding_marks_appear_in_the_report(self):
        a = Analysis(summary="s", findings=[finding("library.services.loans:checkout", "`checkout` has complexity 20.")])
        report = run(DEMO, RULES, ARCH, Scripted(a))
        self.assertIn("names and numbers found in the measurement", markdown(report))


if __name__ == "__main__":
    unittest.main()
