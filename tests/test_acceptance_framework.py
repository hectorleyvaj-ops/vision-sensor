import json
import tempfile
import unittest
from pathlib import Path

from core.acceptance import (
    AcceptanceError,
    add_trial,
    evaluate_acceptance,
    import_trace_jsonl,
    load_acceptance_plan,
    new_acceptance_session,
    set_scenario,
)


class AcceptanceFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "commissioning.json").write_text(
            json.dumps(
                {
                    "required_models": [
                        {"external_id": "X", "recipe": "ONE"},
                        {"external_id": "Y", "recipe": "TWO"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.plan_path = self.root / "acceptance.json"
        self.plan_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "installation_id": "test-cell",
                    "installation_manifest": "commissioning.json",
                    "evidence_files": ["commissioning.json"],
                    "criteria": {
                        "minimum_trials_per_model": {"OK": 2, "NG": 2},
                        "max_false_accepts": 0,
                        "max_false_reject_rate": 0.25,
                        "max_execution_errors": 0,
                        "max_p95_cycle_ms": 500,
                        "require_safe_output_for_non_ok": True,
                    },
                    "required_scenarios": [
                        {"id": "power_loss", "description": "Falla de energia segura"},
                        {"id": "mapping", "description": "Mapeo fisico correcto"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.plan = load_acceptance_plan(self.plan_path)

    def tearDown(self):
        self.temporary.cleanup()

    def _ready_session(self):
        session = new_acceptance_session(self.plan)
        cycle = 0
        for model in self.plan.models:
            for expected in ("OK", "NG"):
                for _ in range(2):
                    cycle += 1
                    add_trial(
                        session,
                        self.plan,
                        model=model,
                        expected_result=expected,
                        observed_result=expected,
                        duration_ms=100 + cycle,
                        cycle_id=f"cycle-{cycle}",
                        output_safe=True,
                    )
        for scenario_id in self.plan.scenarios:
            set_scenario(session, self.plan, scenario_id, "PASS")
        return session

    def test_plan_derives_models_from_installation_manifest(self):
        self.assertEqual(self.plan.models, ("X", "Y"))
        self.assertEqual(self.plan.trial_classes, ("OK", "NG"))

    def test_empty_session_is_pending_and_does_not_approve(self):
        report = evaluate_acceptance(new_acceptance_session(self.plan), self.plan)
        self.assertEqual(report["status"], "PENDING")
        self.assertTrue(report["pending"])

    def test_complete_population_and_scenarios_are_ready(self):
        report = evaluate_acceptance(self._ready_session(), self.plan)
        self.assertEqual(report["status"], "READY_FOR_COMMISSIONING")
        self.assertEqual(report["metrics"]["trials_total"], 8)

    def test_false_accept_is_a_failure(self):
        session = self._ready_session()
        session["trials"][2]["observed_result"] = "OK"
        report = evaluate_acceptance(session, self.plan)
        self.assertEqual(report["status"], "FAILED")
        self.assertIn("FALSE_ACCEPT", {item["code"] for item in report["failures"]})

    def test_false_reject_rate_is_a_failure(self):
        session = self._ready_session()
        session["trials"][0]["observed_result"] = "NG"
        session["trials"][4]["observed_result"] = "NG"
        report = evaluate_acceptance(session, self.plan)
        self.assertEqual(report["status"], "FAILED")
        self.assertIn(
            "FALSE_REJECT_RATE",
            {item["code"] for item in report["failures"]},
        )

    def test_error_unsafe_output_and_slow_cycle_fail(self):
        session = self._ready_session()
        session["trials"][0]["observed_result"] = "ERROR"
        session["trials"][0]["output_safe"] = False
        session["trials"][0]["duration_ms"] = 900
        report = evaluate_acceptance(session, self.plan)
        codes = {item["code"] for item in report["failures"]}
        self.assertTrue({"EXECUTION_ERROR", "UNSAFE_OUTPUT", "CYCLE_P95"} <= codes)

    def test_failed_required_scenario_fails_session(self):
        session = self._ready_session()
        set_scenario(session, self.plan, "power_loss", "FAIL")
        report = evaluate_acceptance(session, self.plan)
        self.assertEqual(report["status"], "FAILED")

    def test_trace_import_filters_model_skips_bad_and_deduplicates(self):
        trace_path = self.root / "cycles.jsonl"
        records = [
            {
                "record_type": "vision_cycle",
                "cycle_id": "one",
                "external_model": "X",
                "final_result": "OK",
                "duration_ms": 123,
            },
            {
                "record_type": "vision_cycle",
                "cycle_id": "two",
                "external_model": "Y",
                "final_result": "OK",
                "duration_ms": 125,
            },
            {
                "record_type": "vision_cycle",
                "cycle_id": "bad-duration",
                "external_model": "X",
                "final_result": "OK",
                "duration_ms": None,
            },
        ]
        trace_path.write_text(
            "\n".join(json.dumps(record) for record in records) + "\n",
            encoding="utf-8",
        )
        session = new_acceptance_session(self.plan)
        first = import_trace_jsonl(
            session,
            self.plan,
            trace_path,
            expected_result="OK",
            model="X",
            output_safe=True,
        )
        second = import_trace_jsonl(
            session,
            self.plan,
            trace_path,
            expected_result="OK",
            model="X",
            output_safe=True,
        )
        self.assertEqual(first, {"imported": 1, "skipped": 2})
        self.assertEqual(second, {"imported": 0, "skipped": 3})

    def test_manually_corrupted_session_is_rejected(self):
        session = new_acceptance_session(self.plan)
        session["trials"].append(
            {
                "model": "UNDECLARED",
                "expected_result": "OK",
                "observed_result": "OK",
                "duration_ms": 10,
            }
        )
        with self.assertRaises(AcceptanceError):
            evaluate_acceptance(session, self.plan)

    def test_plan_requires_ok_and_ng_populations(self):
        value = json.loads(self.plan_path.read_text(encoding="utf-8"))
        value["criteria"]["minimum_trials_per_model"] = {"OK": 2}
        self.plan_path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(AcceptanceError):
            load_acceptance_plan(self.plan_path)

    def test_configuration_change_invalidates_existing_session(self):
        session = new_acceptance_session(self.plan)
        manifest_path = self.root / "commissioning.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["revision"] = 2
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        changed_plan = load_acceptance_plan(self.plan_path)

        with self.assertRaises(AcceptanceError):
            evaluate_acceptance(session, changed_plan)


if __name__ == "__main__":
    unittest.main()
