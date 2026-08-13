import json
import tempfile
import unittest
from pathlib import Path

from core.traceability import CycleTraceWriter
from tools.result import ToolResult, ToolStatus


class TraceabilityTests(unittest.TestCase):
    def test_cycle_record_contains_identity_timing_steps_and_delivery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = CycleTraceWriter(
                directory=temp_dir,
                installation_id="station-01",
            )
            record = writer.record_cycle(
                context={
                    "cycle_id": "cycle-abc",
                    "model": "SKU-42",
                },
                recipe_name="RECIPE_42",
                final_result="NG",
                pipeline_result={
                    "status": "FAIL",
                    "results": {
                        "dmtx_1": ToolResult(
                            status=ToolStatus.FAIL,
                            tool_name="dmtx",
                            error="Codigo incorrecto",
                            error_code="DMTX_MISMATCH",
                        )
                    },
                    "execution_order": ["dmtx_1"],
                    "skipped_steps": [],
                    "step_durations_ms": {"dmtx_1": 12.5},
                },
                communication={"status": "OK"},
                reason="Codigo incorrecto",
            )

            saved = json.loads(
                (Path(temp_dir) / "cycles.jsonl").read_text(encoding="utf-8")
            )
            self.assertEqual(saved, record)
            self.assertEqual(saved["installation_id"], "station-01")
            self.assertEqual(saved["cycle_id"], "cycle-abc")
            self.assertEqual(saved["external_model"], "SKU-42")
            self.assertEqual(saved["recipe"], "RECIPE_42")
            self.assertEqual(saved["steps"][0]["status"], "FAIL")
            self.assertEqual(saved["steps"][0]["duration_ms"], 12.5)
            self.assertEqual(saved["communication"]["status"], "OK")

    def test_rotation_bounds_number_of_cycle_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = CycleTraceWriter(
                directory=temp_dir,
                retention_files=2,
                max_file_size_bytes=1,
            )
            for index in range(5):
                writer.record_cycle(
                    context={"cycle_id": f"c-{index}"},
                    recipe_name="R",
                    final_result="OK",
                )

            files = sorted(Path(temp_dir).glob("cycles*.jsonl"))
            self.assertLessEqual(len(files), 2)
            self.assertTrue((Path(temp_dir) / "cycles.jsonl").exists())

    def test_disabled_writer_creates_no_cycle_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = CycleTraceWriter(directory=temp_dir, enabled=False)
            result = writer.record_cycle(
                context={"cycle_id": "ignored"},
                recipe_name="R",
                final_result="OK",
            )
            self.assertIsNone(result)
            self.assertFalse((Path(temp_dir) / "cycles.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
