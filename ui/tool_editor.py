from utils.qt_compat import QWidget, QFormLayout, QLineEdit, QPushButton, QDoubleSpinBox, QComboBox, QCheckBox
from ui.schemas.schemas import TOOL_SCHEMAS
from ui.widgets.img_list_widget import ImageListWidget
from ui.widgets.video_widget import VideoWidget

class ToolEditor(QWidget):
    def __init__(self, tool_name, get_frame_callback, base_path, edit=False, editing_index=None):
        super().__init__()

        self.tool_name = tool_name
        self.get_frame = get_frame_callback
        self.base_path = base_path
        self.edit = edit
        self.editing_index = editing_index

        self.fields = {}

        self.form = QFormLayout()
        self.setLayout(self.form)

        self.build_ui()

    def build_ui(self):
        schema = TOOL_SCHEMAS[self.tool_name]

        # OBTENEMOS EL LABEL Y EL TYPE DEL WIDGET PARA CADA PARAMETRO SEGUN EL ESQUEMA
        for key, config in schema.items():  
            widget = self.create_widget(key, config)    # CREA EL WIDGET USANDO LA KEY DEL PARAMETRO Y LA CONFIGURACION DEL MISMO
            label = config.get("label", key)

            self.form.addRow(label, widget) # AGREGA UNA LINEA DEBAJO PARA INSERTAR LABEL | WIDGET
            self.fields[key] = widget   # MAPEAMOS UN DICCIONARIO ENTRE KEYS Y WIDGETS CREADOS

    def reload(self, tool_name, base_path):
        self.setUpdatesEnabled(False)  # DESACTIVA ACTUALIZACIONES PARA EVITAR PARPADEOS
        self.tool_name = tool_name
        self.base_path = base_path

        while self.form.count():
            item = self.form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.fields.clear()

        self.build_ui()
        self.setUpdatesEnabled(True)   # REACTIVA ACTUALIZACIONES DESPUES DE RECONSTRUIR LA UI
        self.update()

    # CREA EL WIDGET SEGUN EL TIPO QUE DESCRIBA EL ESQUEMA
    def create_widget(self, key, config):
        t = config["type"]

        if t == "str":
            return QLineEdit()
        
        elif t == "float":
            w = QDoubleSpinBox()
            w.setRange(0, 100)
            w.setDecimals(1)
            return w
        
        elif t == "int":
            w = QDoubleSpinBox()
            w.setRange(0, 100)
            w.setDecimals(0)
            return w
        
        elif t == "bool":
            return QCheckBox()
        
        elif t == "choice":
            w = QComboBox()
            w.addItems(config["options"])
            return w
        
        elif t == "roi":
            # POR SIMPLICIDAD, USAREMOS UN BOTON PARA CAPTURAR EL ROI ACTUAL
            btn = QPushButton("Seleccionar ROI")
            btn.clicked.connect(lambda: self.select_roi(key))
            return btn
        
        elif t == "image_list":
            # UTILIZAMOS NUESTRO WIDGET DEDICADO PARA GUARDAR IMAGENES 
            w = ImageListWidget(
                get_frame_callback=self.get_frame,
                base_path=self.base_path,
                max_images=10
            )
            return w
        
        elif t == "video":
            w = VideoWidget(
                get_frame_callback=self.get_frame,
                enable_edition=False
            )
            return w

        
        else:
            print(f"Type: {t} creado como LineEdit")
            return QLineEdit()  # WIDGET POR DEFECTO
        
    def select_roi(self, key):
        # IMPLEMENTACION SIMPLIFICADA: SOLO IMPRIMIMOS UN MENSAJE
        # LO CONECTAMOS LUEGO
        print(f"Seleccionando ROI para {key}")
        
        # BUSCAR VIDEOWIDGET EN EL FORM
        for key, widget in self.fields.items():
            if isinstance(widget, VideoWidget):
                widget.enable_edition = True

    def get_values(self):
        data = {}

        for key, widget in self.fields.items():
            if hasattr(widget, "get_value"):
                data[key] = widget.get_value()
            
            elif isinstance(widget, QLineEdit):
                data[key] = widget.text()

            elif isinstance(widget, QDoubleSpinBox):
                data[key] = widget.value()

            elif isinstance(widget, QCheckBox):
                data[key] = widget.isChecked()

            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText()

            elif isinstance(widget, VideoWidget):
                data["roi"] = widget.get_roi()

            else:
                data[key] = None

        return data
    
    def set_values(self, data):
        for key, value in data.items():
            widget = self.fields.get(key)

            if widget is None:
                continue

            if hasattr(widget, "set_value"):
                widget.set_value(value)

            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))

            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))

            elif isinstance(widget, QComboBox):
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)