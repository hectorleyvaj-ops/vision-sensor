import copy
import json
import os
import threading

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
    QTimer,
    QVBoxLayout,
    QWidget,
    Signal,
    Qt,
)
from ui.responsive import compact_stylesheet, profile_from_widget
from ui.theme import interface_stylesheet
from core.camera_runtime import format_camera_runtime
from core.focus_modes import FOCUS_MODE_LABELS
from services.hardware_discovery import (
    discover_cameras,
    discover_serial_controllers,
    format_camera_candidate,
    format_serial_candidate,
)


class SystemConfigDialog(QDialog):
    """Edit one complete installation without creating product profiles."""

    configuration_saved = Signal(object)
    hardware_discovery_finished = Signal(object)

    def __init__(
        self,
        system_config,
        recipe_manager,
        platform="windows",
        parent=None,
        display_profile=None,
        camera_runtime=None,
        controller_runtime=None,
    ):
        super().__init__(parent)
        self.system_config = system_config
        self.recipe_manager = recipe_manager
        self.platform = platform
        self.camera_runtime = dict(camera_runtime or {})
        self.controller_runtime = dict(controller_runtime or {})
        self._discovery_running = False
        self.display_profile = display_profile or profile_from_widget(parent or self)
        self.setWindowTitle("Configuracion de la estacion")
        self.setStyleSheet(
            interface_stylesheet(self.display_profile)
            + compact_stylesheet(self.display_profile)
        )
        self._build_ui()
        self._load_values()
        self.hardware_discovery_finished.connect(
            self._on_hardware_discovery_finished
        )
        QTimer.singleShot(100, self.refresh_hardware)

    def _build_ui(self):
        root = QVBoxLayout(self)
        margin = self.display_profile.margin
        root.setContentsMargins(margin, margin, margin, margin)
        root.setSpacing(self.display_profile.spacing)

        title = QLabel("CONFIGURACION DE LA ESTACION")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("uiRole", "summary")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        root.addWidget(self.tabs, 1)

        self._build_station_tab()
        self._build_controller_tab()
        self._build_mapping_tab()
        self._build_runtime_tab()
        self._build_traceability_tab()
        self._apply_help_texts()

        notice = QLabel(
            "Los cambios se validan y guardan con respaldo. "
            "Reinicia la aplicacion para aplicarlos."
        )
        notice.setWordWrap(True)
        root.addWidget(notice)

        buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_save = QPushButton("VALIDAR Y GUARDAR")
        self.btn_save.setProperty("buttonRole", "primary")
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)
        self.btn_refresh_cameras.clicked.connect(self.refresh_hardware)
        self.btn_refresh_controllers.clicked.connect(self.refresh_hardware)
        self.cmb_camera_candidates.currentIndexChanged.connect(
            self._apply_camera_candidate
        )
        self.cmb_controller_candidates.currentIndexChanged.connect(
            self._apply_controller_candidate
        )

    def _form_tab(self, title):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        margin = self.display_profile.margin
        form.setContentsMargins(margin, margin, margin, margin)
        form.setVerticalSpacing(self.display_profile.spacing)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.tabs.addTab(page, title)
        return form

    def _layout_tab(self, title):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        margin = self.display_profile.margin
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(self.display_profile.spacing)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.tabs.addTab(page, title)
        return layout

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
        self.chk_commissioning_mode = QCheckBox(
            "Permitir configuracion y bloquear produccion"
        )
        self.txt_recipe_file = QLineEdit()
        self.chk_auto_migrate = QCheckBox("Crear respaldo y migrar recetas heredadas")
        self.txt_camera_device = QLineEdit()
        self.cmb_camera_candidates = QComboBox()
        self.btn_refresh_cameras = QPushButton("BUSCAR HARDWARE")
        camera_picker = QWidget()
        camera_picker_layout = QHBoxLayout(camera_picker)
        camera_picker_layout.setContentsMargins(0, 0, 0, 0)
        camera_picker_layout.addWidget(self.cmb_camera_candidates, 1)
        camera_picker_layout.addWidget(self.btn_refresh_cameras)
        self.lbl_camera_discovery = QLabel(
            "La busqueda conserva el dispositivo actual hasta que elijas otro."
        )
        self.lbl_camera_discovery.setWordWrap(True)
        self.lbl_active_camera = QLabel(format_camera_runtime(self.camera_runtime))
        self.lbl_active_camera.setWordWrap(True)
        self.spn_camera_width = self._int_spin(1, 16384)
        self.spn_camera_height = self._int_spin(1, 16384)
        self.spn_capture_fps = self._float_spin(0.1, 240.0, 1)
        self.spn_preview_fps = self._float_spin(0.1, 120.0, 1)
        self.cmb_default_focus = QComboBox()
        for value, label in FOCUS_MODE_LABELS.items():
            self.cmb_default_focus.addItem(label, value)

        form.addRow("ID de instalacion", self.txt_installation_id)
        form.addRow("Nombre", self.txt_installation_name)
        form.addRow("Modo de configuracion", self.chk_commissioning_mode)
        form.addRow("Catalogo de recetas", self.txt_recipe_file)
        form.addRow("Migracion", self.chk_auto_migrate)
        form.addRow("Dispositivo de camara", self.txt_camera_device)
        form.addRow("Camaras detectadas", camera_picker)
        form.addRow("Busqueda", self.lbl_camera_discovery)
        form.addRow("Camara activa ahora", self.lbl_active_camera)
        form.addRow("Ancho de captura", self.spn_camera_width)
        form.addRow("Alto de captura", self.spn_camera_height)
        form.addRow("FPS de captura", self.spn_capture_fps)
        form.addRow("FPS de vista previa", self.spn_preview_fps)
        form.addRow("Enfoque predeterminado", self.cmb_default_focus)

    def _build_controller_tab(self):
        layout = self._layout_tab("Control")
        protocol = QLabel("serial / vision_controller_v1 (contrato fijo)")
        protocol.setWordWrap(True)
        layout.addWidget(protocol)

        controller_picker = QWidget()
        controller_picker_layout = QHBoxLayout(controller_picker)
        controller_picker_layout.setContentsMargins(0, 0, 0, 0)
        self.cmb_controller_candidates = QComboBox()
        self.btn_refresh_controllers = QPushButton("BUSCAR HARDWARE")
        controller_picker_layout.addWidget(self.cmb_controller_candidates, 1)
        controller_picker_layout.addWidget(self.btn_refresh_controllers)
        layout.addWidget(QLabel("Controladores y puertos detectados"))
        layout.addWidget(controller_picker)
        self.lbl_controller_discovery = QLabel(
            "Solo se identifica el controlador; GPIO y logica permanecen en la ESP32."
        )
        self.lbl_controller_discovery.setWordWrap(True)
        layout.addWidget(self.lbl_controller_discovery)

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

    def _build_mapping_tab(self):
        layout = self._layout_tab("Mapeo")
        help_label = QLabel(
            "Este cuadro no ordena ni asigna prioridad a las recetas. Mapea "
            "cada identificador recibido del controlador al nombre de una "
            "receta; el orden de las filas no cambia el funcionamiento."
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

    def _build_runtime_tab(self):
        form = self._form_tab("Ejecucion")
        self.chk_require_controller_ready = QCheckBox()
        self.chk_require_controller_sync = QCheckBox()
        self.chk_require_focus_ready = QCheckBox()
        self.spn_max_frame_age = self._float_spin(0.01, 60.0, 2)
        self.spn_mechanical_settle = self._int_spin(0, 600000)
        self.spn_inspection_timeout = self._float_spin(0.1, 3600.0, 1)
        form.addRow("Exigir controlador READY", self.chk_require_controller_ready)
        form.addRow("Exigir handshake", self.chk_require_controller_sync)
        form.addRow("Exigir enfoque listo", self.chk_require_focus_ready)
        form.addRow("Edad maxima de frame (s)", self.spn_max_frame_age)
        form.addRow("Asentamiento mecanico (ms)", self.spn_mechanical_settle)
        form.addRow("Timeout de inspeccion (s)", self.spn_inspection_timeout)

    def _build_traceability_tab(self):
        form = self._form_tab("Registros")
        self.chk_traceability_enabled = QCheckBox()
        self.txt_traceability_directory = QLineEdit()
        self.spn_trace_file_size = self._float_spin(0.1, 4096.0, 1)
        self.spn_trace_retention_files = self._int_spin(1, 1000)
        self.spn_trace_retention_days = self._int_spin(0, 3650)
        form.addRow("Guardar ciclos", self.chk_traceability_enabled)
        form.addRow("Directorio", self.txt_traceability_directory)
        form.addRow("Tamano por archivo (MB)", self.spn_trace_file_size)
        form.addRow("Archivos retenidos", self.spn_trace_retention_files)
        form.addRow("Retencion maxima (dias)", self.spn_trace_retention_days)

    def _apply_help_texts(self):
        help_texts = {
            self.txt_installation_id: "ID tecnico estable de esta estacion.",
            self.txt_installation_name: "Nombre legible mostrado en registros.",
            self.chk_commissioning_mode: "Mantiene READY=0 mientras se instala hardware y se crean recetas.",
            self.txt_recipe_file: "Ruta al catalogo JSON de recetas de esta instalacion.",
            self.chk_auto_migrate: "Convierte esquemas heredados y conserva un archivo .bak.",
            self.txt_camera_device: "Indice 0, 1, etc. o ruta persistente del dispositivo.",
            self.cmb_camera_candidates: "Inventario detectado; la seleccion se copia al campo de dispositivo.",
            self.lbl_active_camera: "Dispositivo y formato que usa la sesion actual; los cambios requieren reinicio.",
            self.spn_camera_width: "Ancho solicitado a la camara; no es el ancho del monitor.",
            self.spn_camera_height: "Alto solicitado a la camara; no es el alto del monitor.",
            self.spn_capture_fps: "Frames por segundo adquiridos desde la camara.",
            self.spn_preview_fps: "Frecuencia visual; puede reducirse para ahorrar CPU.",
            self.cmb_default_focus: "Modo inicial de enfoque para recetas nuevas.",
            self.spn_baudrate: "Velocidad serial; debe coincidir con el controlador.",
            self.cmb_controller_candidates: "Puertos enumerados y controladores compatibles identificados por handshake.",
            self.spn_timeout: "Espera maxima de lectura/escritura serial.",
            self.chk_reset_on_connect: "Permite reiniciar el controlador al abrir el puerto.",
            self.chk_heartbeat: "Supervisa que el enlace con el controlador siga vivo.",
            self.chk_ready_notifications: "Publica READY o NOT_READY al controlador.",
            self.tbl_ports: "Puerto por sistema operativo; puede incluir una entrada default.",
            self.tbl_model_map: (
                "Traduce el ID externo recibido a una receta existente. "
                "El orden de las filas no establece prioridad."
            ),
            self.chk_require_controller_ready: "Bloquea triggers si el controlador no esta listo.",
            self.chk_require_controller_sync: "Exige negociar vision_controller_v1 antes de producir.",
            self.chk_require_focus_ready: "Bloquea produccion sin enfoque valido.",
            self.spn_max_frame_age: "Descarta frames mas antiguos que este limite.",
            self.spn_mechanical_settle: "Espera cancelable para inmovilizar la pieza tras el trigger.",
            self.spn_inspection_timeout: "Tiempo total maximo del ciclo de vision.",
            self.chk_traceability_enabled: "Conserva un registro JSON por cada ciclo.",
            self.txt_traceability_directory: "Directorio de registros y diagnostico de arranque.",
            self.spn_trace_file_size: "Rota cycles.jsonl cuando alcanza este tamano.",
            self.spn_trace_retention_files: "Cantidad maxima de archivos de ciclos conservados.",
            self.spn_trace_retention_days: "Elimina rotaciones mas antiguas; 0 desactiva este limite.",
        }
        for widget, description in help_texts.items():
            widget.setToolTip(description)

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
        remove.setProperty("buttonRole", "danger")
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
        traceability = data.get("traceability", {})

        self.txt_installation_id.setText(str(installation.get("id", "")))
        self.txt_installation_name.setText(str(installation.get("name", "")))
        self.chk_commissioning_mode.setChecked(
            bool(installation.get("commissioning_mode", False))
        )
        self.txt_recipe_file.setText(str(recipes.get("file", "")))
        self.chk_auto_migrate.setChecked(bool(recipes.get("auto_migrate", True)))
        camera_device = camera.get("device")
        self.txt_camera_device.setText(
            "" if camera_device is None else str(camera_device)
        )
        self.spn_camera_width.setValue(int(camera.get("width", 1920)))
        self.spn_camera_height.setValue(int(camera.get("height", 1080)))
        self.spn_capture_fps.setValue(float(camera.get("capture_fps", 30)))
        self.spn_preview_fps.setValue(float(camera.get("preview_fps", 10)))
        focus_index = self.cmb_default_focus.findData(
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
        self.spn_inspection_timeout.setValue(
            float(runtime.get("inspection_timeout_seconds", 20.0))
        )
        self.chk_traceability_enabled.setChecked(
            bool(traceability.get("enabled", True))
        )
        self.txt_traceability_directory.setText(
            str(traceability.get("directory", "runtime/traceability"))
        )
        self.spn_trace_file_size.setValue(
            float(traceability.get("max_file_size_mb", 10.0))
        )
        self.spn_trace_retention_files.setValue(
            int(traceability.get("retention_files", 10))
        )
        self.spn_trace_retention_days.setValue(
            int(traceability.get("retention_days", 30))
        )

    def refresh_hardware(self):
        """Discover endpoints in the background without changing selection."""
        if self._discovery_running:
            return
        self._discovery_running = True
        self.btn_refresh_cameras.setEnabled(False)
        self.btn_refresh_controllers.setEnabled(False)
        self.lbl_camera_discovery.setText("Buscando camaras disponibles...")
        self.lbl_controller_discovery.setText(
            "Enumerando puertos y verificando vision_controller_v1..."
        )
        configured_camera_text = self.txt_camera_device.text().strip()
        configured_camera = parse_camera_device(
            configured_camera_text,
            allow_unassigned=True,
        )
        baudrate = self.spn_baudrate.value()
        platform = self.platform
        camera_runtime = dict(self.camera_runtime)
        controller_runtime = dict(self.controller_runtime)

        def run_discovery():
            payload = {"cameras": [], "controllers": [], "errors": []}
            try:
                payload["cameras"] = discover_cameras(
                    platform,
                    configured_device=configured_camera,
                    active_info=camera_runtime,
                )
            except Exception as exc:
                payload["errors"].append(f"Camaras: {exc}")
            try:
                payload["controllers"] = discover_serial_controllers(
                    baudrate=baudrate,
                    active_info=controller_runtime,
                )
            except Exception as exc:
                payload["errors"].append(f"Controladores: {exc}")
            self.hardware_discovery_finished.emit(payload)

        threading.Thread(
            target=run_discovery,
            name="hardware-discovery",
            daemon=True,
        ).start()

    def _on_hardware_discovery_finished(self, payload):
        self._discovery_running = False
        self.btn_refresh_cameras.setEnabled(True)
        self.btn_refresh_controllers.setEnabled(True)
        payload = dict(payload or {})
        cameras = list(payload.get("cameras") or [])
        controllers = list(payload.get("controllers") or [])

        self.cmb_camera_candidates.blockSignals(True)
        self.cmb_camera_candidates.clear()
        self.cmb_camera_candidates.addItem("Selecciona una camara detectada", None)
        for record in cameras:
            self.cmb_camera_candidates.addItem(
                format_camera_candidate(record),
                record,
            )
        self.cmb_camera_candidates.setCurrentIndex(0)
        self.cmb_camera_candidates.blockSignals(False)

        available_cameras = sum(
            1 for record in cameras if record.get("available")
        )
        self.lbl_camera_discovery.setText(
            f"{available_cameras} camara(s) disponible(s) de "
            f"{len(cameras)} candidato(s)."
        )

        self.cmb_controller_candidates.blockSignals(True)
        self.cmb_controller_candidates.clear()
        self.cmb_controller_candidates.addItem(
            "Selecciona un puerto o controlador detectado",
            None,
        )
        for record in controllers:
            self.cmb_controller_candidates.addItem(
                format_serial_candidate(record),
                record,
            )
        self.cmb_controller_candidates.setCurrentIndex(0)
        self.cmb_controller_candidates.blockSignals(False)

        verified = sum(
            1 for record in controllers if record.get("verified_controller")
        )
        self.lbl_controller_discovery.setText(
            f"{len(controllers)} puerto(s) detectado(s); "
            f"{verified} controlador(es) compatible(s) verificado(s). "
            "La seleccion no modifica GPIO ni logica de la ESP32."
        )
        errors = list(payload.get("errors") or [])
        if errors:
            self.lbl_controller_discovery.setText(
                self.lbl_controller_discovery.text()
                + " Errores: "
                + "; ".join(errors)
            )

    def _apply_camera_candidate(self, index):
        if index <= 0:
            return
        record = self.cmb_camera_candidates.currentData()
        if not isinstance(record, dict):
            return
        if not record.get("available"):
            self.lbl_camera_discovery.setText(
                f"No se selecciono {record.get('device')}: "
                f"{record.get('status', 'no disponible')}"
            )
            return
        self.txt_camera_device.setText(str(record.get("device")))
        self.lbl_camera_discovery.setText(
            f"Camara propuesta: {record.get('device')}. "
            "Guarda y reinicia para aplicarla."
        )

    def _apply_controller_candidate(self, index):
        if index <= 0:
            return
        record = self.cmb_controller_candidates.currentData()
        if not isinstance(record, dict) or not record.get("device"):
            return
        self._set_platform_port(self.platform, record["device"])
        self.lbl_controller_discovery.setText(
            f"Puerto propuesto para {self.platform}: {record['device']}. "
            f"{record.get('status', '')} Guarda y reinicia para aplicarlo."
        )

    def _set_platform_port(self, platform, port):
        for row in range(self.tbl_ports.rowCount()):
            if self._item_text(self.tbl_ports, row, 0) == platform:
                self.tbl_ports.setItem(row, 1, QTableWidgetItem(str(port)))
                return
        self._add_port_row(platform, port)

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
        commissioning_mode = self.chk_commissioning_mode.isChecked()
        candidate["installation"].update({
            "id": self.txt_installation_id.text().strip(),
            "name": self.txt_installation_name.text().strip(),
            "commissioning_mode": commissioning_mode,
        })
        candidate["recipes"].update({
            "file": self.txt_recipe_file.text().strip(),
            "auto_migrate": self.chk_auto_migrate.isChecked(),
        })
        candidate["camera"].update({
            "device": parse_camera_device(
                self.txt_camera_device.text(),
                allow_unassigned=commissioning_mode,
            ),
            "width": self.spn_camera_width.value(),
            "height": self.spn_camera_height.value(),
            "capture_fps": self.spn_capture_fps.value(),
            "preview_fps": self.spn_preview_fps.value(),
            "default_focus_mode": str(
                self.cmb_default_focus.currentData() or "calibrated"
            ),
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
            "inspection_timeout_seconds": self.spn_inspection_timeout.value(),
        })
        candidate.setdefault("traceability", {}).update({
            "enabled": self.chk_traceability_enabled.isChecked(),
            "directory": self.txt_traceability_directory.text().strip(),
            "max_file_size_mb": self.spn_trace_file_size.value(),
            "retention_files": self.spn_trace_retention_files.value(),
            "retention_days": self.spn_trace_retention_days.value(),
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
