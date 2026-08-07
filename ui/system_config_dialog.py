import copy
import json
import os

from core.editor_models import (
    EditorValueError,
    build_model_map,
    parse_camera_device,
)
from core.system_config import SystemConfigError
from utils.qt_compat import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Signal,
    Qt,
)


class SystemConfigDialog(QDialog):
    """Edit one complete installation without creating product profiles."""

    configuration_saved = Signal(object)

    def __init__(self, system_config, recipe_manager, platform="windows", parent=None):
        super().__init__(parent)
        self.system_config = system_config
        self.recipe_manager = recipe_manager
        self.platform = platform
        self.setWindowTitle("Configuracion de instalacion")
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        title = QLabel("INSTALACION DEL MOTOR UNIVERSAL")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._build_station_tab()
        self._build_controller_tab()
        self._build_mapping_tab()
        self._build_runtime_tab()

        notice = QLabel(
            "Los cambios se validan y guardan con respaldo. "
            "Reinicia la aplicacion para aplicarlos."
        )
        notice.setWordWrap(True)
        root.addWidget(notice)

        buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_save = QPushButton("VALIDAR Y GUARDAR")
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)

    def _form_tab(self, title):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setContentsMargins(12, 12, 12, 12)
        form.setVerticalSpacing(10)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.tabs.addTab(page, title)
        return form

    @staticmethod
    def _int_spin(minimum, maximum):
        field = QSpinBox()
        field.setRange(minimum, maximum)
        field.setKeyboardTracking(False)
        return field

    @staticmethod
    def _float_spin(minimum, maximum, decimals=2):
        field = QDoubleSpinBox()
        field.setRange(minimum, maximum)
        field.setDecimals(decimals)
        field.setKeyboardTracking(False)
        return field

    def _build_station_tab(self):
        form = self._form_tab("Estacion")
        self.txt_installation_id = QLineEdit()
        self.txt_installation_name = QLineEdit()
        self.txt_recipe_file = QLineEdit()
        self.chk_auto_migrate = QCheckBox("Crear respaldo y migrar recetas heredadas")
        self.txt_camera_device = QLineEdit()
        self.spn_camera_width = self._int_spin(1, 16384)
        self.spn_camera_height = self._int_spin(1, 16384)
        self.spn_capture_fps = self._float_spin(0.1, 240.0, 1)
        self.spn_preview_fps = self._float_spin(0.1, 120.0, 1)
        self.cmb_default_focus = QComboBox()
        self.cmb_default_focus.addItems([
            "calibrated",
            "manual_fixed",
            "auto_continuous",
            "disabled",
        ])

        form.addRow("ID de instalacion", self.txt_installation_id)
        form.addRow("Nombre", self.txt_installation_name)
        form.addRow("Catalogo de recetas", self.txt_recipe_file)
        form.addRow("Migracion", self.chk_auto_migrate)
        form.addRow("Dispositivo de camara", self.txt_camera_device)
        form.addRow("Ancho", self.spn_camera_width)
        form.addRow("Alto", self.spn_camera_height)
        form.addRow("FPS de captura", self.spn_capture_fps)
        form.addRow("FPS de vista previa", self.spn_preview_fps)
        form.addRow("Enfoque predeterminado", self.cmb_default_focus)

    def _build_controller_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        protocol = QLabel("serial / vision_controller_v1 (contrato fijo)")
        protocol.setWordWrap(True)
        layout.addWidget(protocol)

        form = QFormLayout()
        self.spn_baudrate = self._int_spin(1, 4000000)
        self.spn_timeout = self._float_spin(0.01, 120.0, 2)
        self.chk_reset_on_connect = QCheckBox()
        self.chk_heartbeat = QCheckBox()
        self.chk_ready_notifications = QCheckBox()
        form.addRow("Baudrate", self.spn_baudrate)
        form.addRow("Timeout serial (s)", self.spn_timeout)
        form.addRow("Reset al conectar", self.chk_reset_on_connect)
        form.addRow("Heartbeat", self.chk_heartbeat)
        form.addRow("Publicar READY", self.chk_ready_notifications)
        layout.addLayout(form)

        layout.addWidget(QLabel("Puertos por plataforma"))
        self.tbl_ports = self._new_pair_table("Plataforma", "Puerto")
        layout.addWidget(self.tbl_ports, 1)
        layout.addLayout(self._table_buttons(self.tbl_ports, self._add_port_row))
        self.tabs.addTab(page, "Control")

    def _build_mapping_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        help_label = QLabel(
            "Mapea el identificador opaco enviado por el controlador al nombre "
            "exacto de una receta."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.tbl_model_map = self._new_pair_table(
            "ID externo",
            "Receta",
        )
        layout.addWidget(self.tbl_model_map, 1)
        layout.addLayout(
            self._table_buttons(self.tbl_model_map, self._add_model_row)
        )
        self.tabs.addTab(page, "Mapeo")

    def _build_runtime_tab(self):
        form = self._form_tab("Ejecucion")
        self.chk_require_controller_ready = QCheckBox()
        self.chk_require_controller_sync = QCheckBox()
        self.chk_require_focus_ready = QCheckBox()
        self.spn_max_frame_age = self._float_spin(0.01, 60.0, 2)
        self.spn_mechanical_settle = self._int_spin(0, 600000)
        form.addRow("Exigir controlador READY", self.chk_require_controller_ready)
        form.addRow("Exigir handshake", self.chk_require_controller_sync)
        form.addRow("Exigir enfoque listo", self.chk_require_focus_ready)
        form.addRow("Edad maxima de frame (s)", self.spn_max_frame_age)
        form.addRow("Asentamiento mecanico (ms)", self.spn_mechanical_settle)

    @staticmethod
    def _new_pair_table(first_header, second_header):
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels([first_header, second_header])
        table.setMinimumHeight(120)
        return table

    def _table_buttons(self, table, add_callback):
        row = QHBoxLayout()
        add = QPushButton("AGREGAR")
        remove = QPushButton("ELIMINAR")
        add.clicked.connect(add_callback)
        remove.clicked.connect(lambda: self._remove_current_row(table))
        row.addWidget(add)
        row.addWidget(remove)
        return row

    @staticmethod
    def _remove_current_row(table):
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def _add_port_row(self, platform="", port=""):
        row = self.tbl_ports.rowCount()
        self.tbl_ports.insertRow(row)
        self.tbl_ports.setItem(row, 0, QTableWidgetItem(str(platform)))
        self.tbl_ports.setItem(row, 1, QTableWidgetItem(str(port)))

    def _add_model_row(self, external_id="", recipe_name=""):
        row = self.tbl_model_map.rowCount()
        self.tbl_model_map.insertRow(row)
        self.tbl_model_map.setItem(row, 0, QTableWidgetItem(str(external_id)))
        combo = QComboBox()
        combo.setEditable(True)
        recipe_names = [
            recipe.get("name", "")
            for recipe in self.recipe_manager.get_all()
            if recipe.get("name")
        ]
        combo.addItems(recipe_names)
        if recipe_name:
            index = combo.findText(str(recipe_name))
            if index < 0:
                combo.addItem(str(recipe_name))
                index = combo.findText(str(recipe_name))
            combo.setCurrentIndex(index)
        self.tbl_model_map.setCellWidget(row, 1, combo)

    @staticmethod
    def _item_text(table, row, column):
        item = table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _load_values(self):
        data = self.system_config.data
        installation = data.get("installation", {})
        recipes = data.get("recipes", {})
        camera = data.get("camera", {})
        controller = data.get("controller", {})
        runtime = data.get("runtime", {})

        self.txt_installation_id.setText(str(installation.get("id", "")))
        self.txt_installation_name.setText(str(installation.get("name", "")))
        self.txt_recipe_file.setText(str(recipes.get("file", "")))
        self.chk_auto_migrate.setChecked(bool(recipes.get("auto_migrate", True)))
        self.txt_camera_device.setText(str(camera.get("device", 0)))
        self.spn_camera_width.setValue(int(camera.get("width", 1920)))
        self.spn_camera_height.setValue(int(camera.get("height", 1080)))
        self.spn_capture_fps.setValue(float(camera.get("capture_fps", 30)))
        self.spn_preview_fps.setValue(float(camera.get("preview_fps", 10)))
        focus_index = self.cmb_default_focus.findText(
            str(camera.get("default_focus_mode", "calibrated"))
        )
        self.cmb_default_focus.setCurrentIndex(max(0, focus_index))

        self.spn_baudrate.setValue(int(controller.get("baudrate", 115200)))
        self.spn_timeout.setValue(float(controller.get("timeout", 1.0)))
        self.chk_reset_on_connect.setChecked(
            bool(controller.get("reset_on_connect", True))
        )
        self.chk_heartbeat.setChecked(
            bool(controller.get("heartbeat_enabled", True))
        )
        self.chk_ready_notifications.setChecked(
            bool(controller.get("ready_notifications_enabled", True))
        )
        for platform, port in controller.get("ports", {}).items():
            self._add_port_row(platform, port)
        for external_id, recipe_name in controller.get("model_map", {}).items():
            self._add_model_row(external_id, recipe_name)

        self.chk_require_controller_ready.setChecked(
            bool(runtime.get("require_controller_ready", True))
        )
        self.chk_require_controller_sync.setChecked(
            bool(runtime.get("require_controller_sync", True))
        )
        self.chk_require_focus_ready.setChecked(
            bool(runtime.get("require_focus_ready", True))
        )
        self.spn_max_frame_age.setValue(
            float(runtime.get("max_frame_age_seconds", 0.5))
        )
        self.spn_mechanical_settle.setValue(
            int(runtime.get("mechanical_settle_ms", 0))
        )

    def _read_ports(self):
        ports = {}
        for row in range(self.tbl_ports.rowCount()):
            platform = self._item_text(self.tbl_ports, row, 0)
            port = self._item_text(self.tbl_ports, row, 1)
            if not platform and not port:
                continue
            if not platform or not port:
                raise EditorValueError(
                    "Cada puerto requiere plataforma y valor"
                )
            if platform in ports:
                raise EditorValueError(f"Plataforma duplicada: {platform}")
            ports[platform] = port
        return ports

    def _read_model_map(self):
        rows = []
        for row in range(self.tbl_model_map.rowCount()):
            external_id = self._item_text(self.tbl_model_map, row, 0)
            combo = self.tbl_model_map.cellWidget(row, 1)
            recipe_name = combo.currentText().strip() if combo else ""
            rows.append((external_id, recipe_name))
        return build_model_map(rows)

    def _candidate(self):
        candidate = copy.deepcopy(self.system_config.data)
        candidate["installation"].update({
            "id": self.txt_installation_id.text().strip(),
            "name": self.txt_installation_name.text().strip(),
        })
        candidate["recipes"].update({
            "file": self.txt_recipe_file.text().strip(),
            "auto_migrate": self.chk_auto_migrate.isChecked(),
        })
        candidate["camera"].update({
            "device": parse_camera_device(self.txt_camera_device.text()),
            "width": self.spn_camera_width.value(),
            "height": self.spn_camera_height.value(),
            "capture_fps": self.spn_capture_fps.value(),
            "preview_fps": self.spn_preview_fps.value(),
            "default_focus_mode": self.cmb_default_focus.currentText(),
        })
        candidate["controller"].update({
            "ports": self._read_ports(),
            "baudrate": self.spn_baudrate.value(),
            "timeout": self.spn_timeout.value(),
            "reset_on_connect": self.chk_reset_on_connect.isChecked(),
            "heartbeat_enabled": self.chk_heartbeat.isChecked(),
            "ready_notifications_enabled": self.chk_ready_notifications.isChecked(),
            "model_map": self._read_model_map(),
        })
        candidate["runtime"].update({
            "require_controller_ready": self.chk_require_controller_ready.isChecked(),
            "require_controller_sync": self.chk_require_controller_sync.isChecked(),
            "require_focus_ready": self.chk_require_focus_ready.isChecked(),
            "max_frame_age_seconds": self.spn_max_frame_age.value(),
            "mechanical_settle_ms": self.spn_mechanical_settle.value(),
        })
        return candidate

    def _save(self):
        try:
            candidate = self._candidate()
            recipe_names = self._recipe_names_for(candidate)
            saved = self.system_config.save(
                candidate,
                recipe_names=recipe_names,
            )
        except (EditorValueError, SystemConfigError, ValueError) as exc:
            QMessageBox.critical(self, "Configuracion invalida", str(exc))
            return

        self.configuration_saved.emit(saved)
        QMessageBox.information(
            self,
            "Configuracion guardada",
            "La configuracion es valida. Reinicia la aplicacion para aplicarla.",
        )
        self.accept()

    def _recipe_names_for(self, candidate):
        recipe_file = candidate.get("recipes", {}).get("file", "")
        current_file = getattr(self.recipe_manager, "path", "")
        if os.path.abspath(recipe_file) == os.path.abspath(current_file):
            return [
                recipe.get("name")
                for recipe in self.recipe_manager.get_all()
                if recipe.get("name")
            ]

        if not os.path.exists(recipe_file):
            return []
        try:
            with open(recipe_file, "r", encoding="utf-8") as recipe_stream:
                payload = json.load(recipe_stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise EditorValueError(
                f"No se pudo leer el catalogo de recetas: {exc}"
            ) from exc
        recipes = payload.get("recipes", []) if isinstance(payload, dict) else []
        return [
            recipe.get("name")
            for recipe in recipes
            if isinstance(recipe, dict) and recipe.get("name")
        ]
