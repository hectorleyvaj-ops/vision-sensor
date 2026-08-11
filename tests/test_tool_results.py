import threading
import time
import unittest

from processing.pipeline import VisionPipeline
from tools.result import ToolResult, ToolStatus


def recipe(required=True):
    return {
        "steps": [{
            "id": "fake_1",
            "tool": "fake",
            "enabled": True,
            "required": required,
            "condition": {"type": "always"},
            "params": {},
        }]
    }


class ResultTool:
    def __init__(self, status):
        self.status = status
        self.calls = 0

    def run(self, **kwargs):
        self.calls += 1
        return ToolResult(
            status=self.status,
            tool_name="fake",
            error=None if self.status == ToolStatus.PASS else "diagnostico",
            error_code="FAKE_CODE",
        )


class ToolResultTests(unittest.TestCase):
    def test_legacy_false_result_migrates_to_fail(self):
        self.assertEqual(
            ToolResult(success=False, tool_name="legacy").status,
            ToolStatus.FAIL,
        )

    def test_required_status_is_preserved_by_pipeline(self):
        for status in (
            ToolStatus.PASS,
            ToolStatus.FAIL,
            ToolStatus.ERROR,
            ToolStatus.TIMEOUT,
        ):
            with self.subTest(status=status):
                response = VisionPipeline({"fake": ResultTool(status)}).run(
                    recipe(),
                    {},
                )
                self.assertEqual(response["status"], status.value)
                self.assertEqual(response["success"], status is ToolStatus.PASS)

    def test_optional_failure_does_not_reject_recipe(self):
        response = VisionPipeline({
            "fake": ResultTool(ToolStatus.FAIL),
        }).run(recipe(required=False), {})
        self.assertEqual(response["status"], "PASS")

    def test_pre_cancelled_pipeline_does_not_call_tool(self):
        cancel_event = threading.Event()
        cancel_event.set()
        tool = ResultTool(ToolStatus.PASS)
        response = VisionPipeline({"fake": tool}).run(
            recipe(),
            {"cancel_event": cancel_event},
        )
        self.assertEqual(response["status"], "ERROR")
        self.assertEqual(response["error_code"], "CANCELLED")
        self.assertEqual(tool.calls, 0)

    def test_expired_deadline_is_timeout(self):
        response = VisionPipeline({
            "fake": ResultTool(ToolStatus.PASS),
        }).run(recipe(), {"deadline": time.monotonic() - 1})
        self.assertEqual(response["status"], "TIMEOUT")
        self.assertEqual(response["error_code"], "INSPECTION_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
