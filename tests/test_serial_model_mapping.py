import unittest

from services.model_mapping import extract_model, normalize_model


class SerialModelMappingTests(unittest.TestCase):
    def setUp(self):
        self.model_map = {
            "A": "MODELO_A",
            "B": "MODELO_B",
            "C": "MODELO_C",
        }

    def test_model_mapping_is_not_forced_to_a(self):
        self.assertEqual(normalize_model("A", self.model_map), "MODELO_A")
        self.assertEqual(normalize_model("b", self.model_map), "MODELO_B")
        self.assertEqual(normalize_model(" C ", self.model_map), "MODELO_C")
        self.assertIsNone(normalize_model("D", self.model_map))

    def test_model_is_extracted_from_handshake(self):
        self.assertEqual(
            extract_model("SYNC_OK|MODEL: C"),
            "C",
        )


if __name__ == "__main__":
    unittest.main()
