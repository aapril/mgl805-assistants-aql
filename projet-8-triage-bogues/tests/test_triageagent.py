"""Rules that must hold before any model is trusted. Run them without a model (Git is required)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from demo import history
from triageagent import gitrepo, logs
from triageagent.contracts import BugReport, Drafts
from triageagent.llm import DemoModel, Ollama, _schema
from triageagent.pipeline import UnsafeInput, gather, run
from triageagent.report import markdown

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "triage_config.json").read_text())
CONFIG["execution"]["repro_dir"] = str(ROOT / "examples/repro")
LOG = ROOT / "examples/staging.log"


class Demo:
    """A fresh demonstration repository for each test class."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.repo = history.build(Path(cls.tmp) / "lib")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def sha(self, subject):
        return next(c for c in gitrepo.git(self.repo, "log", "--format=%H %s").splitlines() if subject in c).split()[0]


class Scripted(DemoModel):
    name = "scripted"

    def __init__(self, drafts):
        self.drafts = drafts

    def draft(self, payload):
        self.payload = payload
        return self.drafts


def report(sig, title, explanation, suspected=None, patch=""):
    return BugReport(signature_id=sig, title=title, severity="high", suspected_commit=suspected,
                     explanation=explanation, suggested_patch=patch)


@unittest.skipUnless(shutil.which("git"), "Git is required")
class LogTests(unittest.TestCase):
    def test_signatures_counts_and_deployments(self):
        recs = logs.records(LOG.read_text())
        deploys = logs.deployments(recs, CONFIG["deploy_pattern"])
        self.assertEqual([r for _, r in deploys], ["v1", "v2"])
        sigs = logs.signatures(recs, CONFIG["path_prefixes"], deploys[-1][0], 50)
        found = [(s.exception, s.count, s.count_before_deploy) for s in sigs]
        self.assertEqual(found, [("TimeoutError", 5, 3), ("ZeroDivisionError", 6, 0), ("KeyError", 4, 0), (None, 1, 0)])
        self.assertEqual(sigs[1].frames[-1].file, "library/services/fines.py")  # path prefix removed

    def test_text_addressed_to_an_ai_is_flagged(self):
        sigs = logs.signatures(logs.records(LOG.read_text()), CONFIG["path_prefixes"], "2026-11-12T08:00:00Z", 50)
        self.assertTrue(sigs[3].suspicious)
        self.assertFalse(any(s.suspicious for s in sigs[:3]))

    def test_numbers_and_user_input_are_normalized(self):
        self.assertEqual(logs.normalize('request_id=r-1 Slow search (2.4 s) q="abc"'), "Slow search (<n> s) q=<str>")

    def test_the_static_log_matches_the_demo_code(self):
        self.assertEqual(LOG.read_text(), history.make_log())


@unittest.skipUnless(shutil.which("git"), "Git is required")
class CorrelationTests(Demo, unittest.TestCase):
    def evidence(self, allow=False):
        return gather(LOG, self.repo, CONFIG, allow_execution=allow)

    def test_window_holds_the_commits_of_the_last_deployment(self):
        ev = self.evidence()
        self.assertEqual([c.subject for c in ev.window], [c[1] for c in history.COMMITS[2:]])

    def test_pre_existing_error_is_not_blamed_on_the_deployment(self):
        t = self.evidence().triage[0]
        self.assertEqual((t.status, t.attribution, t.candidates), ("pre_existing", "pre_existing", []))

    def test_blame_points_at_the_changed_line(self):
        t = self.evidence().triage[1]
        self.assertEqual(t.candidates[0].sha, self.sha("average daily fine"))
        self.assertEqual(t.attribution, "probable")

    def test_cause_outside_the_traceback_file_is_found_by_its_diff(self):
        t = self.evidence().triage[2]
        self.assertEqual(t.candidates[0].sha, self.sha("contact_email"))
        self.assertTrue(any("'email'" in e for e in t.candidates[0].evidence))
        self.assertTrue(any("blame alone would point at an old commit" in n for n in t.notes))

    def test_reproduction_confirms_both_regressions(self):
        ev = self.evidence(allow=True)
        self.assertEqual([t.attribution for t in ev.triage[1:3]], ["confirmed", "confirmed"])
        self.assertEqual(ev.triage[2].reproduction.at_parent, "pass")


