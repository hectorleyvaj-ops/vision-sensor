import unittest
from contextlib import redirect_stderr
from io import StringIO

from scripts.controller_protocol_smoke import main


class ControllerSmokeCliTests(unittest.TestCase):
    def test_ok_requires_explicit_pass_output_permission(self):
        with redirect_stderr(StringIO()):
            exit_code = main(["--port", "TEST", "--result", "OK"])
        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
