import copy

from core.editor_models import (
    EditorValueError,
    format_condition,
    parse_condition_text,
)
from utils.qt_compat import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    Signal,
)
from ui.responsive import compact_stylesheet, profile_from_widget


class StepPolicyEditor(QWidget):
    """Edit engine-owned step policy separately from tool parameters."""

    def __init__(
        self,
        step=None,
        available_step_ids=None,
        parent=None,
        display_profile=None,
    ):
        super().__init__(parent)
        self.display_profile = display_profile or profile_from_widget(parent or self)
        self.available_step_ids = list(available_step_ids or [])
        form = QFormLayout(self)
        form.setContentsMargins(8, 8, 8, 8)
        self.txt_step_id = QLineEdit()
        self.chk_enabled = QCheckBox()
        self.chk_required = QCheckBox()
        self.txt_condition = QPlainTextEdit()
        condition_height = 60 if self.display_profile.compact else 95
        self.txt_condition.setMinimumHeight(condition_height)
        self.txt_condition.setPlaceholderText(
            '{"type": "always"} o una condicion del esquema v2'
        )
        form.addRow("ID unico del step", self.txt_step_id)
        form.addRow("Habilitado", self.chk_enabled)
        form.addRow("Requerido", self.chk_required)
        form.addRow("Condicion (JSON)", self.txt_condition)
        self.set_step(step or {})

    def set_step(self, step):
        self.txt_step_id.setText(str(step.get("id", "")))
        self.chk_enabled.setChecked(bool(step.get("enabled", True)))
        self.chk_required.setChecked(bool(step.get("required", True)))
        self.txt_condition.setPlainText(
            format_condition(step.get("condition"))
        )

    def get_values(self):
        step_id = self.txt_step_id.text().strip()
        if not step_id:
            raise EditorValueError("El ID del step es obligatorio")
        condition = parse_condition_text(
            self.txt_condition.toPlainText(),
            available_step_ids=self.available_step_ids,
        )
        return {
            "id": step_id,
            "enabled": self.chk_enabled.isChecked(),
            "required": self.chk_required.isChecked(),
            "condition": condition,
        }


class RecipeSettingsDialog(QDialog):
    recipe_saved = Signal(object)

    def __init__(
        self,
        recipe,
        recipe_manager,
        available_tools,
        parent=None,
        display_profile=None,
    ):
        super().__init__(parent)
        self.recipe = recipe
        self.recipe_manager = recipe_manager
        self.available_tools = list(available_tools or [])
        self.display_profile = display_profile or profile_from_widget(parent or self)
        self.setWindowTitle("Configuracion de receta")
        if parent is not None:
            self.setStyleSheet(
                parent.styleSheet() + compact_stylesheet(self.display_profile)
            )
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.lbl_name = QLabel()
        self.txt_recipe_id = QLineEdit()
        self.chk_commissioned = QCheckBox(
            "Permitir produccion cuando toda la validacion sea correcta"
        )
        self.lbl_summary = QLabel()
        self.lbl_summary.setWordWrap(True)
        form.addRow("Nombre", self.lbl_name)
        form.addRow("ID interno", self.txt_recipe_id)
        form.addRow("Comisionada", self.chk_commissioned)
        form.addRow("Estado", self.lbl_summary)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        cancel = QPushButton("CANCELAR")
        save = QPushButton("VALIDAR Y GUARDAR")
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)

    def _load_values(self):
        self.lbl_name.setText(str(self.recipe.get("name", "")))
        self.txt_recipe_id.setText(str(self.recipe.get("id", "")))
        self.chk_commissioned.setChecked(
            bool(self.recipe.get("commissioned", False))
        )
        steps = self.recipe.get("steps", [])
        enabled = sum(1 for step in steps if step.get("enabled", True))
        focus_mode = self.recipe.get("focus", {}).get("mode", "calibrated")
        self.lbl_summary.setText(
            f"{enabled}/{len(steps)} steps habilitados | enfoque: {focus_mode}"
        )

    def _save(self):
        candidate = copy.deepcopy(self.recipe)
        candidate["id"] = self.txt_recipe_id.text().strip()
        candidate["commissioned"] = self.chk_commissioned.isChecked()

        if candidate["commissioned"]:
            error = self.recipe_manager.get_commissioning_error(
                candidate,
                available_tools=self.available_tools,
            )
            if error:
                QMessageBox.critical(
                    self,
                    "Receta no comisionable",
                    error,
                )
                return

        try:
            self.recipe_manager.save(candidate)
        except ValueError as exc:
            QMessageBox.critical(self, "Receta invalida", str(exc))
            return

        self.recipe.clear()
        self.recipe.update(candidate)
        self.recipe_saved.emit(candidate)
        self.accept()
