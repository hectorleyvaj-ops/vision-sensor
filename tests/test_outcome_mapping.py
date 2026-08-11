import unittest

from core.outcome import controller_result_for_pipeline


class OutcomeMappingTests(unittest.TestCase):
    def test_product_decisions_and_execution_failures_are_distinct(self):
        self.assertEqual(controller_result_for_pipeline("PASS"), "OK")
        self.assertEqual(controller_result_for_pipeline("FAIL"), "NG")
        self.assertEqual(controller_result_for_pipeline("ERROR"), "ERROR")
        self.assertEqual(controller_result_for_pipeline("TIMEOUT"), "ERROR")
        self.assertEqual(controller_result_for_pipeline("unknown"), "ERROR")


if __name__ == "__main__":
    unittest.main()
