import os
from utils.qt_compat import QWidget, QDialog, QVBoxLayout, QPushButton, QComboBox, QInputDialog, QTimer, Signal
from ui.ui_config_window import Ui_Form
from ui.tool_editor import ToolEditor
from ui.schemas.schemas import TOOL_SCHEMAS
import shutil

class ConfigWindow(QWidget):
    update_rois = Signal()
    def __init__(self, recipe_manager, get_frame_callback, state_manager):
        super().__init__()

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.recipe_manager = recipe_manager
        self.get_frame = get_frame_callback
        self.state_manager = state_manager

        self.current_recipe = None

        self.connect_signals()
        self.load_recipes()

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

        layout = QVBoxLayout()

        editor = ToolEditor(
            tool_name=tool_name,
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=True
        )

        editor.set_values(params)

        btn_save = QPushButton("Guardar")

        layout.addWidget(editor)
        layout.addWidget(btn_save)

        dialog.setLayout(layout)

        def save():
            new_params = editor.get_values()

            self.current_recipe["steps"][selected]["params"] = new_params

            self.recipe_manager.save(self.current_recipe)

            dialog.accept()

        btn_save.clicked.connect(save)

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
        layout = QVBoxLayout()

        cmb_tools = QComboBox()
        cmb_tools.addItems(tools)
        btn_save = QPushButton("Guardar")

        def create_path():
            tool_name = cmb_tools.currentText()
            step_index = len(self.current_recipe["steps"])
            base_path = self.build_base_path(tool_name, step_index)

            return tool_name, base_path

        tool_name, base_path = create_path()

        editor = ToolEditor(
            tool_name=tool_name,
            get_frame_callback=self.get_frame,
            base_path=base_path,
            edit=False
        )

        layout.addWidget(cmb_tools)
        layout.addWidget(editor)
        layout.addWidget(btn_save)
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

        def reload_ui():
            tool_name, base_path = create_path()
            editor.reload(tool_name, base_path)

        cmb_tools.currentTextChanged.connect(reload_ui)

        # MUESTRA LA NUEVA VENTANA DE EDICION DE FORMA BLOQUEANTE
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
        name, ok = QInputDialog.getText(self, "Nueva Receta", "Nombre:")

        if not ok or not name.strip():
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

        

    