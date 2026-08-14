import copy
from utils.qt_compat import (
    QT_LIB, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QInputDialog, QTimer, Signal, Qt, QScrollArea, QMessageBox,
    QLabel,
)
from core.editor_models import EditorValueError
from core.resource_archive import archive_resource_path as archive_path
from core.resource_paths import recipe_resource_root
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
from ui.theme import interface_stylesheet

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
        self.ui.lbl_tittle.setText("CONFIGURACION DEL MOTOR DE VISION")
        self.ui.lbl_recipes.setText("RECETAS")
        self.ui.lbl_tools.setText("PASOS DE INSPECCION")
        self.ui.lbl_focus.setText("CAMARA Y ENFOQUE")
        self.ui.btn_add_r.setText("NUEVA")
        self.ui.btn_del_r.setText("BORRAR")
        self.ui.btn_select_r.setText("ACTIVAR")
        self.ui.btn_add_t.setText("AGREGAR PASO")
        self.ui.btn_del_t.setText("BORRAR PASO")
        self.ui.btn_edit_t.setText("EDITAR PASO")
        self.ui.btn_focus_config.setText("CONFIGURAR ENFOQUE")
        self.ui.btn_save.setText("GUARDAR")
        self.ui.btn_out.setText("VOLVER")

        self.lbl_recipe_state = QLabel("Selecciona una receta")
        self.lbl_recipe_state.setObjectName("lbl_recipe_state")
        self.lbl_recipe_state.setProperty("uiRole", "summary")
        self.lbl_recipe_state.setWordWrap(True)
        self.lbl_recipe_state.setAlignment(Qt.AlignCenter)
        self.ui.left_panel.insertWidget(2, self.lbl_recipe_state)

        self.btn_installation_config = QPushButton("ESTACION")
        self.btn_recipe_config = QPushButton("PROPIEDADES")
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

        self.ui.btn_select_r.setProperty("buttonRole", "primary")
        self.ui.btn_save.setProperty("buttonRole", "primary")
        self.ui.btn_del_r.setProperty("buttonRole", "danger")
        self.ui.btn_del_t.setProperty("buttonRole", "danger")
        self.ui.btn_add_r.setToolTip("Crear una receta configurable")
        self.ui.btn_select_r.setToolTip("Usar esta receta en nuevos ciclos")
        self.ui.btn_del_r.setToolTip("Archivar y retirar la receta seleccionada")
        self.ui.btn_del_t.setToolTip("Archivar y retirar el paso seleccionado")

    def apply_config_style(self):
        for widget in (
            self.ui.top_bar,
            self.ui.lbl_tittle,
            self.ui.lbl_recipes,
            self.ui.cmb_recipes,
            self.ui.btn_add_r,
            self.ui.btn_del_r,
            self.ui.btn_select_r,
            self.ui.line,
            self.ui.lbl_tools,
            self.ui.cmb_tools,
            self.ui.btn_add_t,
            self.ui.btn_del_t,
            self.ui.btn_edit_t,
            self.ui.line_2,
            self.ui.lbl_focus,
            self.ui.btn_focus_config,
            self.ui.frame,
            self.ui.list_log_config,
            self.ui.btn_save,
            self.ui.btn_out,
        ):
            widget.setStyleSheet("")
        self.setStyleSheet(
            interface_stylesheet(self.display_profile)
            + compact_stylesheet(self.display_profile)
        )

    def add_button_feedback(self, button):
        button.setStyleSheet("")
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
        scroll.setStyleSheet("")

    def get_screen_size(self):
        return self.display_profile.width, self.display_profile.height

    def safe_name(self, name):
        return name.replace(" ","_").replace("/","_").replace("\\","_")

    def confirm_action(self, title, message):
        buttons = getattr(QMessageBox, "StandardButton", QMessageBox)
        yes = getattr(buttons, "Yes")
        no = getattr(buttons, "No")
        answer = QMessageBox.question(self, title, message, yes | no, no)
        return answer == yes

    def archive_resource_path(self, path):
        target = archive_path(path)
        if target is not None:
            print(f"[CONFIG] Recursos archivados en {target}")
        return target

    def refresh_recipe_summary(self):
        if not isinstance(self.current_recipe, dict):
            self.lbl_recipe_state.setText("SIN RECETA SELECCIONADA")
            return
        steps = self.current_recipe.get("steps", [])
        active_steps = [
            step
            for step in steps
            if isinstance(step, dict) and step.get("enabled", True)
        ]
        selected = "ACTIVA" if self.current_recipe.get("selected") else "INACTIVA"
        commissioned = (
            "COMISIONADA"
            if self.current_recipe.get("commissioned") is True
            else "EN CALIBRACION"
        )
        self.lbl_recipe_state.setText(
            f"{selected}  ·  {len(active_steps)} PASOS  ·  {commissioned}"
        )
    
    def ensure_steps(self):
        if "steps" not in self.current_recipe or not isinstance(self.current_recipe["steps"], list):
            self.current_recipe["steps"] = []

    def build_base_path(self, tool_name, step_index):
        name = self.safe_name(self.current_recipe["name"])
        root = self.recipe_resource_root()
        return str(root / name / f"{self.safe_name(tool_name)}_{step_index + 1}")

    def recipe_resource_root(self):
        return recipe_resource_root(getattr(self.recipe_manager, "path", ""))

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

        camera_runtime = (
            self.camera_worker.runtime_camera_info()
            if self.camera_worker is not None
            and hasattr(self.camera_worker, "runtime_camera_info")
            else {}
        )
        controller_runtime = (
            self.state_manager.comm.runtime_controller_info()
            if self.state_manager is not None
            and getattr(self.state_manager, "comm", None) is not None
            and hasattr(self.state_manager.comm, "runtime_controller_info")
            else {}
        )
        dialog = SystemConfigDialog(
            system_config=self.system_config,
            recipe_manager=self.recipe_manager,
            platform=self.platform,
            parent=self,
            display_profile=self.display_profile,
            camera_runtime=camera_runtime,
            controller_runtime=controller_runtime,
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
        
        camera_runtime = (
            self.camera_worker.runtime_camera_info()
            if self.camera_worker is not None
            and hasattr(self.camera_worker, "runtime_camera_info")
            else {}
        )
        dialog = FocusConfigDialog(
            recipe=self.current_recipe,
            get_frame_callback=self.get_frame,
            platform=self.platform,
            parent=self,
            display_profile=self.display_profile,
            camera_runtime=camera_runtime,
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
                self.refresh_recipe_summary()
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
                self.refresh_recipe_summary()
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
            self.refresh_recipe_summary()
            return

        name = self.ui.cmb_recipes.itemText(item).strip()

        if not name:
            self.current_recipe = None
            self.ui.cmb_tools.clear()
            self.refresh_recipe_summary()
            return

        print(name)

        recipe = self.recipe_manager.get(name)

        if not recipe:
            print(f"[CONFIG][WARNING] Receta no encontrada al seleccionar: {name}")
            self.current_recipe = None
            self.ui.cmb_tools.clear()
            self.refresh_recipe_summary()
            return

        self.current_recipe = recipe
        self.refresh_recipe_summary()

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
        layout.setContentsMargins(
            self.display_profile.margin,
            self.display_profile.margin,
            self.display_profile.margin,
            self.display_profile.margin,
        )
        layout.setSpacing(self.display_profile.spacing)

        editor = ToolEditor(
            tool_name=tool_name,
            tool_schema=self.tool_schemas.get(tool_name, {}),
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=True,
            platform=self.platform,
            screen_size=screen_size,
            display_profile=self.display_profile,
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
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(self.display_profile.spacing)
        scroll_layout.addWidget(policy_editor)
        scroll_layout.addWidget(editor)
        scroll.setWidget(scroll_content)
        self.apply_scrollbar_style(scroll)

        btn_save = QPushButton("GUARDAR CAMBIOS")
        btn_cancel = QPushButton("CANCELAR")
        btn_save.setProperty("buttonRole", "primary")

        btn_save.setCursor(Qt.PointingHandCursor)
        btn_cancel.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_save)

        layout.addWidget(scroll, 1)
        layout.addLayout(buttons_layout)

        def save():
            try:
                policy = policy_editor.get_values()
            except EditorValueError as exc:
                QMessageBox.critical(dialog, "Paso invalido", str(exc))
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
                QMessageBox.critical(dialog, "Paso invalido", str(exc))
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
        dialog.setWindowTitle("Agregar paso de inspeccion")

        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout()
        layout.setContentsMargins(
            self.display_profile.margin,
            self.display_profile.margin,
            self.display_profile.margin,
            self.display_profile.margin,
        )
        layout.setSpacing(self.display_profile.spacing)

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
            screen_size=screen_size,
            display_profile=self.display_profile,
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
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(self.display_profile.spacing)
        scroll_layout.addWidget(cmb_tools)
        scroll_layout.addWidget(policy_editor)
        scroll_layout.addWidget(editor)
        scroll.setWidget(scroll_content)
        self.apply_scrollbar_style(scroll)

        btn_cancel = QPushButton("CANCELAR")
        btn_save = QPushButton("GUARDAR PASO")
        btn_save.setProperty("buttonRole", "primary")

        btn_save.setCursor(Qt.PointingHandCursor)
        btn_cancel.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_save)

        layout.addWidget(scroll, 1)
        layout.addLayout(buttons_layout)

        dialog.setLayout(layout)

        def save():
            try:
                policy = policy_editor.get_values()
            except EditorValueError as exc:
                QMessageBox.critical(dialog, "Paso invalido", str(exc))
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
                QMessageBox.critical(dialog, "Paso invalido", str(exc))
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
        step_name = step.get("id", tool_name)

        if not self.confirm_action(
            "Borrar paso",
            f"Se retirara el paso '{step_name}' de la receta. "
            "Sus recursos se archivaran para recuperacion. ¿Continuar?",
        ):
            return

        path = self.build_base_path(tool_name, selected)

        candidate = copy.deepcopy(self.current_recipe)
        del candidate["steps"][selected]
        self.recipe_manager.save(candidate)
        self.current_recipe.clear()
        self.current_recipe.update(candidate)
        self.archive_resource_path(path)

        self.load_tools()
        self.refresh_recipe_summary()
          

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

        if not self.confirm_action(
            "Borrar receta",
            f"Se retirara la receta '{name}' y sus recursos se archivaran. "
            "Esta accion no puede realizarse durante produccion. ¿Continuar?",
        ):
            return

        safe = self.safe_name(name)
        path = str(self.recipe_resource_root() / safe)

        was_active = False
        if self.state_manager and getattr(self.state_manager, "active_recipe_name", None) == name:
            was_active = True

        self.recipe_manager.delete(name)
        self.archive_resource_path(path)

        recipes = self.recipe_manager.get_all()

        if not recipes:
            self.current_recipe = None
            self.ui.cmb_recipes.clear()
            self.ui.cmb_tools.clear()

            if self.state_manager:
                self.state_manager.set_active_recipe(None)

            print("[CONFIG] No quedan recetas disponibles")
            self.refresh_recipe_summary()
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
        self.refresh_recipe_summary()

        if self.state_manager:
            self.state_manager.set_active_recipe(self.current_recipe["name"])

        self.update_rois.emit()

        print("Cambios guardados, receta seleccionada:", self.current_recipe["name"])
        
    def select_recipe(self):
        name = self.ui.cmb_recipes.currentText()

        if not name:
            return
        
        self.recipe_manager.set_selected(name)
        self.current_recipe = self.recipe_manager.get(name)
        self.refresh_recipe_summary()
        
        if self.state_manager:
            self.state_manager.set_active_recipe(name)

        self.update_rois.emit()
        print(f"Receta seleccionada: {name}")

    def closeEvent(self, event):
        event.accept()
