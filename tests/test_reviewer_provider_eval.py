import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reviewer_provider_eval.py"
SPEC = importlib.util.spec_from_file_location("reviewer_provider_eval", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)

class ReviewerProviderEvalTest(unittest.TestCase):
    def _decision(self, verdict, rationale):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        p = pathlib.Path(td.name) / "decision.json"
        p.write_text(json.dumps({"verdict": verdict, "confidence": 0.9, "rationale": rationale}), encoding="utf-8")
        return p

    def test_corpus_shas_are_exact_and_distinct(self):
        self.assertEqual(set(mod.CASES), {"H1", "H2", "H3", "H4"})
        shas = [c.sha for c in mod.CASES.values()]
        self.assertEqual(len(shas), len(set(shas)))
        self.assertTrue(all(len(x) == 40 for x in shas))

    def test_h1_requires_blocking_and_causal_signature(self):
        p = self._decision("CHANGES_REQUIRED", "Collection success is incorrectly tied to merge eligibility, so a valid UNPROVEN observation exits as failure.")
        self.assertEqual(mod.score("H1", p)["status"], "DETECTED")
        p = self._decision("READY_FOR_HUMAN", "Collection success is incorrectly tied to eligibility.")
        self.assertEqual(mod.score("H1", p)["status"], "MISSED")

    def test_h2_detects_broken_status_assignment(self):
        p = self._decision("CHANGES_REQUIRED", "The success-path status assignment is swallowed by literal comment text, leaving status undefined before exit.")
        self.assertEqual(mod.score("H2", p)["status"], "DETECTED")

    def test_h3_detects_redirect_credential_boundary(self):
        p = self._decision("CHANGES_REQUIRED", "The default urllib redirect behavior can replay the Authorization bearer token to a redirect target.")
        self.assertEqual(mod.score("H3", p)["status"], "DETECTED")

    def test_negative_control_rejects_repaired_defect_claims(self):
        p = self._decision("READY_FOR_HUMAN", "No concrete blocker is visible in the bounded collector evidence.")
        self.assertEqual(mod.score("H4", p)["status"], "CLEAN_CONTROL")
        p = self._decision("CHANGES_REQUIRED", "Authorization token is still replayed across redirects.")
        self.assertEqual(mod.score("H4", p)["status"], "FALSE_POSITIVE")

    def test_summary_never_claims_migration_authority(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        paths=[]
        for case,status in (("H1","DETECTED"),("H2","DETECTED"),("H3","DETECTED"),("H4","CLEAN_CONTROL")):
            p=pathlib.Path(td.name)/f"{case}.json"
            p.write_text(json.dumps({"case":case,"status":status}),encoding="utf-8"); paths.append(p)
        s=mod.summarize(paths)
        self.assertEqual(s["result"], "QUALIFIED_FOR_REPEAT")
        self.assertFalse(s["model_output_invalid"])
        self.assertIn("does not authorize provider migration", s["note"])

    def test_provider_failure_is_not_qualification(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        rows=[
            {"case":"H1","status":"PROVIDER_FAILURE"},
            {"case":"H2","status":"DETECTED"},
            {"case":"H3","status":"DETECTED"},
            {"case":"H4","status":"CLEAN_CONTROL"},
        ]
        paths=[]
        for i,row in enumerate(rows):
            p=pathlib.Path(td.name)/f"{i}.json"; p.write_text(json.dumps(row),encoding="utf-8"); paths.append(p)
        s=mod.summarize(paths)
        self.assertEqual(s["result"], "NOT_QUALIFIED")
        self.assertTrue(s["provider_failure"])
        self.assertFalse(s["model_output_invalid"])

    def test_invalid_model_output_is_distinct_and_fail_closed(self):
        row = mod.model_output_invalid("H1", "reviewer output rejected: rationale must contain 20-800 characters")
        self.assertEqual(row["status"], "MODEL_OUTPUT_INVALID")
        self.assertNotEqual(row["status"], "PROVIDER_FAILURE")
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        rows=[
            row,
            {"case":"H2","status":"DETECTED"},
            {"case":"H3","status":"DETECTED"},
            {"case":"H4","status":"CLEAN_CONTROL"},
        ]
        paths=[]
        for i,item in enumerate(rows):
            p=pathlib.Path(td.name)/f"{i}.json"; p.write_text(json.dumps(item),encoding="utf-8"); paths.append(p)
        s=mod.summarize(paths)
        self.assertEqual(s["result"], "NOT_QUALIFIED")
        self.assertFalse(s["provider_failure"])
        self.assertTrue(s["model_output_invalid"])
        self.assertEqual(s["invalid_model_output_cases"], ["H1"])

if __name__ == "__main__":
    unittest.main()
