import unittest
from pathlib import Path
from xml.etree import ElementTree


class FinalUiContractTests(unittest.TestCase):
    def test_canonical_main_window_is_installation_neutral(self):
        root = ElementTree.parse("ui/main_window.ui").getroot()
        texts = {
            (node.text or "").strip()
            for node in root.iter("string")
            if (node.text or "").strip()
        }
        self.assertIn("SISTEMA DE VISIÓN", texts)
        self.assertIn("RECETA ACTIVA", texts)
        self.assertIn("CONFIGURAR ESTACIÓN", texts)
        self.assertNotIn("SISTEMA DE VISIÓN - SUMMIT USB", texts)
        self.assertFalse(any("MODELO DE PIEZA: A" in text for text in texts))

    def test_both_generated_backends_match_canonical_operator_copy(self):
        for filename in (
            "ui/pyqt5/ui_main_window.py",
            "ui/pyside6/ui_main_window.py",
        ):
            text = Path(filename).read_text(encoding="utf-8")
            self.assertNotIn("SUMMIT USB", text, filename)
            self.assertIn("RECETA ACTIVA", text, filename)

    def test_controller_remains_authority_for_production_cycle(self):
        text = Path("app/app.py").read_text(encoding="utf-8")
        self.assertNotIn("btn_trigger.clicked.connect(self.run_fsm)", text)
        self.assertIn("Los ciclos son iniciados por el controlador", text)

    def test_configuration_copy_and_destructive_guards_are_explicit(self):
        text = Path("ui/config_window_logic.py").read_text(encoding="utf-8")
        for label in (
            "CONFIGURACION DEL MOTOR DE VISION",
            "CONFIGURAR ENFOQUE",
            "EN CALIBRACION",
        ):
            self.assertIn(label, text)
        self.assertIn("confirm_action", text)
        self.assertIn("archive_resource_path", text)


if __name__ == "__main__":
    unittest.main()
