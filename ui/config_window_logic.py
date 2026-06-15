import os
from utils.qt_compat import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QInputDialog, QTimer, Signal, Qt, QScrollArea
)
from ui.pyside6.ui_config_window import Ui_Form
from ui.tool_editor import ToolEditor
from ui.schemas.schemas import TOOL_SCHEMAS
from ui.focus_config_dialog import FocusConfigDialog
import shutil

class ConfigWindow(QWidget):
    update_rois = Signal()
    focus_calibration_requested = Signal(object)
    def __init__(self, recipe_manager, get_frame_callback, state_manager, platform, camera_worker=None):
        super().__init__()

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.apply_config_style()
        self.apply_button_feedbakcs()

        self.recipe_manager = recipe_manager
        self.get_frame = get_frame_callback
        self.state_manager = state_manager
        self.platform = platform
        self.camera_worker = camera_worker

        self.current_recipe = None

        self.connect_signals()
        self.load_recipes()

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
        ]

        for btn in buttons:
            self.add_button_feedback(btn)

    def get_screen_size(self):
        screen = self.screen()

        if screen is None:
            return (480, 320)
        
        geo = screen.availableGeometry()
        return geo.width(), geo.height()

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

    def open_focus_config(self):
        # REQUIERE TENER UNA RECETA ACTIVA PARA CONFIGURAR EL ENFOQUE
        if not self.current_recipe:
            print("[CONFIG] No hay receta seleccionada para cofigurar enfoque")
            return
        
        dialog = FocusConfigDialog(
            recipe=self.current_recipe,
            get_frame_callback=self.get_frame,
            platform=self.platform,
            parent=self
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

        screen_size = self.get_screen_size()
        sw, sh = screen_size

        if self.platform == "linux":
            dialog.setMinimumSize(sw, sh)
            dialog.showFullScreen()
        else:
            dialog.resize(800, 600)

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

    def load_recipes(self):
        self.ui.cmb_recipes.clear()

        recipes = self.recipe_manager.get_all()

        selected_index = 0

        for i, r in enumerate(recipes):
            self.ui.cmb_recipes.addItem(r["name"])

            if r.get("selected"):
                selected_index = i

        self.ui.cmb_recipes.setCurrentIndex(selected_index)

    def on_recipe_selected(self, item):
        name = self.ui.cmb_recipes.itemText(item)
        print(name)

        self.current_recipe = self.recipe_manager.get(name)
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
        sw, sh =  screen_size

        if self.platform == "linux": 
            dialog.setMinimumSize(sw, sh)
        else:
            dialog.setMinimumSize(700,520)

        dialog.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dialog)

        editor = ToolEditor(
            tool_name=tool_name,
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=True,
            platform=self.platform,
            screen_size=screen_size
        )

        editor.set_values(params)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(editor)

        btn_save = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")

        btn_save.setCursor(Qt.PointingHandCursor)
        btn_cancel.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_save)

        layout.addWidget(scroll)
        layout.addLayout(buttons_layout)

        def save():
            new_params = editor.get_values()

            self.current_recipe["steps"][selected]["params"] = new_params

            self.recipe_manager.save(self.current_recipe)

            dialog.accept()

        btn_save.clicked.connect(save)
        btn_cancel.clicked.connect(dialog.reject)

        if self.platform == "linux":
            dialog.showFullScreen()
        else:
            dialog.resize(700, 520)

        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def add_step(self):
        self.ensure_steps()  # ASEGURA QUE EXISTE LA CLAVE "steps" Y ES UNA LISTA

        tools = []
        # OBETENER LAS HERRAMIENTAS DISPONIBLES PARA AGREGAR
        for key in TOOL_SCHEMAS:
            tools.append(key)

        # VENTANA Y WIDGETS
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregando nuevo Step")

        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout()

        cmb_tools = QComboBox()
        cmb_tools.addItems(tools)
        

        def create_path():
            tool_name = cmb_tools.currentText()
            step_index = len(self.current_recipe["steps"])
            base_path = self.build_base_path(tool_name, step_index)

            return tool_name, base_path

        tool_name, base_path = create_path()

        screen_size = self.get_screen_size()
        sw, sh =  screen_size

        if self.platform == "linux": 
            dialog.setMinimumSize(sw, sh)
        else:
            dialog.setMinimumSize(700,520)

        editor = ToolEditor(
            tool_name=tool_name,
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=False,
            platform=self.platform,
            screen_size=screen_size
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(layout)

        btn_cancel = QPushButton("Cancelar")
        btn_save = QPushButton("Guardar")

        btn_save.setCursor(Qt.PointingHandCursor)
        btn_cancel.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_save)

        layout.addWidget(cmb_tools)
        layout.addWidget(scroll)
        layout.addLayout(buttons_layout)

        dialog.setLayout(layout)

        def save():
            new_params = editor.get_values()
            new_step = {
                "tool": cmb_tools.currentText(),
                "params": new_params
            }
            self.current_recipe["steps"].append(new_step)
            self.recipe_manager.save(self.current_recipe)

            self.load_tools()  # RECARGA LA LISTA DE HERRAMIENTAS PARA MOSTRAR LA NUEVA AGREGADA
            # ACEPTA EL EVENTO DEL DIALOG Y CIERRA LA VENTANA PARA REGRESAR A CONFIGURACION
            dialog.accept()

        btn_save.clicked.connect(save)
        btn_cancel.clicked.connect(dialog.reject)

        def reload_ui():
            tool_name, base_path = create_path()
            editor.reload(tool_name, base_path)

        cmb_tools.currentTextChanged.connect(reload_ui)

        # MUESTRA LA NUEVA VENTANA DE EDICION DE FORMA BLOQUEANTE
        if self.platform == "linux":
            dialog.showFullScreen()
        else:
            dialog.resize(700, 520)

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
            self.ui.cmb_tools.addItem(tool_name)

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

        self.recipe_manager.create_recipe(name, False)
        self.load_recipes()

        # SELECCIONAR AUTOMATICAMENTE LA NUEVA RECETA EN EL COMBOBOX
        index = self.ui.cmb_recipes.findText(name)
        if index >= 0:
            self.ui.cmb_recipes.setCurrentIndex(index)

    def delete_recipe(self):
        name = self.ui.cmb_recipes.currentText()

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

        self.recipe_manager.delete(name)
        self.current_recipe = None

        self.load_recipes()
        self.ui.cmb_tools.clear()  # LIMPIA LA LISTA DE HERRAMIENTAS AL ELIMINAR LA RECETA

        if self.state_manager and self.state_manager.active_recipe_name == name:
            self.state_manager.set_active_recipe(None)

    def save_changes(self):
        if self.current_recipe:
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
