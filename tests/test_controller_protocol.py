import unittest

from services.controller_protocol import (
    CycleGuard,
    ProtocolError,
    decode_message,
    encode_message,
)


class ControllerProtocolTests(unittest.TestCase):
    def test_message_round_trip_preserves_reason(self):
        payload = encode_message(
            "ready",
            state=0,
            reason="Camara sin frame | receta pendiente",
        )
        message = decode_message(payload)

        self.assertEqual(message.kind, "READY")
        self.assertEqual(message.fields["STATE"], "0")
        self.assertEqual(
            message.fields["REASON"],
            "Camara sin frame | receta pendiente",
        )

    def test_duplicate_field_is_rejected(self):
        with self.assertRaises(ProtocolError):
            decode_message("TRIGGER|CYCLE=one|CYCLE=two|MODEL=SKU-8472")

    def test_cycle_guard_accepts_opaque_model_ids(self):
        event = CycleGuard().begin("boot1-1", "SKU-8472-REV-C")
        self.assertEqual(event["model"], "SKU-8472-REV-C")

    def test_cycle_guard_rejects_parallel_cycle(self):
        guard = CycleGuard()
        guard.begin("boot1-1", "PART-1")

        with self.assertRaises(ProtocolError):
            guard.begin("boot1-2", "PART-2")

    def test_cycle_guard_rejects_late_result(self):
        guard = CycleGuard()
        guard.begin("boot1-1", "PART-1")
        guard.close("boot1-1")
        guard.begin("boot1-2", "PART-2")

        with self.assertRaises(ProtocolError):
            guard.require_active("boot1-1")

    def test_cancel_closes_active_cycle(self):
        guard = CycleGuard()
        guard.begin("boot1-1", "PART-3")

        self.assertEqual(guard.cancel("boot1-1"), "boot1-1")
        self.assertIsNone(guard.active_cycle_id)
        self.assertEqual(guard.last_closed_cycle_id, "boot1-1")


if __name__ == "__main__":
    unittest.main()
