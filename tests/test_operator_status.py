import unittest

from core.operator_status import build_operator_status


class OperatorStatusTests(unittest.TestCase):
    def test_critical_state_has_priority_over_latched_ok(self):
        view = build_operator_status(
            "CRITICAL",
            "Serial desconectado",
            final_result="OK",
            recipe_name="MODELO_A",
        )
        self.assertEqual(view.level, "critical")
        self.assertEqual(view.headline, "ATENCIÓN REQUERIDA")
        self.assertIn("Serial", view.detail)

    def test_warning_explains_why_system_is_not_ready(self):
        view = build_operator_status(
            "WARNING",
            "Enfoque pendiente",
            recipe_name="MODELO_B",
        )
        self.assertEqual(view.level, "warning")
        self.assertEqual(view.detail, "Enfoque pendiente")

    def test_busy_cycle_precedes_previous_result(self):
        view = build_operator_status(
            "READY",
            final_result="NG",
            cycle_busy=True,
        )
        self.assertEqual(view.level, "working")
        self.assertEqual(view.headline, "INSPECCIONANDO")

    def test_ready_result_is_shown_in_words(self):
        ok_view = build_operator_status("READY", final_result="OK")
        ng_view = build_operator_status("READY", final_result="NG")
        self.assertEqual(ok_view.headline, "RESULTADO OK")
        self.assertEqual(ng_view.headline, "RESULTADO NG")

    def test_ready_idle_state_and_recipe_fallback_are_explicit(self):
        view = build_operator_status("READY")
        self.assertEqual(view.level, "ready")
        self.assertEqual(view.recipe_caption, "SIN RECETA")
        self.assertIn("Esperando", view.detail)


if __name__ == "__main__":
    unittest.main()