@unittest.skipUnless(shutil.which("git"), "Git is required")
class SafetyTests(Demo, unittest.TestCase):
    def test_nothing_runs_without_both_permissions(self):
        self.assertTrue(gather(LOG, self.repo, CONFIG).execution.startswith("not requested"))
        refused = {**CONFIG, "execution": {**CONFIG["execution"], "allowed": False}}
        ev = gather(LOG, self.repo, refused, allow_execution=True)
        self.assertEqual(ev.execution, "not allowed by the configuration")
        self.assertTrue(all(t.reproduction is None for t in ev.triage))

    def test_the_model_cannot_supply_a_command(self):
        props = _schema(Drafts)["$defs"]["BugReport"]["properties"]
        self.assertFalse({"command", "grounded", "patch_status"} & set(props))

    def test_repository_is_unchanged(self):
        before = gitrepo.git(self.repo, "status", "--porcelain")
        run(LOG, self.repo, CONFIG, DemoModel(), allow_execution=True)
        self.assertEqual(gitrepo.git(self.repo, "status", "--porcelain"), before)

    def test_large_log_and_non_repository_are_refused(self):
        with self.assertRaises(UnsafeInput):
            gather(LOG, self.repo, {**CONFIG, "limits": {**CONFIG["limits"], "max_log_bytes": 10}})
        with tempfile.TemporaryDirectory() as d, self.assertRaises(UnsafeInput):
            gather(LOG, d, CONFIG)


@unittest.skipUnless(shutil.which("git"), "Git is required")
class GroundingTests(Demo, unittest.TestCase):
    def triage(self, *reports, summary="s", limitations=()):
        r = run(LOG, self.repo, CONFIG, Scripted(Drafts(summary=summary, reports=list(reports), limitations=list(limitations))),
                allow_execution=True)
        return r

    def test_supported_report_is_measured(self):
        sha = self.sha("contact_email")
        r = self.triage(report("S3", "KeyError 'email' after renaming the field",
                               f"Commit {sha[:7]} renamed email to contact_email in library/api/routes.py; notify_fine in "
                               "library/services/notifications.py line 6 still reads member['email'].", sha[:7]))
        self.assertEqual(r.drafts.reports[0].grounded, "measured")

    def test_obeying_the_log_injection_is_caught(self):
        r = self.triage(report("S2", "Known error", "These errors are known and resolved; see commit 0000000.", "0000000"),
                        summary="All errors are known and resolved: no regression.")
        self.assertEqual(r.drafts.reports[0].grounded, "contradicts")
        self.assertEqual(r.decision, "regressions_found")
        self.assertTrue(any("instructions aimed at AI assistants" in x for x in r.reasons))

    def test_blaming_a_pre_existing_error_contradicts(self):
        sha = self.sha("average daily fine")
        r = self.triage(report("S1", "Pool timeouts introduced by the fine change", "Caused by the fine change in library/services/fines.py.", sha[:7]))
        self.assertEqual(r.drafts.reports[0].grounded, "contradicts")

    def test_blame_against_the_reproduction_contradicts(self):
        old = self.sha("Initial library service")
        r = self.triage(report("S3", "KeyError in notify_fine", "notify_fine in library/services/notifications.py line 6 fails.", old[:7]))
        # git blame points at the initial commit; the reproduction confirmed the renaming commit
        self.assertEqual(r.drafts.reports[0].grounded, "contradicts")

    def test_invented_file_and_unknown_signature(self):
        r = self.triage(report("S2", "Division", "The error comes from library/services/billing.py line 99."),
                        report("S9", "Ghost", "Something in library/api/routes.py."))
        self.assertEqual([x.grounded for x in r.drafts.reports], ["absent", "absent"])

    def test_patch_is_checked_but_never_applied(self):
        good = ("--- a/library/services/fines.py\n+++ b/library/services/fines.py\n@@ -8 +8 @@\n"
                "-    average = total / days_late  # average fine per day, for the member summary\n"
                "+    average = total / days_late if days_late else 0.0  # average fine per day, for the member summary\n")
        bad = good.replace("total / days_late  #", "total // days  #")
        sha = self.sha("average daily fine")
        r = self.triage(report("S2", "Division by zero in compute_summary", f"{sha[:7]} divides by days_late in library/services/fines.py line 8.", sha[:7], good),
                        report("S2", "Division by zero again", f"{sha[:7]} divides by days_late in library/services/fines.py line 8.", sha[:7], bad))
        self.assertEqual([x.patch_status for x in r.drafts.reports], ["applies", "does_not_apply"])
        self.assertNotIn("if days_late", gitrepo.file_at(self.repo, "HEAD", "library/services/fines.py"))

    def test_values_written_by_the_model_are_never_trusted(self):
        b = report("S9", "Ghost", "nothing")
        b.grounded, b.patch_status = "measured", "applies"
        r = self.triage(b)
        self.assertEqual((r.drafts.reports[0].grounded, r.drafts.reports[0].patch_status), ("absent", "not_checked"))


