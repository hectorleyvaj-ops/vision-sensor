import copy
import os
from utils.qt_compat import (
    QT_LIB, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QInputDialog, QTimer, Signal, Qt, QScrollArea, QMessageBox
)
from core.editor_models import EditorValueError
from utils.ui_logger import get_ui_logger
if QT_LIB == "PySide6":
    from ui.pyside6.ui_config_window import Ui_Form
else:
    from ui.pyqt5.config_window import Ui_Form
from ui.tool_editor import ToolEditor
from ui.schemas.schemas import tool_schemas
from ui.focus_config_dialog import FocusConfigDialog
from ui.recipe_policy_dialogs import RecipeSettingsDialog, StepPolicyEditor
from ui.system_config_dialog import SystemConfigDialog
from ui.responsive import (
    apply_config_window_layout,
    compact_stylesheet,
    configure_dialog,
    profile_from_widget,
)
import shutil

class ConfigWindow(QWidget):
    update_rois = Signal()
    focus_calibration_requested = Signal(object)
    restart_required = Signal(object)

    def __init__(
        self,
        recipe_manager,
        get_frame_callback,
        state_manager,
        platform,
        camera_worker=None,
        system_config=None,
        tool_registry=None,
        available_tools=None,
        display_profile=None,
    ):
        super().__init__()

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.display_profile = display_profile or profile_from_widget(self)
        self._build_universal_controls()
        apply_config_window_layout(self, self.ui, self.display_profile)
        
        self.apply_config_style()
        self.setStyleSheet(
            self.styleSheet() + compact_stylesheet(self.display_profile)
        )
        self.apply_button_feedbakcs()

        self.recipe_manager = recipe_manager
        self.get_frame = get_frame_callback
        self.state_manager = state_manager
        self.platform = platform
        self.camera_worker = camera_worker
        self.system_config = system_config
        self.tool_registry = tool_registry
        self.tool_schemas = tool_schemas(tool_registry)
        self.tool_labels = {
            tool_id: tool_registry.tool_class(tool_id).display_name()
            for tool_id in tool_registry or []
        }
        self.available_tools = set(
            tool_registry.keys() if tool_registry is not None else available_tools or []
        )

        self.current_recipe = None
        self.loading_recipes = False

        self.connect_signals()
        self.load_recipes()

    def _build_universal_controls(self):
        self.btn_installation_config = QPushButton("SISTEMA")
        self.btn_recipe_config = QPushButton("RECETA")
        self.ui.bttm_layout.setSpacing(6)
        self.ui.bttm_layout.insertWidget(1, self.btn_installation_config)
        self.ui.bttm_layout.insertWidget(2, self.btn_recipe_config)
        max_width = 92 if self.display_profile.compact else 105
        for button in (
            self.btn_installation_config,
            self.btn_recipe_config,
            self.ui.btn_save,
            self.ui.btn_out,
        ):
            button.setMaximumWidth(max_width)

    def apply_config_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(11, 19, 43);
                color: rgb(234, 234, 234);
                font-size: 14px;
            }

            QDialog {
                background-color: rgb(11, 19, 43);
                color: rgb(234, 234, 234);
            }

            QLabel {
                color: rgb(234, 234, 234);
                background-color: transparent;
            }

            QPushButton {
                color: rgb(234, 234, 234);
                border-radius: 10px;
                border: 2px solid rgb(91, 192, 190);
                background-color: rgb(15, 27, 61);
                min-height: 28px;
                padding: 4px 12px;
            }

            QPushButton:hover {
                background-color: rgb(20, 38, 82);
                border-color: rgb(46, 196, 182);
            }

            QPushButton:pressed {
                background-color: rgb(46, 196, 182);
                color: rgb(11, 19, 43);
            }

            QComboBox,
            QLineEdit,
            QDoubleSpinBox,
            QSpinBox {
                color: rgb(234, 234, 234);
                border-radius: 4px;
                border: 2px solid rgb(91, 192, 190);
                background-color: rgb(15, 27, 61);
                min-height: 28px;
                padding-left: 6px;
                padding-right: 26px;
                selection-background-color: rgb(46, 196, 182);
                selection-color: rgb(11, 19, 43);
            }

            QComboBox:hover,
            QLineEdit:hover,
            QDoubleSpinBox:hover,
            QSpinBox:hover {
                border-color: rgb(46, 196, 182);
            }

            QDoubleSpinBox::up-button,
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid rgb(91, 192, 190);
                border-bottom: 1px solid rgb(91, 192, 190);
                background-color: rgb(20, 38, 82);
            }

            QDoubleSpinBox::down-button,
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 22px;
                border-left: 1px solid rgb(91, 192, 190);
                background-color: rgb(20, 38, 82);
            }

            QDoubleSpinBox::up-button:hover,
            QDoubleSpinBox::down-button:hover,
            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover {
                background-color: rgb(46, 196, 182);
            }

            QCheckBox {
                color: rgb(234, 234, 234);
                background-color: transparent;
                min-height: 24px;
                spacing: 8px;
            }

            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 2px solid rgb(91, 192, 190);
                background-color: rgb(15, 27, 61);
            }

            QCheckBox::indicator:hover {
                border-color: rgb(46, 196, 182);
            }

            QCheckBox::indicator:checked {
                background-color: rgb(46, 196, 182);
                border-color: rgb(46, 196, 182);
            }

            QFrame#line {
                background-color: rgb(15, 27, 61);
            }

            QInputDialog {
                background-color: rgb(11, 19, 43);
                color: rgb(234, 234, 234);
            }

            QInputDialog QLabel {
                color: rgb(234, 234, 234);
            }

            QScrollArea {
                border: none;
                background-color: rgb(11, 19, 43);
            }

            QScrollArea QWidget {
                background-color: rgb(11, 19, 43);
            }
        """)

    def add_button_feedback(self, button):
        base_style = button.styleSheet().strip()
        
        feedback_style = """
        QPushButton:hover {
            background-color: rgb(20 ,38 ,82);
            border-color: rgb(46, 196, 182);
        }
        QPushButton:pressed {
            background-color: rgb(46, 196, 182);
            color: rgb(11, 19, 43);
        }
        """

        if base_style:
            if "{" in base_style and "}" in base_style:
                final_style = base_style + "\n" + feedback_style
            else:
                final_style = f"""
                QPushButton {{
                    {base_style}
                }}
                {feedback_style}
                """
        else:
            final_style = """
            QPushButton {
                color: rgb(234, 234, 234);
                border-radius: 10px;
                border: 2px solid rgb(91, 192, 190);
                background-color: rgb(15, 27, 61);
                min-height: 28px;
                padding: 4px 12px;
            }

            QPushButton:hover {
                background-color: rgb(20, 38, 82);
                border-color: rgb(46, 196, 182);
            }

            QPushButton:pressed {
                background-color: rgb(46, 196, 182);
                color: rgb(11, 19, 43);
            }
            """

        button.setStyleSheet(final_style)
        button.setCursor(Qt.PointingHandCursor)

    def apply_button_feedbakcs(self):
        buttons = [
            self.ui.btn_add_r,
            self.ui.btn_del_r,
            self.ui.btn_select_r,
            self.ui.btn_add_t,
            self.ui.btn_del_t,
            self.ui.btn_edit_t,
            self.ui.btn_out,
            self.ui.btn_save,
            self.ui.btn_focus_config,
            self.btn_installation_config,
            self.btn_recipe_config,
        ]

        for btn in buttons:
            self.add_button_feedback(btn)

    def apply_scrollbar_style(self, scroll):
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgb(11, 19, 43);
            }

            QScrollBar:vertical {
                background-color: rgb(15, 27, 61);
                width: 22px;
                margin: 0px;
                border-radius: 8px;
            }

            QScrollBar::handle:vertical {
                background-color: rgb(91, 192, 190);
                min-height: 36px;
                border-radius: 8px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: rgb(46, 196, 182);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QScrollBar:horizontal {
                background-color: rgb(15, 27, 61);
                height: 18px;
                margin: 0px;
                border-radius: 8px;
            }

            QScrollBar::handle:horizontal {
                background-color: rgb(91, 192, 190);
                min-width: 36px;
                border-radius: 8px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: rgb(46, 196, 182);
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
                border: none;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)

    def get_screen_size(self):
        return self.display_profile.width, self.display_profile.height

    def safe_name(self, name):
        return name.replace(" ","_").replace("/","_").replace("\\","_")
    
    def ensure_steps(self):
        if "steps" not in self.current_recipe or not isinstance(self.current_recipe["steps"], list):
            self.current_recipe["steps"] = []

    def build_base_path(self, tool_name, step_index):
        name = self.safe_name(self.current_recipe["name"])
        return f"master_img/{name}/{tool_name}_{step_index+1}/"

    def connect_signals(self):
        self.ui.cmb_recipes.currentIndexChanged.connect(self.on_recipe_selected)
        self.ui.btn_edit_t.clicked.connect(self.edit_tool)
        self.ui.btn_add_t.clicked.connect(self.add_step)
        self.ui.btn_del_t.clicked.connect(self.delete_tool)
        self.ui.btn_save.clicked.connect(self.save_changes)
        self.ui.btn_add_r.clicked.connect(self.add_recipe)
        self.ui.btn_del_r.clicked.connect(self.delete_recipe)
        self.ui.btn_select_r.clicked.connect(self.select_recipe)
        self.ui.btn_out.clicked.connect(self.close)
        self.ui.btn_focus_config.clicked.connect(self.open_focus_config)
        self.btn_installation_config.clicked.connect(self.open_system_config)
        self.btn_recipe_config.clicked.connect(self.open_recipe_settings)

    def open_system_config(self):
        if self.system_config is None:
            QMessageBox.critical(
                self,
                "Configuracion no disponible",
                "No se recibio la configuracion activa de la instalacion.",
            )
            return

        dialog = SystemConfigDialog(
            system_config=self.system_config,
            recipe_manager=self.recipe_manager,
            platform=self.platform,
            parent=self,
            display_profile=self.display_profile,
        )
        dialog.configuration_saved.connect(self.restart_required.emit)
        configure_dialog(
            dialog,
            self.display_profile,
            requested=(800, 600),
            fullscreen=self.platform == "linux",
        )
        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def open_recipe_settings(self):
        if not self.current_recipe:
            QMessageBox.information(
                self,
                "Sin receta",
                "Selecciona una receta antes de editar sus propiedades.",
            )
            return

        dialog = RecipeSettingsDialog(
            recipe=self.current_recipe,
            recipe_manager=self.recipe_manager,
            available_tools=self.available_tools,
            parent=self,
            display_profile=self.display_profile,
        )
        dialog.recipe_saved.connect(self.on_recipe_settings_saved)
        configure_dialog(
            dialog,
            self.display_profile,
            requested=(520, 320),
            fullscreen=self.platform == "linux",
        )
        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def on_recipe_settings_saved(self, recipe):
        name = recipe.get("name")
        self.load_recipes(name)
        if name and self.state_manager:
            self.state_manager.set_active_recipe(name)
        self.update_rois.emit()

    def open_focus_config(self):
        # REQUIERE TENER UNA RECETA ACTIVA PARA CONFIGURAR EL ENFOQUE
        if not self.current_recipe:
            print("[CONFIG] No hay receta seleccionada para cofigurar enfoque")
            return
        
        dialog = FocusConfigDialog(
            recipe=self.current_recipe,
            get_frame_callback=self.get_frame,
            platform=self.platform,
            parent=self,
            display_profile=self.display_profile,
        )

        if self.camera_worker is not None:
            print("[CONFIG] Conectando señales de calibración con CameraWorker")
            dialog.calibration_requested.connect(self.foward_focus_calibration_request)
            self.camera_worker.manual_focus_finished.connect(dialog.on_calibration_finished)
            self.camera_worker.manual_focus_failed.connect(dialog.on_calibration_failed)
        else:
            print("[CONFIG][ERROR] camera_worker es None. No se podrá calibrar enfoque.")
            dialog.lbl_status.setText("Error: CameraWorker no está disponible.")
            dialog.btn_calibrate.setEnabled(False)

        configure_dialog(
            dialog,
            self.display_profile,
            requested=(800, 600),
            fullscreen=self.platform == "linux",
        )

        if hasattr(dialog, "exec"):
            result = dialog.exec()
        else:
            result = dialog.exec_()

        if result:
            self.recipe_manager.save(self.current_recipe)

            focus = self.current_recipe.get("focus", {})

            if self.camera_worker is not None:
                self.camera_worker.set_focus_from_recipe(focus)

            print(f"[CONFIG] Focus guardado en receta: {focus}")
            self.update_rois.emit()

        if self.camera_worker is not None:
            try:
                dialog.calibration_requested.disconnect(self.foward_focus_calibration_request)
                self.camera_worker.manual_focus_finished.disconnect(dialog.on_calibration_finished)
                self.camera_worker.manual_focus_failed.disconnect(dialog.on_calibration_failed)
            except Exception:
                pass

    def foward_focus_calibration_request(self, focus_config):
        print(f"[CONFIG] Redirigiendo solicitud de calibración a MainWindow: {focus_config}")
        self.focus_calibration_requested.emit(focus_config)

    def load_recipes(self, preferred_name=None):
        self.loading_recipes = False

        try:
            self.ui.cmb_recipes.blockSignals(True)
            self.ui.cmb_recipes.clear()

            recipes = self.recipe_manager.get_all()

            if not recipes:
                self.current_recipe = None
                self.ui.cmb_tools.clear()
                return
            
            selected_index = 0

            for i, r in enumerate(recipes):
                name = r.get("name", "")

                if not name:
                    continue

                self.ui.cmb_recipes.addItem(name)

                if preferred_name and name == preferred_name:
                    selected_index = i

                elif not preferred_name and r.get("selected"):
                    selected_index = i

            if self.ui.cmb_recipes.count() == 0:
                self.current_recipe = None
                self.ui.cmb_tools.clear()
                return
            
            selected_index = max(0, min(selected_index, self.ui.cmb_recipes.count() - 1))
            self.ui.cmb_recipes.setCurrentIndex(selected_index)

        finally:
            self.ui.cmb_recipes.blockSignals(False)
            self.loading_recipes = False

        # Cargar manualmente la receta seleccionada una sola vez, ya sin señales intermedias.
        self.on_recipe_selected(self.ui.cmb_recipes.currentIndex())

    def on_recipe_selected(self, item):
        if self.loading_recipes:
            return

        if item < 0:
            self.current_recipe = None
            self.ui.cmb_tools.clear()
            return

        name = self.ui.cmb_recipes.itemText(item).strip()

        if not name:
            self.current_recipe = None
            self.ui.cmb_tools.clear()
            return

        print(name)

        recipe = self.recipe_manager.get(name)

        if not recipe:
            print(f"[CONFIG][WARNING] Receta no encontrada al seleccionar: {name}")
            self.current_recipe = None
            self.ui.cmb_tools.clear()
            return

        self.current_recipe = recipe

        print(f"Current Recipe: {self.current_recipe.get('name', 'UNKNOWN')}")

        self.load_tools()
    
    def edit_tool(self):
        selected = self.ui.cmb_tools.currentIndex()
        print(f"Index selected: {selected}")

        if selected < 0:
            return
        
        self.ensure_steps()
        step = self.current_recipe["steps"][selected]

        tool_name = step["tool"]
        params = step["params"]

        base_path = self.build_base_path(tool_name, selected)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Editar {tool_name}")

        screen_size = self.get_screen_size()

        dialog.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dialog)

        editor = ToolEditor(
            tool_name=tool_name,
            tool_schema=self.tool_schemas.get(tool_name, {}),
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=True,
            platform=self.platform,
            screen_size=screen_size
        )

        editor_values = dict(params)
        editor.set_values(editor_values)

        previous_step_ids = [
            candidate.get("id")
            for candidate in self.current_recipe["steps"][:selected]
            if candidate.get("id")
        ]
        policy_editor = StepPolicyEditor(
            step=step,
            available_step_ids=previous_step_ids,
            display_profile=self.display_profile,
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(editor)
        self.apply_scrollbar_style(scroll)

        btn_save = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")

        btn_save.setCursor(Qt.PointingHandCursor)
        btn_cancel.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_save)

        layout.addWidget(policy_editor)
        layout.addWidget(scroll)
        layout.addLayout(buttons_layout)

        def save():
            try:
                policy = policy_editor.get_values()
            except EditorValueError as exc:
                QMessageBox.critical(dialog, "Step invalido", str(exc))
                return
            new_params = editor.get_values()

            # Mantiene parametros existentes que no aparezcan todavía en schemas.py.
            # Esto evita perder configuraciones nuevas o futuras al editar desde la UI.
            current_params = self.current_recipe["steps"][selected].get("params", {})
            if not isinstance(current_params, dict):
                current_params = {}

            merged_params = dict(current_params)
            merged_params.update(new_params)

            candidate = copy.deepcopy(self.current_recipe)
            candidate["steps"][selected]["params"] = merged_params
            candidate["steps"][selected].update(policy)

            try:
                self.recipe_manager.save(candidate)
            except ValueError as exc:
                QMessageBox.critical(dialog, "Step invalido", str(exc))
                return

            self.current_recipe.clear()
            self.current_recipe.update(candidate)
            self.load_tools()
            dialog.accept()

        btn_save.clicked.connect(save)
        btn_cancel.clicked.connect(dialog.reject)

        configure_dialog(
            dialog,
            self.display_profile,
            requested=(700, 520),
            fullscreen=self.platform == "linux",
        )

        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def add_step(self):
        self.ensure_steps()  # ASEGURA QUE EXISTE LA CLAVE "steps" Y ES UNA LISTA

        tools = sorted(self.tool_schemas)
        if not tools:
            QMessageBox.critical(
                self,
                "Sin herramientas",
                "El catalogo no contiene herramientas editables.",
            )
            return

        # VENTANA Y WIDGETS
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregando nuevo Step")

        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout()

        cmb_tools = QComboBox()
        for available_tool in tools:
            cmb_tools.addItem(
                self.tool_labels.get(available_tool, available_tool),
                available_tool,
            )

        def selected_tool_id():
            return str(cmb_tools.currentData() or cmb_tools.currentText())
        

        def create_path():
            tool_name = selected_tool_id()
            step_index = len(self.current_recipe["steps"])
            base_path = self.build_base_path(tool_name, step_index)

            return tool_name, base_path

        tool_name, base_path = create_path()

        screen_size = self.get_screen_size()

        editor = ToolEditor(
            tool_name=tool_name,
            tool_schema=self.tool_schemas.get(tool_name, {}),
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=False,
            platform=self.platform,
            screen_size=screen_size
        )
        default_id = self.recipe_manager.slugify(tool_name) or "step"
        default_id = f"{default_id}_{len(self.current_recipe['steps']) + 1}"
        policy_editor = StepPolicyEditor(
            step={
                "id": default_id,
                "enabled": True,
                "required": True,
                "condition": {"type": "always"},
            },
            available_step_ids=[
                step.get("id")
                for step in self.current_recipe["steps"]
                if step.get("id")
            ],
            display_profile=self.display_profile,
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(editor)
        self.apply_scrollbar_style(scroll)

        btn_cancel = QPushButton("Cancelar")
        btn_save = QPushButton("Guardar")

        btn_save.setCursor(Qt.PointingHandCursor)
        btn_cancel.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_save)

        layout.addWidget(cmb_tools)
        layout.addWidget(policy_editor)
        layout.addWidget(scroll)
        layout.addLayout(buttons_layout)

        dialog.setLayout(layout)

        def save():
            try:
                policy = policy_editor.get_values()
            except EditorValueError as exc:
                QMessageBox.critical(dialog, "Step invalido", str(exc))
                return
            new_params = editor.get_values()
            new_step = {
                "tool": selected_tool_id(),
                "params": new_params
            }
            new_step.update(policy)
            self.current_recipe["steps"].append(new_step)
            try:
                self.recipe_manager.save(self.current_recipe)
            except ValueError as exc:
                self.current_recipe["steps"].pop()
                QMessageBox.critical(dialog, "Step invalido", str(exc))
                return

            self.load_tools()  # RECARGA LA LISTA DE HERRAMIENTAS PARA MOSTRAR LA NUEVA AGREGADA
            # ACEPTA EL EVENTO DEL DIALOG Y CIERRA LA VENTANA PARA REGRESAR A CONFIGURACION
            dialog.accept()

        btn_save.clicked.connect(save)
        btn_cancel.clicked.connect(dialog.reject)

        def reload_ui(_index=None):
            tool_name, base_path = create_path()
            editor.reload(
                tool_name,
                self.tool_schemas.get(tool_name, {}),
                base_path,
            )

        cmb_tools.currentIndexChanged.connect(reload_ui)

        # MUESTRA LA NUEVA VENTANA DE EDICION DE FORMA BLOQUEANTE
        configure_dialog(
            dialog,
            self.display_profile,
            requested=(700, 520),
            fullscreen=self.platform == "linux",
        )

        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def delete_tool(self):
        self.ensure_steps()
        selected = self.ui.cmb_tools.currentIndex()

        if selected < 0:
            return
        
        step = self.current_recipe["steps"][selected]
        tool_name = step["tool"]

        path = self.build_base_path(tool_name, selected)
        
        del self.current_recipe["steps"][selected]

        # ELIMINAR LA CARPETA DE IMAGENES ASOCIADA A LA HERRAMIENTA ELIMINADA
        if os.path.exists(path):
            shutil.rmtree(path)

        self.recipe_manager.save(self.current_recipe)

        self.load_tools()
          

    def load_tools(self):
        self.ui.cmb_tools.clear()

        if not self.current_recipe:
            return
        
        if not isinstance(self.current_recipe, dict):
            print("Receta no es un diccionario")
            return
        
        self.ensure_steps()
        steps = self.current_recipe.get("steps", [])
        if not steps:
            print("Receta no tiene pasos definidos")
            return

        for step in steps:
            tool_name = step.get("tool", "unknown")
            tool_label = self.tool_labels.get(tool_name, tool_name)
            step_id = step.get("id", "sin_id")
            flags = []
            if not step.get("enabled", True):
                flags.append("OFF")
            if not step.get("required", True):
                flags.append("OPCIONAL")
            suffix = f" [{' / '.join(flags)}]" if flags else ""
            self.ui.cmb_tools.addItem(f"{step_id} - {tool_label}{suffix}")

    def add_recipe(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Nueva Receta")
        dialog.setLabelText("Nombre:")
        dialog.setStyleSheet(self.styleSheet())

        if self.platform == "linux":
            dialog.resize(300, 160)
        else:
            dialog.resize(360, 180)

        if hasattr(dialog, "exec"):
            ok = dialog.exec()
        else:
            ok = dialog.exec_()

        if not ok:
            return
        
        name = dialog.textValue().strip()

        if not name:
            return

        # EVITAR DUPLICADOS
        if self.recipe_manager.get(name):
            print("Receta existente, elige otro nombre")
            return

        self.recipe_manager.create_recipe(name)
        self.load_recipes()

        # SELECCIONAR AUTOMATICAMENTE LA NUEVA RECETA EN EL COMBOBOX
        index = self.ui.cmb_recipes.findText(name)
        if index >= 0:
            self.ui.cmb_recipes.setCurrentIndex(index)

    def delete_recipe(self):
        name = self.ui.cmb_recipes.currentText().strip()

        if not name:
            return

        recipe = self.recipe_manager.get(name)

        if not recipe:
            print("Receta no encontrada")
            return

        # ELIMINAR CARPETA DE IMAGENES ASOCIADA A LA RECETA
        safe = self.safe_name(name)
        path = f"master_img/{safe}/"

        if os.path.exists(path):
            shutil.rmtree(path)

        was_active = False
        if self.state_manager and getattr(self.state_manager, "active_recipe_name", None) == name:
            was_active = True

        self.recipe_manager.delete(name)

        recipes = self.recipe_manager.get_all()

        if not recipes:
            self.current_recipe = None
            self.ui.cmb_recipes.clear()
            self.ui.cmb_tools.clear()

            if self.state_manager:
                self.state_manager.set_active_recipe(None)

            print("[CONFIG] No quedan recetas disponibles")
            return

        # Seleccionar la primera receta restante.
        fallback_name = recipes[0].get("name")

        if fallback_name:
            self.recipe_manager.set_selected(fallback_name)

        self.load_recipes(preferred_name=fallback_name)

        if was_active and self.state_manager and fallback_name:
            self.state_manager.set_active_recipe(fallback_name)

        self.update_rois.emit()

        print(f"[CONFIG] Receta eliminada: {name}. Receta actual: {fallback_name}")

    def save_changes(self):
        if not self.current_recipe:
            print("[CONFIG][WARNING] No hay receta actual para guardar")
            return

        self.recipe_manager.save(self.current_recipe)

        if self.state_manager:
            self.state_manager.set_active_recipe(self.current_recipe["name"])

        self.update_rois.emit()

        print("Cambios guardados, receta seleccionada:", self.current_recipe["name"])
        
    def select_recipe(self):
        name = self.ui.cmb_recipes.currentText()

        if not name:
            return
        
        self.recipe_manager.set_selected(name)
        
        if self.state_manager:
            self.state_manager.set_active_recipe(name)

        print(f"Receta seleccionada: {name}")

    def closeEvent(self, event):
        event.accept()
