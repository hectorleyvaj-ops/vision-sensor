import unittest

from services.controller_protocol import (
    PROTOCOL_VERSION,
    CycleGuard,
    decode_message,
    encode_message,
)
from tests.simulators.controller_simulator import ControllerSimulator


class ControllerContractTests(unittest.TestCase):
    def setUp(self):
        self.controller = ControllerSimulator()
        self.guard = CycleGuard()
        hello = self.controller.receive(
            encode_message(
                "HELLO",
                proto=PROTOCOL_VERSION,
                role="VISION_ENGINE",
            )
        )
        self.assertEqual(decode_message(hello[0]).kind, "HELLO_ACK")
        self.controller.receive(encode_message("READY", state=1))

    def test_vision_result_is_bound_to_cycle(self):
        trigger = decode_message(self.controller.trigger("SKU-8472"))
        event = self.guard.begin(
            trigger.fields["CYCLE"],
            trigger.fields["MODEL"],
        )
        ack = decode_message(
            self.controller.receive(
                encode_message(
                    "VISION_RESULT",
                    cycle=event["cycle_id"],
                    result="OK",
                )
            )[0]
        )

        self.assertEqual(ack.fields["STATUS"], "OK")
        self.assertEqual(self.controller.vision_result, "OK")

    def test_cancel_then_late_result_cannot_affect_next_cycle(self):
        first = decode_message(self.controller.trigger("PART-1"))
        first_cycle = first.fields["CYCLE"]
        self.guard.begin(first_cycle, "PART-1")

        cancel = decode_message(self.controller.cancel("QUALITY_RELEASE"))
        self.guard.cancel(cancel.fields["CYCLE"])

        second = decode_message(self.controller.trigger("PART-2"))
        second_cycle = second.fields["CYCLE"]
        self.guard.begin(second_cycle, "PART-2")

        stale_ack = decode_message(
            self.controller.receive(
                encode_message(
                    "VISION_RESULT",
                    cycle=first_cycle,
                    result="OK",
                )
            )[0]
        )

        self.assertEqual(stale_ack.fields["STATUS"], "REJECTED")
        self.assertEqual(stale_ack.fields["ERROR"], "STALE_CYCLE")
        self.assertEqual(self.guard.active_cycle_id, second_cycle)
        self.assertIsNone(self.controller.vision_result)

    def test_final_result_contains_no_machine_specific_fields(self):
        trigger = decode_message(self.controller.trigger("CUSTOM-PART"))
        self.guard.begin(trigger.fields["CYCLE"], trigger.fields["MODEL"])
        final = decode_message(self.controller.final_result("NG"))

        self.assertEqual(
            set(final.fields),
            {"CYCLE", "RESULT"},
        )

    def test_heartbeat_echoes_sequence(self):
        pong = decode_message(
            self.controller.receive(encode_message("PING", seq="42"))[0]
        )
        self.assertEqual(pong.kind, "PONG")
        self.assertEqual(pong.fields["SEQ"], "42")

    def test_identical_vision_result_retry_is_idempotent(self):
        trigger = decode_message(self.controller.trigger("PART-1"))
        first = decode_message(
            self.controller.receive(
                encode_message(
                    "VISION_RESULT",
                    cycle=trigger.fields["CYCLE"],
                    result="OK",
                )
            )[0]
        )
        retry = decode_message(
            self.controller.receive(
                encode_message(
                    "VISION_RESULT",
                    cycle=trigger.fields["CYCLE"],
                    result="OK",
                )
            )[0]
        )
        self.assertEqual(first.fields["STATUS"], "OK")
        self.assertEqual(retry.fields["STATUS"], "OK")
        self.assertEqual(self.controller.vision_result, "OK")

    def test_conflicting_vision_result_retry_is_rejected(self):
        trigger = decode_message(self.controller.trigger("PART-1"))
        self.controller.receive(
            encode_message(
                "VISION_RESULT",
                cycle=trigger.fields["CYCLE"],
                result="OK",
            )
        )
        conflict = decode_message(
            self.controller.receive(
                encode_message(
                    "VISION_RESULT",
                    cycle=trigger.fields["CYCLE"],
                    result="NG",
                )
            )[0]
        )
        self.assertEqual(conflict.fields["STATUS"], "REJECTED")
        self.assertEqual(conflict.fields["ERROR"], "CONFLICTING_RESULT")


if __name__ == "__main__":
    unittest.main()
