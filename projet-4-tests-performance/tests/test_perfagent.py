"""Rules that must hold before any model is trusted. Run them without a model."""
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from demo_app.app import serve
from perfagent import grounding, loadgen, safety, slo as slo_mod
from perfagent.contracts import Analysis, Finding, Scenario, Step
from perfagent.decision import decide
from perfagent.llm import DemoModel, Ollama, _schema
from perfagent.pipeline import run

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "perf_config.json").read_text())
SLOS = slo_mod.load(ROOT / "examples/slo.json")
REQS = (ROOT / "examples/requirements.md").read_text()


def scenario(users=20, duration=2, steps=None):
    steps = steps or [Step(method=e["method"], path=e["path"], weight=1, body=e.get("body")) for e in CONFIG["catalog"]]
    return Scenario(name="t", virtual_users=users, duration_s=duration, steps=steps)


class App:
    """The demo application on a free port, for the duration of a test class."""
    @classmethod
    def setUpClass(cls):
        cls.server = serve(0)
        cls.target = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()


class SafetyTests(unittest.TestCase):
    def test_target_outside_allowlist_is_refused_before_the_model(self):
        class Spy(DemoModel):
            called = False
            def plan(self, payload):
                Spy.called = True
                return super().plan(payload)
        with self.assertRaises(safety.UnsafeTarget):
            run(CONFIG, REQS, SLOS, "https://www.example.com", Spy())
        self.assertFalse(Spy.called)

    def test_clamp_removes_unknown_endpoints_and_caps_load(self):
        s = scenario(users=500, duration=3600, steps=[Step(path="/admin/delete", weight=1), Step(path="/health", weight=1)])
        executed, notes = safety.clamp(s, CONFIG)
        self.assertEqual([st.path for st in executed.steps], ["/health"])
        self.assertEqual((executed.virtual_users, executed.duration_s), (50, 120))
        self.assertEqual(len(notes), 3)


class LoadAndSloTests(App, unittest.TestCase):
    def test_seeded_defects_are_measured(self):
        m = loadgen.run(self.target, scenario(users=20, duration=2))
        results = {r.id: r for r in slo_mod.evaluate(SLOS, m)}
        self.assertEqual(results["PERF-1"].status, "not_met")   # the pool of one connection
        self.assertEqual(results["PERF-2"].status, "met")
        self.assertGreater(m.total_requests, 50)

    def test_light_load_does_not_measure_the_requirement(self):
        m = loadgen.run(self.target, scenario(users=2, duration=1))
        self.assertTrue(all(r.status == "not_measured" for r in slo_mod.evaluate(SLOS, m)))


class GroundingTests(App, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m = loadgen.run(cls.target, scenario(users=20, duration=2))
        cls.slos = slo_mod.evaluate(SLOS, cls.m)
        cls.p95 = next(e.p95_ms for e in cls.m.endpoints if e.path.startswith("/search"))

    def ground(self, evidence):
        a = Analysis(summary="s", findings=[Finding(severity="high", title="t", evidence=evidence, recommendation="r")])
        return grounding.check(a, self.m, self.slos, self.m.scenario, {"/health", "/books", "/search", "/reserve"})

    def test_measured_number_is_grounded(self):
        self.assertEqual(self.ground(f"p95 of /search is {self.p95} ms").findings[0].grounded, "measured")

    def test_invented_number_is_not(self):
        a = self.ground("p95 of /search is 98765 ms")
        self.assertEqual(a.findings[0].grounded, "absent")
        self.assertTrue(any("98765" in x for x in a.limitations))

    def test_mixed_and_unknown_path(self):
        self.assertEqual(self.ground(f"/search p95 {self.p95} ms, CPU at 87654 %").findings[0].grounded, "partly")
        self.assertEqual(self.ground("/admin is slow").findings[0].grounded, "absent")

    def test_model_cannot_see_or_set_program_fields(self):
        self.assertNotIn("grounded", json.dumps(_schema(Analysis)))
        a = Analysis(summary="s", findings=[Finding(severity="low", title="t", evidence="prose", recommendation="r", grounded="measured")])
        self.assertIsNone(grounding.check(a, self.m, self.slos, self.m.scenario, set()).findings[0].grounded)


class DecisionTests(unittest.TestCase):
    def slos(self, *statuses):
        from perfagent.contracts import SloResult
        return [SloResult(id=f"P{i}", text="t", status=s, measured=1.0, threshold=2.0) for i, s in enumerate(statuses)]

    def measurement(self):
        from perfagent.contracts import Measurement
        return Measurement(target="t", scenario=scenario(), started_at="x", elapsed_s=1, total_requests=10,
                           throughput_rps=10, error_rate=0, endpoints=[])

    def test_all_met_still_needs_a_person(self):
        d, reasons = decide(self.measurement(), self.slos("met", "met"), Analysis(summary="s"), [])
        self.assertEqual(d, "ready_for_human_approval")
        self.assertIn("a person must still approve", reasons[0])

    def test_unmet_requirement_requests_changes(self):
        self.assertEqual(decide(self.measurement(), self.slos("met", "not_met"), Analysis(summary="s"), [])[0], "changes_recommended")

    def test_adjusted_scenario_or_missing_measurement_goes_to_a_person(self):
        self.assertEqual(decide(self.measurement(), self.slos("met"), Analysis(summary="s"), ["capped"])[0], "human_review_required")
        self.assertEqual(decide(None, self.slos("not_measured"), Analysis(summary="s"), [])[0], "human_review_required")


class PipelineTests(App, unittest.TestCase):
    def test_demo_pipeline_finds_the_seeded_defects(self):
        cfg = {**CONFIG, "limits": {**CONFIG["limits"], "default_duration_s": 2}}
        report = run(cfg, REQS, SLOS, self.target, DemoModel())
        self.assertEqual(report.decision, "changes_recommended")
        self.assertTrue(any(r.startswith("PERF-1 not met") for r in report.reasons))

    def test_model_proposals_are_clamped_and_its_numbers_checked(self):
        plan = Scenario(name="aggressive", virtual_users=900, duration_s=2,
                        steps=[Step(path="/search?q=python", weight=3), Step(path="/admin/purge", weight=1)])
        analysis = Analysis(summary="s", findings=[Finding(severity="high", title="Search is slow",
                            evidence="p95 of /search is 4321 ms", recommendation="Add connections to the pool.")])
        answers = iter([plan.model_dump_json(), analysis.model_dump_json()])
        cfg = {**CONFIG, "limits": {**CONFIG["limits"], "max_virtual_users": 20}}
        with patch.object(Ollama, "post", side_effect=lambda body: {"message": {"content": next(answers)}}):
            report = run(cfg, REQS, SLOS, self.target, Ollama("qwen-test"))
        self.assertEqual(report.executed.virtual_users, 20)
        self.assertEqual([s.path for s in report.executed.steps], ["/search?q=python"])
        self.assertEqual(report.analysis.findings[0].grounded, "absent")
        self.assertEqual(report.decision, "changes_recommended")

    def test_ollama_request_is_deterministic_and_schema_bound(self):
        body = Ollama("m").request("x", Scenario, {})
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertIn("DATA", body["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
