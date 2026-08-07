import unittest

from services.model_mapping import normalize_model


class SerialModelMappingTests(unittest.TestCase):
    def setUp(self):
        self.model_map = {
            "LINE-01": "RECIPE_RED",
            "SKU-8472": "RECIPE_BLUE",
        }

    def test_external_model_ids_map_to_recipe_names(self):
        self.assertEqual(
            normalize_model("line-01", self.model_map),
            "RECIPE_RED",
        )
        self.assertEqual(
            normalize_model(" SKU-8472 ", self.model_map),
            "RECIPE_BLUE",
        )
        self.assertIsNone(normalize_model("UNKNOWN", self.model_map))

    def test_empty_map_does_not_impose_a_naming_convention(self):
        self.assertEqual(normalize_model("sku-8472", {}), "SKU-8472")


if __name__ == "__main__":
    unittest.main()
