import re
import unittest
from pathlib import Path


class FirmwarePhase9ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.firmware = (root / "ESP32" / "FSM" / "FSM.ino").read_text(
            encoding="utf-8"
        )
        cls.config = (
            root / "ESP32" / "FSM" / "worksurface_config.h"
        ).read_text(encoding="utf-8")

    def test_firmware_implements_required_protocol_messages(self):
        for token in (
            "HELLO_ACK|PROTO=",
            "PONG|SEQ=",
            "TRIGGER|CYCLE=",
            "VISION_RESULT",
            "FINAL_RESULT|CYCLE=",
            "CANCEL|CYCLE=",
            "RESET|SCOPE=CYCLE",
        ):
            self.assertIn(token, self.firmware)

    def test_pass_output_is_forced_safe_on_reset_and_link_loss(self):
        reset_body = re.search(
            r"void resetCycleState\(\) \{(?P<body>.*?)\n\}",
            self.firmware,
            re.DOTALL,
        ).group("body")
        loss_body = re.search(
            r"void loseLink\([^)]*\) \{(?P<body>.*?)\n\}",
            self.firmware,
            re.DOTALL,
        ).group("body")
        self.assertIn("setPassOutput(false)", reset_body)
        self.assertIn("setPassOutput(false)", loss_body)

    def test_worksurface_model_and_sensor_mapping_is_explicit(self):
        self.assertIn('MODEL_BITS_10[] = "A"', self.config)
        self.assertIn('MODEL_BITS_01[] = "B"', self.config)
        self.assertIn('{"A", true, false}', self.config)
        self.assertIn('{"B", false, true}', self.config)
        self.assertIn('{"C", true, true}', self.config)

    def test_only_final_ok_can_enable_plc_pass(self):
        self.assertIn('setPassOutput(finalResult == "OK")', self.firmware)
        self.assertNotIn('sendSerial("TRIGGER")', self.firmware)
        self.assertNotIn('message == "OK"', self.firmware)

    def test_missing_final_ack_eventually_forces_safe_cancel(self):
        self.assertIn("MAX_FINAL_RETRIES = 10", self.config)
        self.assertIn("FINAL_ACK_TIMEOUT", self.firmware)
        timeout_position = self.firmware.index("FINAL_ACK_TIMEOUT")
        safe_position = self.firmware.rfind(
            "setPassOutput(false)", 0, timeout_position
        )
        self.assertGreater(safe_position, 0)

    def test_zero_model_bits_are_rejected_instead_of_reusing_old_model(self):
        self.assertIn('sendError("INVALID_MODEL_BITS"', self.firmware)
        self.assertIsNotNone(
            re.search(
                r'String readModel\(\).*?return "";',
                self.firmware,
                re.DOTALL,
            )
        )


if __name__ == "__main__":
    unittest.main()
