from utils.qt_compat import (
    QWidget, QFormLayout, QLineEdit, QPushButton, QDoubleSpinBox,
    QComboBox, QCheckBox, QSizePolicy, Qt
)
from ui.widgets.img_list_widget import ImageListWidget
from ui.widgets.video_widget import VideoWidget
from core.display_profile import build_display_profile
from ui.responsive import profile_from_widget

class ToolEditor(QWidget):
    def __init__(
        self,
        tool_name,
        tool_schema,
        get_frame_callback,
        base_path,
        edit=False,
        editing_index=None,
        platform="windows",
        screen_size=None,
        display_profile=None,
    ):
        super().__init__()

        self.tool_name = tool_name
        self.tool_schema = dict(tool_schema or {})
        self.get_frame = get_frame_callback
        self.base_path = base_path
        self.edit = edit
        self.editing_index = editing_index
        self.platform = platform
        self.screen_size = screen_size
        self.display_profile = display_profile or (
            build_display_profile(*screen_size)
            if screen_size
            else profile_from_widget(self)
        )

        self.fields = {}

        self.form = QFormLayout()
        margin = self.display_profile.margin
        spacing = self.display_profile.spacing
        self.form.setContentsMargins(margin, margin, margin, margin)
        self.form.setHorizontalSpacing(max(spacing, spacing * 2))
        self.form.setVerticalSpacing(max(6, spacing))
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.setLayout(self.form)

        self.build_ui()

    def build_ui(self):
        schema = self.tool_schema

        # OBTENEMOS EL LABEL Y EL TYPE DEL WIDGET PARA CADA PARAMETRO SEGUN EL ESQUEMA
        for key, config in schema.items():  
            widget = self.create_widget(key, config)    # CREA EL WIDGET USANDO LA KEY DEL PARAMETRO Y LA CONFIGURACION DEL MISMO
            label = config.get("label", key)

            self.form.addRow(label, widget) # AGREGA UNA LINEA DEBAJO PARA INSERTAR LABEL | WIDGET
            self.fields[key] = widget   # MAPEAMOS UN DICCIONARIO ENTRE KEYS Y WIDGETS CREADOS

    def reload(self, tool_name, tool_schema, base_path):
        self.setUpdatesEnabled(False)  # DESACTIVA ACTUALIZACIONES PARA EVITAR PARPADEOS
        self.tool_name = tool_name
        self.tool_schema = dict(tool_schema or {})
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
        field_height = self.display_profile.touch_target

        if t == "str":
            w = QLineEdit()
            w.setMinimumHeight(field_height)
            if "default" in config:
                w.setText(str(config.get("default", "")))
            return w
        
        elif t == "float":
            w = QDoubleSpinBox()
            w.setRange(float(config.get("min", 0)), float(config.get("max", 100)))
            w.setDecimals(int(config.get("decimals", 1)))
            if "step" in config:
                w.setSingleStep(float(config["step"]))
            if "default" in config:
                w.setValue(float(config["default"]))
            w.setCursor(Qt.ArrowCursor)
            w.setKeyboardTracking(False)
            w.setMinimumHeight(field_height)
            return w
        
        elif t == "int":
            w = QDoubleSpinBox()
            w.setRange(int(config.get("min", 0)), int(config.get("max", 100)))
            w.setDecimals(0)
            if "step" in config:
                w.setSingleStep(int(config["step"]))
            if "default" in config:
                w.setValue(int(config["default"]))
            w.setCursor(Qt.ArrowCursor)
            w.setKeyboardTracking(False)
            w.setMinimumHeight(field_height)
            return w
        
        elif t == "bool":
            w = QCheckBox()
            w.setChecked(bool(config.get("default", False)))
            return w
        
        elif t == "choice":
            w = QComboBox()
            w.addItems(config["options"])
            default = config.get("default")
            if default is not None:
                index = w.findText(str(default))
                if index >= 0:
                    w.setCurrentIndex(index)
            w.setMinimumHeight(field_height)
            return w
        
        elif t == "roi":
            # POR SIMPLICIDAD, USAREMOS UN BOTON PARA CAPTURAR EL ROI ACTUAL
            btn = QPushButton("Seleccionar ROI")
            btn.setMinimumHeight(field_height)
            btn.setCursor(Qt.PointingHandCursor)
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
            video_w = max(240, min(520, int(self.display_profile.width * 0.62)))
            video_h = max(112, self.display_profile.dialog_video_height)
            video_size = (video_w, video_h)

            w = VideoWidget(
                get_frame_callback=self.get_frame,
                enable_edition=False,
                platform=self.platform,
                video_size=video_size,
                fill_mode="fit"
            )

            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            if video_size:
                w.setMinimumHeight(video_size[1])
                w.setMaximumHeight(video_size[1])

            return w

        
        else:
            print(f"Type: {t} creado como LineEdit")
            return QLineEdit()  # WIDGET POR DEFECTO
        
    def select_roi(self, key):
        # IMPLEMENTACION SIMPLIFICADA: SOLO IMPRIMIMOS UN MENSAJE
        # LO CONECTAMOS LUEGO
        print(f"Seleccionando ROI para {key}")
        
        # BUSCAR VIDEOWIDGET EN EL FORM
        for _field_key, widget in self.fields.items():
            if isinstance(widget, VideoWidget):
                widget.enable_edition = True
                roi_button = self.fields.get(key)
                if isinstance(roi_button, QPushButton):
                    roi_button.setText("Dibuja la ROI sobre la imagen")

    def get_values(self):
        data = {}

        for key, widget in self.fields.items():
            if key == "roi":
                continue

            if hasattr(widget, "get_value"):
                data[key] = widget.get_value()
            
            elif isinstance(widget, QLineEdit):
                data[key] = widget.text()

            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()
                data[key] = int(value) if widget.decimals() == 0 else value

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
            if key == "roi":
                video_widget = self.get_video_widget()
                if video_widget and value:
                    roi = tuple(value)
                    video_widget.roi = roi
                    video_widget.set_rois([roi])
                continue

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

    # HELPER
    def get_video_widget(self):
        for widget in self.fields.values():
            if isinstance(widget, VideoWidget):
                return widget
            
        return None