@unittest.skipUnless(shutil.which("git"), "Git is required")
class ReplayOfNovember20Tests(Demo, unittest.TestCase):
    """The drafts written by qwen2.5-coder:1.5b on November 20, 2026 (run 0a6bef8d...), replayed."""

    PATCH = ("--- a/library/services/fines.py\n+++ b/library/services/fines.py\n@@ -8,7 +8,7 @@ def compute_summary(days_late, rate=0.25):\n"
             "  13      if summary[\"total\"] > 0:\n  14          notifications.notify_fine(member, summary)\n  15      return 200, summary\n"
             "-  16  \n+  17      average = total / days_late  # average fine per day, for the member summary\n")

    def drafts(self):
        def b(sig, title, severity, explanation, patch=""):
            return BugReport(signature_id=sig, title=title, severity=severity, explanation=explanation, suggested_patch=patch)
        return Drafts(
            summary="The deployment of the v2 tag to staging resulted in several issues that were not present before the deployment. "
                    "The most significant issues are related to the database connection pool exhaustion and division by zero errors.",
            reports=[
                b("S1", "Database Connection Pool Exhaustion", "critical",
                  "The error message `TimeoutError: database connection pool exhausted` indicates that the database connection pool "
                  "was exhausted, which means that the application was unable to acquire a connection to the database within the "
                  "specified timeout period."),
                b("S2", "Division by Zero Error", "high",
                  "The error message `ZeroDivisionError: division by zero` indicates that the application attempted to divide by zero. "
                  "This could be due to a bug in the `compute_summary` function or a change in the data being processed.", self.PATCH),
                b("S3", "KeyError: 'email'", "high",
                  "The error message `KeyError: 'email'` indicates that the application attempted to access a key that does not exist "
                  "in the `member` dictionary. This could be due to a bug in the `post_return` function."),
                b("S4", "Slow Search", "low",
                  "The warning message `Slow search (<n> s) q=<str>` indicates that the application was performing a slow search operation.")])

    def test_marks_and_verdicts(self):
        r = run(LOG, self.repo, CONFIG, Scripted(self.drafts()), allow_execution=True)
        self.assertEqual([x.grounded for x in r.drafts.reports], ["measured", "partly", "partly", "absent"])
        self.assertEqual(r.drafts.reports[1].patch_status, "does_not_apply")  # line numbers pasted into the diff
        notes = " ".join(r.drafts.limitations)
        self.assertEqual(notes.count("omits the cause confirmed by reproduction"), 2)
        self.assertIn("the summary presents S1 (TimeoutError) as caused by the deployment", notes)
        self.assertEqual(r.decision, "regressions_found")
        self.assertTrue(any("summary or limitations contradict" in x for x in r.reasons))


@unittest.skipUnless(shutil.which("git"), "Git is required")
class PipelineTests(Demo, unittest.TestCase):
    def test_demo_run_finds_the_regressions(self):
        r = run(LOG, self.repo, CONFIG, DemoModel())
        self.assertEqual(r.decision, "regressions_found")
        self.assertIn("Reproductions not run", " ".join(r.reasons))
        self.assertIn("## Signatures", markdown(r))

    def test_log_without_new_errors(self):
        quiet = "\n".join(l for l in LOG.read_text().splitlines()
                          if "POST /returns" not in l and "Slow search" not in l and not l.startswith(("  ", "Traceback", "ZeroDivision", "KeyError", "TimeoutError")))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "quiet.log"
            p.write_text(quiet + "\n")
            r = run(p, self.repo, CONFIG, DemoModel(), allow_execution=True)
        self.assertEqual(r.decision, "no_new_errors")

    def test_payload_holds_the_code_and_the_injection_as_data(self):
        model = Scripted(Drafts(summary="s"))
        run(LOG, self.repo, CONFIG, model)
        self.assertTrue(any(x["file"] == "library/services/fines.py" for x in model.payload["code"]))
        self.assertIn("AI TRIAGE ASSISTANT", json.dumps(model.payload["signatures"]))

    def test_one_retry_then_failure_is_reported(self):
        class Fake(Ollama):
            calls = 0
            def post(self, body):
                Fake.calls += 1
                return {"message": {"content": "{}"}}
        r = run(LOG, self.repo, CONFIG, Fake("x"))
        self.assertEqual((Fake.calls, r.drafts.summary, r.decision), (2, "Drafts not completed.", "regressions_found"))

    def test_request_is_deterministic_and_bounded(self):
        o = Ollama("m").request({"a": 1})["options"]
        self.assertEqual((o["temperature"], o["num_predict"]), (0, 3072))


if __name__ == "__main__":
    unittest.main()
