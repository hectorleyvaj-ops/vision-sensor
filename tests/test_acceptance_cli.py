import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.acceptance_session import main


class AcceptanceCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "commissioning.json").write_text(
            json.dumps({"required_models": [{"external_id": "A"}]}),
            encoding="utf-8",
        )
        self.plan = self.root / "acceptance.json"
        self.plan.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "installation_id": "cli-test",
                    "installation_manifest": "commissioning.json",
                    "evidence_files": ["commissioning.json"],
                    "criteria": {
                        "minimum_trials_per_model": {"OK": 1, "NG": 1},
                        "max_false_accepts": 0,
                        "max_false_reject_rate": 0,
                        "max_execution_errors": 0,
                        "max_p95_cycle_ms": 1000,
                    },
                    "required_scenarios": [
                        {"id": "safe", "description": "Salida segura"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.session = self.root / "session.json"

    def tearDown(self):
        self.temporary.cleanup()

    def _run(self, *arguments):
        output = StringIO()
        errors = StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(["--plan", str(self.plan), *arguments])
        return code, output.getvalue(), errors.getvalue()

    def test_cli_lifecycle_stays_pending_until_evidence_is_complete(self):
        code, _, _ = self._run("init", "--session", str(self.session))
        self.assertEqual(code, 0)
        code, output, _ = self._run("evaluate", "--session", str(self.session))
        self.assertEqual(code, 3)
        self.assertIn("PENDING", output)

        for expected in ("OK", "NG"):
            code, _, _ = self._run(
                "record-trial",
                "--session",
                str(self.session),
                "--model",
                "A",
                "--expected",
                expected,
                "--observed",
                expected,
                "--duration-ms",
                "100",
                "--cycle-id",
                expected.lower(),
            )
            self.assertEqual(code, 0)
        code, _, _ = self._run(
            "record-scenario",
            "--session",
            str(self.session),
            "--id",
            "safe",
            "--status",
            "PASS",
        )
        self.assertEqual(code, 0)
        report_path = self.root / "report.json"
        code, output, _ = self._run(
            "evaluate",
            "--session",
            str(self.session),
            "--json-out",
            str(report_path),
        )
        self.assertEqual(code, 0)
        self.assertIn("READY_FOR_COMMISSIONING", output)
        self.assertEqual(
            json.loads(report_path.read_text(encoding="utf-8"))["status"],
            "READY_FOR_COMMISSIONING",
        )

    def test_init_refuses_to_replace_existing_session(self):
        self.assertEqual(
            self._run("init", "--session", str(self.session))[0],
            0,
        )
        code, _, errors = self._run("init", "--session", str(self.session))
        self.assertEqual(code, 2)
        self.assertIn("--force", errors)


if __name__ == "__main__":
    unittest.main()
