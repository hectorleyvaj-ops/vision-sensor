import unittest

from tools.dmtx_policy import DataMatrixReadPolicy


class DataMatrixPolicyTests(unittest.TestCase):
    def test_duplicate_symbols_in_one_attempt_count_once(self):
        policy = DataMatrixReadPolicy(
            expected_code="ABC",
            min_expected_reads=2,
        )
        policy.observe(["ABC", "ABC"])
        self.assertIsNone(policy.confirmed_code)
        self.assertEqual(policy.expected_attempt_count, 1)
        policy.observe(["ABC"])
        self.assertEqual(policy.confirmed_code, "ABC")

    def test_exact_and_prefix_are_distinct_policies(self):
        exact = DataMatrixReadPolicy("ABC", match_mode="exact")
        prefix = DataMatrixReadPolicy("ABC", match_mode="prefix")
        exact.observe(["ABC-123"])
        prefix.observe(["ABC-123"])
        self.assertIsNone(exact.confirmed_code)
        self.assertEqual(prefix.confirmed_code, "ABC")

    def test_wrong_reads_are_counted_per_attempt(self):
        policy = DataMatrixReadPolicy("ABC", max_wrong_reads=0)
        policy.observe(["BAD", "BAD"])
        self.assertEqual(policy.wrong_attempt_count, 1)
        self.assertTrue(policy.wrong_limit_exceeded)

    def test_tied_consensus_without_expected_code_does_not_pass(self):
        policy = DataMatrixReadPolicy(None, min_expected_reads=1)
        policy.observe(["ABC", "XYZ"])
        self.assertIsNone(policy.confirmed_code)


if __name__ == "__main__":
    unittest.main()
