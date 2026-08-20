import sys
import cv2
import os
# IMPORTS DE QT
from utils.qt_compat import (
    load_ui,
    QT_LIB,
    QThread,
    QImage,
    QPixmap,
    QMainWindow,
    QApplication,
    QMetaObject,
    Qt,
    QTimer,
    QLabel,
)
from utils.ui_logger import get_ui_logger
# IMPORTS DE UI
if QT_LIB == "PySide6":
    from ui.pyside6.ui_main_window import Ui_MainWindow
else:
    from ui.pyqt5.ui_main_window import Ui_MainWindow
from ui.config_window_logic import ConfigWindow
# IMPORTS DE HERRAMIENTAS, SERVICIOS Y LOGICA
from tools.registry import discover_tool_registry
from core.state_manager import StateManager
from services.camera import Camera
from processing.pipeline import VisionPipeline
from services.serial_comm import SerialComm
from app.state_worker import StateWorker
from vision.camera_worker import CameraWorker
from core.recipe_manager import RecipeManager
from core.system_config import SystemConfig
from core.diagnostics import DiagnosticsManager, run_static_diagnostics
from core.traceability import CycleTraceWriter
from core.operator_status import build_operator_status
from ui.responsive import (
    apply_main_window_layout,
    compact_stylesheet,
    profile_from_screen,
    profile_from_widget,
)
from ui.theme import interface_stylesheet, operator_stylesheet

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Sistema de vision")
        self.display_profile = profile_from_widget(self)
        apply_main_window_layout(self, self.ui, self.display_profile)
        self.installation_name = "Motor de vision"
        self._configure_operator_interface()
        QTimer.singleShot(0, self._bind_display_screen)

        self.setup_ui_logger()
        print(f"Qt backend: {QT_LIB}")

        self.platform = self.detect_platform()
        print(f"[CAMERA] Sistema operativo detectado: {self.platform}")

        config_path = os.getenv("VISION_SYSTEM_CONFIG", "config/system.json")
        self.system_config = SystemConfig(config_path)
        self.camera_config = self.system_config.section("camera")
        self.controller_config = self.system_config.section("controller")
        self.runtime_config = self.system_config.section("runtime")
        installation = self.system_config.section("installation")
        self.commissioning_mode = bool(
            installation.get("commissioning_mode", False)
        )
        self.installation_name = installation.get(
            "name",
            installation.get("id", "Motor de vision"),
        )
        self.ui.lbl_tittle.setText(
            f"SISTEMA DE VISIÓN  ·  {self.installation_name}"
        )
        print(
            f"[CONFIG] Instalacion activa: "
            f"{installation.get('name', installation.get('id'))}"
        )

        self.apply_main_button_feedbacks()

        # ASIGNAR WIDGETS DE LA UI A VARIABLES CORRESPONDIENTES
        self.lbl_video = self.ui.lbl_video
        self.lbl_video.get_frame = self.get_current_frame
        self.btn_trigger = self.ui.indicator_1
        self.btn_config = self.ui.btn_config

        # CONECTAR WIDGETS
        self.btn_config.clicked.connect(self.open_config)
        self.ui.btn_cerrar.clicked.connect(self.close)
        self.ui.btn_minimizar.clicked.connect(self.minimize)

        self.current_frame = None
        self.selected_recipe = None
        self.rois_to_apply = []

        # BANDERAS
        self.fsm_busy = False
        self.focus_ready_for_active_recipe = False
        self.focus_check_busy = False
        self.pending_trigger_after_focus = False
        self.focus_runtime_verified = False
        self.configuration_restart_required = False

        # BLOQUEOS DE PRODUCCION
        self.require_controller_ready = bool(
            self.runtime_config.get("require_controller_ready", True)
        )
        self.require_controller_sync = bool(
            self.runtime_config.get("require_controller_sync", True)
        )
        self.production_focus_required = bool(
            self.runtime_config.get("require_focus_ready", True)
        )
        self.max_frame_age = float(
            self.runtime_config.get("max_frame_age_seconds", 0.50)
        )
        self.last_recipe_result = None
        self.last_esp_result = None

        # ESTADO VISUAL DEL INDICADOR
        # El resultado final de ESP32/PLC queda enclavado visualmente.
        # Solo se limpia al comenzar un nuevo ciclo valido o al recibir RESET.
        self.indicator_latched_result = None
        self.indicator_epoch = 0

        # Estado visual general del sistema.
        # READY permite mostrar resultado OK/NG.
        # WARNING/CRITICAL tienen prioridad sobre cualquier resultado.
        self.current_system_visual_state = "WARNING"
        self.current_system_ready_error = "Sistema iniciando"
        self.refresh_operator_dashboard()

        # EVALUAR SISTEMA LISTO PARA TRIGGER
        self.last_ready_sent = None
        self.last_ready_reason = None
        self.ready_notify_interval = 1000
        self.ready_timer = QTimer(self)
        self.ready_timer.timeout.connect(self.publish_rpi_ready_status)
        self.ready_timer.start(self.ready_notify_interval)

        self.tool_registry = discover_tool_registry()
        self.recipe_manager = RecipeManager(
            self.system_config.recipe_file,
            auto_migrate=self.system_config.auto_migrate_recipes,
            tool_registry=self.tool_registry,
            default_focus_mode=self.camera_config.get(
                "default_focus_mode",
                "calibrated",
            ),
        )
        traceability_config = self.system_config.section("traceability")
        self.cycle_trace = CycleTraceWriter.from_config(
            traceability_config,
            installation_id=installation.get("id", "vision-station"),
        )
        self.diagnostics = DiagnosticsManager(
            self.cycle_trace.diagnostics_path
        )
        startup_report = run_static_diagnostics(
            manager=self.diagnostics,
            system_config=self.system_config,
            recipe_manager=self.recipe_manager,
            tool_registry=self.tool_registry,
            trace_writer=self.cycle_trace,
            platform=self.platform,
        )
        print(
            f"[DIAGNOSTICS] Arranque estatico: "
            f"{startup_report['overall_status']} "
            f"({len(startup_report['items'])} comprobaciones)"
        )
        # Construir todos los componentes antes de arrancar hilos evita que
        # una camara ausente termine su worker mientras el resto del runtime
        # todavia se inicializa (por ejemplo, durante el reset DTR en Windows).
        self.camera_thread = None
        self.camera_worker = None
        self.serial_thread = None
        self.serial = None
        self.state_thread = None
        self.state_worker = None

        try:
            self.setup_camera()
            self.setup_serial()
            self.setup_state_manager()
            self.start_runtime_workers()
            if self.commissioning_mode:
                QTimer.singleShot(250, self.open_commissioning_configuration)
        except Exception:
            self.shutdown_runtime_components()
            raise

    def setup_ui_logger(self):
        self.ui_logger = get_ui_logger()
        self.ui_logger.install()

        if hasattr(self.ui, "list_log"):
            print(f"[LOGGER] list_log detectado: {type(self.ui.list_log)}")

            self.ui_logger.attach_list_widget(
                self.ui.list_log,
                max_items=80,
                load_history=True
            )
        else:
            print("[LOGGER][ERROR] No existe list_log en ui")

        print("[LOGGER] Loger de interfaz iniciao")

    def _configure_operator_interface(self):
        """Remove legacy per-widget styling and expose one semantic dashboard."""
        for widget in (
            self.ui.centralwidget,
            self.ui.top_bar,
            self.ui.lbl_tittle,
            self.ui.btn_minimizar,
            self.ui.btn_cerrar,
            self.ui.lbl_cam,
            self.ui.lbl_video,
            self.ui.lbl_model,
            self.ui.btn_config,
            self.ui.indicator_1,
            self.ui.lbl_indicator_1,
            self.ui.bttm_bar,
            self.ui.list_log,
        ):
            widget.setStyleSheet("")

        self.ui.lbl_cam.setText("VISTA DE INSPECCIÓN")
        self.ui.btn_config.setText("CONFIGURAR ESTACIÓN")
        self.ui.btn_minimizar.setText("—")
        self.ui.btn_cerrar.setText("×")
        self.ui.btn_config.setProperty("buttonRole", "primary")
        self.ui.btn_cerrar.setProperty("buttonRole", "danger")
        self.ui.indicator_1.setProperty("statusLevel", "warning")
        self.ui.indicator_1.setToolTip(
            "Indicador de estado. Los ciclos son iniciados por el controlador."
        )
        self.ui.indicator_1.setFocusPolicy(Qt.NoFocus)
        self.ui.indicator_1.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.ui.lbl_model.setWordWrap(True)
        self.ui.lbl_indicator_1.setWordWrap(True)
        self.ui.lbl_model.setAlignment(Qt.AlignCenter)
        self.ui.lbl_indicator_1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.ui.lbl_tittle.setAccessibleName("Instalacion activa")
        self.ui.lbl_video.setAccessibleName("Vista de la camara")
        self.ui.lbl_model.setAccessibleName("Receta activa")
        self.ui.indicator_1.setAccessibleName("Estado de inspeccion")
        self.ui.lbl_indicator_1.setAccessibleName("Detalle del estado")
        self.ui.btn_config.setAccessibleName("Abrir configuracion")
        self.ui.btn_minimizar.setAccessibleName("Minimizar")
        self.ui.btn_cerrar.setAccessibleName("Cerrar aplicacion")
        self.lbl_recent_events = QLabel("EVENTOS\nRECIENTES")
        self.lbl_recent_events.setObjectName("lbl_recent_events")
        self.lbl_recent_events.setProperty("uiRole", "logCaption")
        self.lbl_recent_events.setAlignment(Qt.AlignCenter)
        self.lbl_recent_events.setAccessibleName("Eventos recientes")
        self.ui.horizontalLayout_3.insertWidget(0, self.lbl_recent_events)
        self.ui.list_log.setToolTip(
            "Ultimos eventos del motor. Consulte la trazabilidad para el detalle."
        )
        self._apply_interface_theme()

    def _apply_interface_theme(self):
        stylesheet = (
            interface_stylesheet(self.display_profile)
            + operator_stylesheet(self.display_profile)
            + compact_stylesheet(self.display_profile)
        )
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet)
        self.setStyleSheet(stylesheet)

    @staticmethod
    def _refresh_widget_style(widget):
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def refresh_operator_dashboard(self):
        recipe = getattr(self, "selected_recipe", None)
        recipe_name = recipe.get("name") if isinstance(recipe, dict) else None
        view = build_operator_status(
            getattr(self, "current_system_visual_state", "WARNING"),
            getattr(self, "current_system_ready_error", "Sistema iniciando"),
            final_result=getattr(self, "indicator_latched_result", None),
            cycle_busy=bool(getattr(self, "fsm_busy", False)),
            recipe_name=recipe_name,
        )
        self.ui.lbl_model.setText(f"RECETA ACTIVA\n{view.recipe_caption}")
        self.ui.lbl_indicator_1.setText(
            f"{view.headline}\n{view.detail}"
        )
        self.ui.lbl_indicator_1.setToolTip(view.detail)
        self.ui.indicator_1.setText(view.indicator_text)
        self.ui.indicator_1.setProperty("statusLevel", view.level)
        self.ui.btn_config.setEnabled(
            not bool(getattr(self, "fsm_busy", False))
            and not bool(getattr(self, "focus_check_busy", False))
        )
        self._refresh_widget_style(self.ui.indicator_1)

    def detect_platform(self):
        if sys.platform.startswith("win"):
            return "windows"

        if sys.platform.startswith("linux"):
            return "linux"

        return "other"

    def _bind_display_screen(self):
        """Refresh the layout if the window is moved to another monitor."""
        handle = self.windowHandle()
        if handle is None:
            return
        try:
            handle.screenChanged.connect(self.on_display_screen_changed)
        except (AttributeError, TypeError):
            pass

    def on_display_screen_changed(self, screen):
        self.display_profile = profile_from_screen(screen)
        apply_main_window_layout(self, self.ui, self.display_profile)
        self._apply_interface_theme()
        self.refresh_operator_dashboard()
        print(
            f"[UI] Pantalla activa: {self.display_profile.width}x"
            f"{self.display_profile.height} ({self.display_profile.mode})"
        )

    def apply_main_button_feedbacks(self):
        buttons = [
            self.ui.btn_config,
        ]

        for btn in buttons:
            self.add_button_feedback(btn)

    def add_button_feedback(self, button):
        button.setCursor(Qt.PointingHandCursor)

    def setup_camera(self):
        # CREAR THREAD Y WORKER DE CAMARA
        self.camera_thread = QThread()
        self.camera_worker = CameraWorker(
            camera_index=self.camera_config.get("device", 0),
            width=int(self.camera_config.get("width", 1920)),
            height=int(self.camera_config.get("height", 1080)),
            capture_fps=float(self.camera_config.get("capture_fps", 30)),
            preview_fps=float(self.camera_config.get("preview_fps", 10)),
            focus_mode=self.camera_config.get("default_focus_mode", "calibrated"),
            platform=self.platform,
        )

        # MOVER WORKER AL HILO DE VISION
        self.camera_worker.moveToThread(self.camera_thread)

        # INICIAR EL LOOP EN EL WORKER CUANDO SE INICIE EL HILO
        self.camera_thread.started.connect(self.camera_worker.start)

        # CONEXIONES CLAVE
        self.camera_worker.frame_ready.connect(self.update_frame)
        self.camera_worker.finished.connect(self.camera_thread.quit)
        self.camera_worker.focus_check_finished.connect(self.on_focus_check_finished)
        self.camera_worker.focus_check_failed.connect(self.on_focus_check_failed)
        self.camera_worker.diagnostic_update.connect(self.on_component_diagnostic)

        # Se inicia despues, cuando todos los receptores ya existen.

    def update_frame(self, frame):
        self.current_frame = frame      # GUARDAR FRAME ACTUAL PARA COMPARTIR

    def apply_rois_from_recipe(self):
        self.selected_recipe = self.recipe_manager.get_selected()
        self.rois_to_apply = []
        if self.selected_recipe:
            for step in self.selected_recipe.get("steps", []):
                params = step.get("params",{})
                roi = params.get("roi")
                if roi:
                    x1, y1, x2, y2 = roi
                    self.rois_to_apply.append((x1, y1, x2, y2))
            self.lbl_video.set_rois(self.rois_to_apply)

        self.apply_focus_from_recipe(self.selected_recipe)
        if hasattr(self, "current_system_visual_state"):
            self.refresh_operator_dashboard()

    def apply_focus_from_recipe(self, recipe):
        self.focus_ready_for_active_recipe = False
        self.focus_runtime_verified = False

        if not recipe:
            print("[APP] No hay receta activa para cargar enfoque")
            self.camera_worker.set_focus_from_recipe({})
            return

        focus = self.recipe_manager.get_focus(recipe["name"])

        print(f"[APP] Cargando enfoque desde receta {recipe['name']}: {focus}")

        self.camera_worker.set_focus_from_recipe(focus)
        self.focus_ready_for_active_recipe = self.is_focus_config_complete(focus)

        if self.focus_ready_for_active_recipe:
            print("[FOCUS] Enfoque guardado detectado para receta activa")
        else:
            print("[FOCUS][WARNING] La receta activa no tiene enfoque guardado completo")

    def setup_serial(self):
        puerto = self.system_config.controller_port(self.platform)

        self.serial_thread = QThread()
        self.serial = SerialComm(
            port=puerto,
            baudrate=int(self.controller_config.get("baudrate", 115200)),
            timeout=float(self.controller_config.get("timeout", 1.0)),
            reset_on_connect=bool(self.controller_config.get("reset_on_connect", True)),
            model_map=self.controller_config.get("model_map", {}),
            heartbeat_enabled=bool(
                self.controller_config.get("heartbeat_enabled", True)
            ),
            ready_notifications_enabled=bool(
                self.controller_config.get("ready_notifications_enabled", True)
            ),
        )

        self.serial.moveToThread(self.serial_thread)

        self.serial_thread.started.connect(self.serial.start_listening)

        self.serial.cycle_trigger_received.connect(self.on_cycle_trigger_received)
        self.serial.cycle_cancelled.connect(self.on_cycle_cancelled)
        self.serial.model_received.connect(self.on_model_changed)
        self.serial.esp_result_received.connect(self.on_esp_result_received)
        self.serial.reset_received.connect(self.on_esp_reset_received)
        self.serial.connection_lost.connect(self.on_serial_connection_lost)
        self.serial.connection_restored.connect(self.on_serial_connection_restored)
        self.serial.diagnostic_update.connect(self.on_component_diagnostic)

        # Se inicia junto con el resto del runtime completamente conectado.

    def on_serial_connection_lost(self, reason):
        print(f"[APP][SERIAL] Conexion perdida: {reason}")

        self.last_ready_sent = None
        self.last_ready_reason = None

        self.set_system_status_visual("CRITICAL", f"Conexion perdida: {reason}")
        if hasattr(self, "state_manager"):
            self.state_manager.cancel_cycle(reason="SERIAL_CONNECTION_LOST")

    def on_serial_connection_restored(self):
        print("[APP][SERIAL] Conexion restaurada con ESP32")
        self.last_ready_sent = None
        self.last_ready_reason = None
        self.publish_rpi_ready_status()

    def setup_state_manager(self):
        # COMPONENTES DEL STATE_MANAGER
        self.camera = Camera()
        self.processor = VisionPipeline(self.tool_registry)
        self.comm = self.serial

        self.state_manager = StateManager(
            self.camera,
            self.processor,
            self.comm,
            mechanical_settle_ms=int(
                self.runtime_config.get("mechanical_settle_ms", 0)
            ),
            inspection_timeout_seconds=float(
                self.runtime_config.get("inspection_timeout_seconds", 20.0)
            ),
            cycle_trace=self.cycle_trace,
        )

        # THREAD + WORKER
        self.state_thread = QThread()
        self.state_worker = StateWorker(self.state_manager)

        self.state_worker.moveToThread(self.state_thread)

        # CONEXIONES
        self.state_thread.finished.connect(self.state_worker.deleteLater)
        self.camera_worker.frame_ready.connect(self.camera.update_frame)

        self.state_manager.inspectionResult.connect(self.on_recipe_result)
        self.state_manager.cycleTraced.connect(self.on_cycle_traced)

        self.state_worker.cycle_finished.connect(self.on_fsm_finished)

            # STATE MANAGER OBTIENE RECIPE MANAGER PARA ACCEDER A LAS RECETAS DESDE EL WORKER
        self.state_manager.set_recipe_manager(self.recipe_manager)
        self.state_manager.load_selected_recipe()
        self.selected_recipe = self.recipe_manager.get_selected()
        self.apply_rois_from_recipe()
        self.refresh_operator_dashboard()

        # LOG
        self.state_worker.log.connect(print)

        # Se inicia en start_runtime_workers().

    def start_runtime_workers(self):
        """Start the fully wired runtime in a deterministic, safe order."""
        self.state_thread.start()
        self.serial_thread.start()
        self.camera_thread.start()

    def on_component_diagnostic(self, item):
        if not isinstance(item, dict):
            return
        blocking = bool(item.get("blocking", False))
        if item.get("component") == "controller" and not self.require_controller_ready:
            blocking = False
        saved = self.diagnostics.update(
            key=item.get("key", "runtime.unknown"),
            status=item.get("status", "ERROR"),
            component=item.get("component", "runtime"),
            message=item.get("message", "Diagnostico sin mensaje"),
            action=item.get("action", ""),
            details=item.get("details", {}),
            blocking=blocking,
        )
        print(
            f"[DIAGNOSTICS][{saved['status']}] "
            f"{saved['component']}: {saved['message']}"
        )
        self.last_ready_sent = None
        self.last_ready_reason = None

    def on_cycle_traced(self, record):
        if not isinstance(record, dict):
            return
        print(
            f"[TRACEABILITY] Ciclo {record.get('cycle_id')} "
            f"{record.get('final_result')} en {record.get('duration_ms')} ms"
        )

    def set_indicator_result_style(self, result):
        synthetic_state = "READY"
        synthetic_result = result
        synthetic_reason = None
        if result == "NOT_READY":
            synthetic_state = "WARNING"
            synthetic_result = None
            synthetic_reason = self.current_system_ready_error
        elif result == "CRITICAL":
            synthetic_state = "CRITICAL"
            synthetic_result = None
            synthetic_reason = self.current_system_ready_error
        elif result == "BASE":
            synthetic_result = None

        recipe = self.selected_recipe if isinstance(self.selected_recipe, dict) else {}
        view = build_operator_status(
            synthetic_state,
            synthetic_reason,
            final_result=synthetic_result,
            cycle_busy=False,
            recipe_name=recipe.get("name"),
        )
        self.ui.lbl_model.setText(f"RECETA ACTIVA\n{view.recipe_caption}")
        self.ui.lbl_indicator_1.setText(f"{view.headline}\n{view.detail}")
        self.ui.lbl_indicator_1.setToolTip(view.detail)
        self.ui.indicator_1.setText(view.indicator_text)
        self.ui.indicator_1.setProperty("statusLevel", view.level)
        self._refresh_widget_style(self.ui.indicator_1)

    def refresh_indicator_visual(self):
        """
        Aplica la prioridad visual final del indicador.

        Prioridad:
        1. CRITICAL del sistema
        2. WARNING del sistema
        3. Resultado final OK/NG de ESP si el sistema está READY
        4. BASE si el sistema está READY y no hay resultado
        """
        self.refresh_operator_dashboard()

    # MEJORAR PARA ACTUALIZAR LA PALETA DE COLORES DE TODA LA INTERFAZ SEGUN EL ESTADO O RESULTADO
    def set_system_status_visual(self, state, reason=None, log=True):
        """
        Actualiza el estado general del sistema y refresca el indicador
        usando prioridad centralizada.

        Solo imprime cuando el estado o la razón cambian.
        """
        state_changed = state != self.current_system_visual_state
        reason_changed = reason != self.current_system_ready_error
        should_log = log and reason and (state_changed or reason_changed)

        self.current_system_visual_state = state
        self.current_system_ready_error = reason

        self.refresh_indicator_visual()

        if should_log:
            print(f"[APP][STATUS] {state}: {reason}")

    def clear_indicator_for_new_cycle(self):
        """
        Limpia el resultado visual anterior cuando comienza un nuevo ciclo valido.
        El color final sigue respetando el estado general del sistema.
        """
        self.indicator_epoch += 1
        self.indicator_latched_result = None
        self.last_esp_result = None
        self.refresh_indicator_visual()

    def clear_indicator_from_reset(self):
        """
        Limpia el resultado visual por RESET/llave de calidad recibido desde ESP32/PLC.
        Después vuelve a publicar el estado real del sistema.
        """
        self.indicator_epoch += 1
        self.indicator_latched_result = None
        self.last_esp_result = None
        self.last_ready_sent = None
        self.last_ready_reason = None
        self.publish_rpi_ready_status()

    def update_indicator(self, result, delay=None, latch=False):
        """
        Guarda o muestra resultado de inspección.

        Si latch=True, el resultado OK/NG/ERROR de ESP queda guardado, pero no
        necesariamente visible. La prioridad visual final la decide
        refresh_indicator_visual().
        """
        result = str(result or "ERROR").upper()
        if result not in ("OK", "NG", "ERROR"):
            result = "ERROR"

        if latch:
            self.indicator_epoch += 1
            self.indicator_latched_result = result
            self.last_esp_result = result
            if result == "ERROR":
                self.set_system_status_visual(
                    "CRITICAL",
                    "El controlador reporto un error de ciclo",
                )
                return
            self.refresh_indicator_visual()
            return

        # Avisos temporales locales solo se muestran si el sistema está READY.
        # Si el sistema está WARNING/CRITICAL, esos estados tienen prioridad.
        if self.current_system_visual_state != "READY":
            self.refresh_indicator_visual()
            return

        self.indicator_epoch += 1
        epoch = self.indicator_epoch

        self.set_indicator_result_style(result)

        if delay is not None and delay > 0:
            QTimer.singleShot(delay, lambda: self.reset_temporary_indicator(epoch))
            # Avisos temporales locales ya no deben imponerse si el estado general
            # está evaluado como WARNING/CRITICAL.
            if self.current_system_visual_state in ("WARNING", "CRITICAL"):
                self.set_system_status_visual(
                    self.current_system_visual_state,
                    self.current_system_ready_error
                )
                return

            self.indicator_epoch += 1
            epoch = self.indicator_epoch

            self.set_indicator_result_style(result)

            if delay is not None and delay > 0:
                QTimer.singleShot(delay, lambda: self.reset_temporary_indicator(epoch))

    def reset_temporary_indicator(self, epoch):
        if epoch != self.indicator_epoch:
            return

        self.refresh_indicator_visual()

    def on_recipe_result(self, result):
        self.last_recipe_result = result
        print(f"[APP] Resultado de receta enviado a ESP32: {result}")

    def on_esp_result_received(self, result):
        self.last_esp_result = result
        print(f"[APP] Resultado final recibido desde ESP32/PLC: {result}")
        self.update_indicator(result, latch=True)

    def on_esp_reset_received(self):
        print("[APP] RESET recibido desde ESP32/PLC")
        self.clear_indicator_from_reset()

    def on_cycle_trigger_received(self, event):
        if not isinstance(event, dict):
            print("[APP][CONTROLLER][ERROR] Trigger sin contexto valido")
            return

        recipe_name = event.get("recipe_name")
        if recipe_name and (
            not self.selected_recipe
            or self.selected_recipe.get("name") != recipe_name
        ):
            self.on_model_changed(recipe_name)

        try:
            self.state_manager.prepare_cycle(event)
        except (ValueError, RuntimeError) as exc:
            print(f"[APP][CONTROLLER][ERROR] Ciclo rechazado: {exc}")
            self.reject_controller_cycle(event, str(exc))
            return

        if not self.run_fsm():
            self.reject_controller_cycle(event, "Raspberry dejo de estar lista")

    def reject_controller_cycle(self, event, reason):
        cycle_id = event.get("cycle_id") if isinstance(event, dict) else None
        print(
            f"[APP][CONTROLLER] Reportando ERROR seguro para ciclo "
            f"{cycle_id}: {reason}"
        )
        if cycle_id and hasattr(self, "serial"):
            self.serial.send_command("ERROR", cycle_id=cycle_id)
        if hasattr(self, "state_manager"):
            self.state_manager.cancel_cycle(cycle_id=cycle_id, reason=reason)

    def on_cycle_cancelled(self, event):
        event = event if isinstance(event, dict) else {}
        reason = event.get("reason", "CANCELLED")
        cycle_id = event.get("cycle_id")
        print(f"[APP][CONTROLLER] Ciclo {cycle_id} cancelado: {reason}")
        if hasattr(self, "state_manager"):
            self.state_manager.cancel_cycle(cycle_id=cycle_id, reason=reason)
        self.clear_indicator_from_reset()

    def is_focus_config_complete(self, focus):
        if not isinstance(focus, dict):
            return False

        mode = focus.get("mode", "calibrated")
        if mode == "disabled":
            return True
        if mode == "auto_continuous":
            return bool(focus.get("enabled", True))
        if not focus.get("enabled", False):
            return False

        value = focus.get("value")
        if mode == "manual_fixed":
            return value is not None

        return value is not None and focus.get("min_score") is not None

    def validate_active_recipe_for_production(self):
        recipe = self.selected_recipe or self.recipe_manager.get_selected()

        if not recipe:
            return "No hay receta activa"
        return self.recipe_manager.get_execution_error(
            recipe,
            available_tools=self.processor.tool_registry.keys(),
        )

    def get_focus_ready_error(self):
        if not self.production_focus_required:
            return None

        if not hasattr(self, "camera_worker") or self.camera_worker is None:
            return "CameraWorker no disponible"

        if getattr(self.camera_worker, "calibrating", False):
            return "Camara calibrando enfoque"

        if getattr(self.camera_worker, "focus_busy", False):
            return "Camara enfocando/calibrando"

        focus = self.get_active_focus_config()
        can_prepare_on_trigger = (
            focus.get("mode", "calibrated") == "calibrated"
            and focus.get("verify_on_first_trigger", True)
            and self.platform == "linux"
            and getattr(self.camera_worker, "focus_absolute_supported", False)
        )

        if not getattr(self.camera_worker, "focus_ready", False) and can_prepare_on_trigger:
            return None

        if not getattr(self.camera_worker, "focus_ready", False):
            return "Foco de camara no listo/no aplicado"

        if callable(getattr(self.camera_worker, "has_applied_focus", None)):
            if not self.camera_worker.has_applied_focus():
                return "Foco de camara no aplicado"

        return None

    def get_system_ready_error(self):
        if self.commissioning_mode:
            return "Estacion en modo configuracion; produccion bloqueada"

        if self.configuration_restart_required:
            return "Reinicio requerido para aplicar la configuracion"

        if hasattr(self, "diagnostics"):
            diagnostic_error = self.diagnostics.blocking_reason()
            if diagnostic_error:
                return diagnostic_error

        if not hasattr(self, "state_thread") or not self.state_thread.isRunning():
            return "State thread no esta corriendo"

        if not hasattr(self, "state_manager") or self.state_manager is None:
            return "State manager no disponible"

        if self.state_manager.state != "IDLE":
            return f"FSM ocupada en estado {self.state_manager.state}"

        recipe_error = self.validate_active_recipe_for_production()
        if recipe_error:
            return recipe_error

        focus_error = self.get_focus_ready_error()
        if focus_error:
            return focus_error

        if not hasattr(self, "camera") or self.camera is None:
            return "Camera no disponible"

        if not self.camera.has_fresh_frame(max_age=self.max_frame_age):
            return "No hay frame fresco de camara"

        if self.require_controller_ready:
            if not hasattr(self, "serial") or self.serial is None:
                return "Serial no disponible"

            if not self.serial.is_connected():
                return "Serial no conectado"

            if self.require_controller_sync and not self.serial.synced:
                return "Controlador sin handshake HELLO_ACK"

            remote_error = getattr(
                self.serial,
                "remote_not_ready_reason",
                None,
            )
            if remote_error:
                return remote_error

        if self.focus_check_busy:
            return "Enfoque/Calibracion en proceso"

        return None

    def classify_ready_error(self, ready_error):
        """
        Clasifica la razón de bloqueo para decidir color visual.

        WARNING = condición temporal o esperada:
        - enfocando
        - FSM ocupada
        - sin frame fresco al arranque
        - foco no listo
        - receta/configuración pendiente

        CRITICAL = falla de infraestructura:
        - serial desconectado
        - sin handshake
        - hilos caídos
        - workers no disponibles
        """
        if not ready_error:
            return "READY"

        text = ready_error.lower()

        critical_keywords = (
            "serial no conectado",
            "serial sin handshake",
            "state thread no esta corriendo",
            "state manager no disponible",
            "cameraworker no disponible",
            "camera worker no disponible",
            "thread no esta corriendo",
            "conexion perdida",
            "desconectado",
        )

        for keyword in critical_keywords:
            if keyword in text:
                return "CRITICAL"

        warning_keywords = (
            "fsm ocupada",
            "enfoque",
            "calibr",
            "foco",
            "no hay frame fresco",
            "receta",
            "roi",
            "dmtx",
            "step",
            "expected_code",
            "sensores esp32",
            "modo configuracion",
            "reinicio requerido",
        )

        for keyword in warning_keywords:
            if keyword in text:
                return "WARNING"

        # Por seguridad, cualquier error desconocido se trata como crítico.
        return "CRITICAL"

    def publish_rpi_ready_status(self):
        if not hasattr(self, "serial") or self.serial is None:
            ready_error = "Serial no disponible"
            visual_state = self.classify_ready_error(ready_error)
            self.set_system_status_visual(visual_state, ready_error)
            return

        if not self.serial.is_connected():
            ready_error = "Serial no conectado"
            visual_state = self.classify_ready_error(ready_error)
            self.set_system_status_visual(visual_state, ready_error)
            return

        ready_error = self.get_system_ready_error()
        ready_now = ready_error is None

        if ready_now:
            if self.last_ready_sent != "READY":
                print("[APP][READY] Raspberry lista para produccion")
                self.serial.notify_rpi_ready()
                self.last_ready_sent = "READY"
                self.last_ready_reason = None

            self.set_system_status_visual("READY", None, log=False)
            return

        visual_state = self.classify_ready_error(ready_error)

        if self.last_ready_sent != "NOT_READY" or self.last_ready_reason != ready_error:
            print(f"[APP][READY] Raspberry NO lista: {ready_error}")
            self.serial.notify_rpi_not_ready(ready_error)
            self.last_ready_sent = "NOT_READY"
            self.last_ready_reason = ready_error

        self.set_system_status_visual(visual_state, ready_error, log=False)

    def run_fsm(self):
        pending_cycle = getattr(self.state_manager, "pending_cycle", None)
        if not isinstance(pending_cycle, dict) or not pending_cycle.get("cycle_id"):
            print(
                "[FSM][BLOQUEADO] No existe un ciclo valido del controlador"
            )
            return False

        if self.fsm_busy:
            print("[FSM] Ciclo ocupado, trigger ignorado")
            return False

        if self.focus_check_busy:
            print("[FOCUS] Verificacion/recalibracion de enfoque en proceso, trigger ignorado")
            return False

        ready_error = self.get_system_ready_error()
        if ready_error:
            print(f"[SYSTEM][BLOQUEADO] Trigger rechazado: {ready_error}")
            visual_state = self.classify_ready_error(ready_error)
            self.set_system_status_visual(visual_state, ready_error)
            return False

        self.clear_indicator_for_new_cycle()

        if self.should_check_focus_before_trigger():
            self.start_focus_check_before_trigger()
            return True

        return self.start_fsm_cycle(reset_indicator=False)

    def get_active_focus_config(self):
        recipe = self.selected_recipe or self.recipe_manager.get_selected()

        if not recipe:
            return {}

        focus = recipe.get("focus", {})
        return focus if isinstance(focus, dict) else {}

    def focus_check_is_supported_for_current_platform(self):
        focus = self.get_active_focus_config()
        return (
            self.production_focus_required
            and focus.get("mode", "calibrated") == "calibrated"
            and self.platform == "linux"
            and getattr(self.camera_worker, "focus_absolute_supported", False)
        )

    def should_check_focus_before_trigger(self):
        if not self.focus_check_is_supported_for_current_platform():
            return False

        focus = self.get_active_focus_config()

        verify_on_first_trigger = focus.get("verify_on_first_trigger", True)
        if verify_on_first_trigger is False:
            return False

        return not self.focus_runtime_verified

    def start_focus_check_before_trigger(self):
        focus_config = self.get_active_focus_config()

        print(
            "[FOCUS] Verificando enfoque antes del trigger. "
            "Si el score es bajo o no hay foco guardado, se recalibrara automaticamente."
        )

        if hasattr(self, "serial") and self.serial.is_connected():
            self.serial.notify_calibrating()

        self.focus_check_busy = True
        self.pending_trigger_after_focus = True
        self.refresh_operator_dashboard()
        self.camera_worker.request_focus_check_before_trigger(focus_config)

    def start_fsm_cycle(self, reset_indicator=True):
        if self.fsm_busy:
            print("[FSM] Ciclo ocupado, trigger ignorado")
            return False

        ready_error = self.get_system_ready_error()
        if ready_error:
            print(f"[SYSTEM][BLOQUEADO] Ciclo no iniciado: {ready_error}")
            self.fsm_busy = False
            return False

        if reset_indicator:
            self.clear_indicator_for_new_cycle()

        self.fsm_busy = True
        self.refresh_operator_dashboard()

        if self.state_thread.isRunning():
            QMetaObject.invokeMethod(
                self.state_worker,
                "run_once",
                Qt.QueuedConnection
            )
            return True

        self.fsm_busy = False
        self.refresh_operator_dashboard()
        return False

    def on_fsm_finished(self):
        self.fsm_busy = False
        self.refresh_operator_dashboard()

    def get_current_frame(self):
        return self.current_frame

    def on_model_changed(self, model_name):
        if not model_name:
            print("[SERIAL] Modelo vacio, cambio ignorado")
            return

        print(f"Cambiando receta a modelo: {model_name}")

        self.recipe_manager.set_selected(model_name)
        self.state_manager.set_active_recipe(model_name)

        self.selected_recipe = self.recipe_manager.get(model_name)

        self.apply_rois_from_recipe()
        self.apply_focus_from_recipe(self.selected_recipe)

        self.refresh_operator_dashboard()

    def open_config(self):
        if self.fsm_busy or self.focus_check_busy or (hasattr(self, "state_manager") and self.state_manager.state != "IDLE"):
            print("[CONFIG][BLOQUEADO] No se puede abrir configuracion durante un ciclo activo")
            return

        self.config_window = ConfigWindow(
            recipe_manager=self.recipe_manager,
            get_frame_callback=self.get_current_frame,
            state_manager=self.state_manager,
            platform=self.platform,
            camera_worker=self.camera_worker,
            system_config=self.system_config,
            tool_registry=self.tool_registry,
            display_profile=self.display_profile,
        )
        # CONECTAR SIGNALS DESDE CONFIG WINDOW
        self.config_window.update_rois.connect(
            self.apply_rois_from_recipe,
            Qt.UniqueConnection
        )

        self.config_window.focus_calibration_requested.connect(
            self.request_camera_focus_from_config,
            Qt.DirectConnection
        )
        self.config_window.restart_required.connect(
            self.on_system_configuration_saved,
            Qt.UniqueConnection,
        )

        if self.platform == "linux":
            self.config_window.showFullScreen()
        else:
            self.config_window.show()

    def open_commissioning_configuration(self):
        """Guide a neutral first boot directly to station discovery."""
        if not self.commissioning_mode:
            return
        self.open_config()
        if hasattr(self, "config_window"):
            QTimer.singleShot(50, self.config_window.open_system_config)

    def on_system_configuration_saved(self, _saved_config):
        self.configuration_restart_required = True
        self.last_ready_sent = None
        self.last_ready_reason = None
        self.publish_rpi_ready_status()
        print(
            "[CONFIG] Configuracion guardada. Reinicie la aplicacion para "
            "aplicar camara, controlador y runtime."
        )

    def request_camera_focus_from_config(self, focus_config):
        print(f"[APP] Solicitud de calibración recibida desde ConfigWindow: {focus_config}")

        if not hasattr(self, "camera_worker") or self.camera_worker is None:
            print("[APP][ERROR] camera_worker no disponible")
            return

        self.camera_worker.request_manual_focus_from_config(focus_config)

    def on_focus_check_finished(self, result):
        print(f"[APP] Resultado verificación enfoque: {result}")

        self.focus_check_busy = False
        self.refresh_operator_dashboard()

        if not isinstance(result, dict) or not result.get("ok"):
            print("[APP][ERROR] Verificación de enfoque no válida")
            self.pending_trigger_after_focus = False
            return

        self.focus_ready_for_active_recipe = True
        self.focus_runtime_verified = True

        if result.get("focus_updated") and self.selected_recipe:
            focus_data = {
                "mode": "calibrated",
                "enabled": True,
                "roi": result.get("roi"),
                "value": result.get("focus_value"),
                "min_score": result.get("min_score"),
                "median_score": result.get("median_score"),
                "peak_score": result.get("peak_score"),
                "verify_on_first_trigger": True,
                "auto_refocus_if_failed": True,
            }

            self.recipe_manager.update_focus(self.selected_recipe["name"], focus_data)
            self.selected_recipe = self.recipe_manager.get(self.selected_recipe["name"])
            self.camera_worker.set_focus_from_recipe(focus_data)

            print(f"[APP] Receta actualizada con nuevo enfoque: {focus_data}")

        if self.pending_trigger_after_focus:
            self.pending_trigger_after_focus = False
            self.start_fsm_cycle(reset_indicator=False)

    def on_focus_check_failed(self, message):
        print(f"[APP][ERROR] Verificación de enfoque falló: {message}")

        self.focus_check_busy = False
        self.pending_trigger_after_focus = False
        self.focus_ready_for_active_recipe = False
        self.focus_runtime_verified = False

        self.last_ready_sent = None
        self.last_ready_reason = None
        self.set_system_status_visual("WARNING", message)
        self.publish_rpi_ready_status()

    def shutdown_thread(self,thread, worker, name="thread"):
        # DETENER WORKERS
        if worker:
            try:
                worker.stop()
            except RuntimeError as exc:
                print(f"[SHUTDOWN][WARNING] {name} ya no esta disponible: {exc}")

        # MANEJO SEGURO DEL THREAD
        if thread and thread.isRunning():
            print(f"Esperando thread de {name}")
            thread.quit()

            if not thread.wait(3000):
                print(f"{name} no responde, intentando stop extra...")

                if worker:
                    try:
                        worker.stop()
                    except RuntimeError:
                        pass

                if not thread.wait(2000):
                    print(f"Forzando terminate en {name}")
                    thread.terminate()
                    thread.wait()

    def shutdown_runtime_components(self):
        """Stop every component that may exist after a partial startup."""
        ready_timer = getattr(self, "ready_timer", None)
        if ready_timer is not None:
            ready_timer.stop()

        self.shutdown_thread(
            getattr(self, "camera_thread", None),
            getattr(self, "camera_worker", None),
            "camera",
        )
        self.shutdown_thread(
            getattr(self, "state_thread", None),
            getattr(self, "state_worker", None),
            "state",
        )
        self.shutdown_thread(
            getattr(self, "serial_thread", None),
            getattr(self, "serial", None),
            "serial",
        )

    def closeEvent(self, event):
        print("Close Event ejecutado")

        self.shutdown_runtime_components()

        print("App cerrada correctamente")
        event.accept()

    def minimize(self):
        self.showNormal()
        self.showMinimized()
