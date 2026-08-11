import threading
import time
import unittest

from core.execution_control import wait_interruptibly
from tools.result import ToolCancelled


class ExecutionCancellationTests(unittest.TestCase):
    def test_cancel_interrupts_wait_without_waiting_full_delay(self):
        cancel_event = threading.Event()
        outcome = []

        def wait_in_worker():
            try:
                wait_interruptibly(3.0, cancel_event=cancel_event)
            except ToolCancelled:
                outcome.append("cancelled")

        worker = threading.Thread(target=wait_in_worker)
        started = time.monotonic()
        worker.start()
        time.sleep(0.03)
        cancel_event.set()
        worker.join(timeout=0.5)

        self.assertFalse(worker.is_alive())
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(outcome, ["cancelled"])


if __name__ == "__main__":
    unittest.main()
