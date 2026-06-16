import sys
import cv2
# IMPORTS DE QT
from utils.qt_compat import load_ui, QT_LIB, QThread, QImage, QPixmap, QMainWindow, QMetaObject, Qt, QTimer
from utils.ui_logger import get_ui_logger
# IMPORTS DE UI
from ui.pyside6.ui_main_window import Ui_MainWindow
from ui.config_window_logic import ConfigWindow
# IMPORTS DE HERRAMIENTAS, SERVICIOS Y LOGICA
from tools.compare_img_hist import CompareImgHistTool
from tools.dmtx_tool import DataMatrixTool
from core.state_manager import StateManager
from services.camera import Camera
from processing.pipeline import VisionPipeline
from services.serial_comm import SerialComm
from app.state_worker import StateWorker
from vision.camera_worker import CameraWorker
from core.recipe_manager import RecipeManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setup_ui_logger()
        print(f"Qt backend: {QT_LIB}")

        self.platform = self.detect_platform()
        print(f"[CAMERA] Sistema operativo detectado: {self.platform}")

        self.apply_main_button_feedbacks()

        # ASIGNAR WIDGETS DE LA UI A VARIABLES CORRESPONDIENTES
        self.lbl_video = self.ui.lbl_video
        self.lbl_video.get_frame = self.get_current_frame
        self.btn_trigger = self.ui.indicator_1
        self.btn_config = self.ui.btn_config

        # CONECTAR WIDGETS
        self.btn_trigger.clicked.connect(self.run_fsm)
        self.btn_config.clicked.connect(self.open_config)
        self.ui.btn_cerrar.clicked.connect(self.close)

        self.current_frame = None
        self.selected_recipe = None
        self.rois_to_apply = []

        # BANDERAS
        self.fsm_busy = False
        self.focus_ready_for_active_recipe = False
        self.focus_check_busy = False
        self.pending_trigger_after_focus = False
        self.focus_runtime_verified = False

        # BLOQUEOS DE PRODUCCION
        self.require_serial_ready = True
        # Dejar False si el firmware actual de la ESP32 aun no responde SYNC_OK.
        # Cuando agregues handshake al firmware final, cambialo a True.
        self.require_serial_sync = False
        self.require_single_dmtx_recipe = True
        self.production_focus_required = True
        self.max_frame_age = 0.50
        self.last_recipe_result = None
        self.last_esp_result = None

        # ESTADO VISUAL DEL INDICADOR
        # El resultado final de ESP32/PLC queda enclavado visualmente.
        # Solo se limpia al comenzar un nuevo ciclo valido o al recibir RESET.
        self.indicator_latched_result = None
        self.indicator_epoch = 0

        self.BASE_STYLE = """
        border: 2px solid;
        font-size: 16px;
        border-radius: 30px;
        border-color: rgb(46, 196, 182);
        color: rgb(46, 196, 182);
        background-color: rgb(15, 27, 61);
        """

        self.OK_STYLE = """
        border: 2px solid;
        font-size: 16px;
        border-radius: 30px;
        border-color: rgb(82, 183, 136);
        color: white;
        background-color: rgb(46, 125, 50);
        """

        self.NG_STYLE = """
        border: 2px solid;
        font-size: 16px;
        border-radius: 30px;
        border-color: rgb(230, 57, 70);
        color: white;
        background-color: rgb(183, 28, 28);
        """

        self.lbl_video.setStyleSheet("""
            QLabel {
                background-color: black;
                border-radius: 0px;
                border: 2px solid rgb(91, 192, 190);
            }
        """)

        self.recipe_manager = RecipeManager("core/models/recipes.json")
        self.setup_camera()
        self.setup_serial()
        self.setup_state_manager()

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
        
    def detect_platform(self):
        if sys.platform.startswith("win"):
            return "windows"
        
        if sys.platform.startswith("linux"):
            return "linux"
        
        return "other"
    
    def apply_main_button_feedbacks(self):
        buttons = [
            self.ui.btn_config,
        ]

        for btn in buttons:
            self.add_button_feedback(btn)
    
    def add_button_feedback(self, button):
        base_style = button.styleSheet().strip()

        feedback_style = """
        QPushButton:hover {
            background-color: rgb(20, 38, 82);
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

    def setup_camera(self):
        # CREAR THREAD Y WORKER DE CAMARA
        self.camera_thread = QThread()
        self.camera_worker = CameraWorker(camera_index=0,width=1920,height=1080,platform=self.platform)

        # MOVER WORKER AL HILO DE VISION
        self.camera_worker.moveToThread(self.camera_thread)

        # INICIAR EL LOOP EN EL WORKER CUANDO SE INICIE EL HILO
        self.camera_thread.started.connect(self.camera_worker.start)

        # CONEXIONES CLAVE
        self.camera_worker.frame_ready.connect(self.update_frame)
        self.camera_worker.finished.connect(self.camera_thread.quit)
        self.camera_worker.finished.connect(self.camera_worker.deleteLater)
        self.camera_worker.focus_check_finished.connect(self.on_focus_check_finished)
        self.camera_worker.focus_check_failed.connect(self.on_focus_check_failed)

        self.camera_thread.start()

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
        puerto = None
        if self.platform == "linux":
            puerto = "/dev/ttyUSB0"
        elif self.platform == "windows":
            puerto = "COM7"

        self.serial_thread = QThread()
        self.serial = SerialComm(port=puerto, baudrate=115200)

        self.serial.moveToThread(self.serial_thread)

        self.serial_thread.started.connect(self.serial.start_listening)

        self.serial.trigger_received.connect(self.run_fsm)
        self.serial.model_received.connect(self.on_model_changed)
        self.serial.esp_result_received.connect(self.on_esp_result_received)
        self.serial.reset_received.connect(self.on_esp_reset_received)
        self.serial_thread.start()

    def setup_state_manager(self):
        # TOOLS
        #REGISTRAR TODAS LAS HERRAMIENTAS POSIBLES EN EL PIPELINE
        #MEJORA: AUTOMATIZAR EL REGISTRO DE HERRAMIENTAS EN LUGAR DE MANUAL - INLCUIR SOLO LAS NECESARIAS SEGUN LAS RECETAS
        tool_registry = {
            "dmtx": DataMatrixTool(),
            "img_hist": CompareImgHistTool()
        }

        # COMPONENTES DEL STATE_MANAGER
        self.camera = Camera()
        self.processor = VisionPipeline(tool_registry)
        self.comm = self.serial

        self.state_manager = StateManager(
            self.camera, 
            self.processor,
            self.comm
        )

        # THREAD + WORKER
        self.state_thread = QThread()
        self.state_worker = StateWorker(self.state_manager)

        self.state_worker.moveToThread(self.state_thread)

        # CONEXIONES
        self.state_thread.finished.connect(self.state_worker.deleteLater)
        self.camera_worker.frame_ready.connect(self.camera.update_frame)

        self.state_manager.inspectionResult.connect(self.on_recipe_result)

        self.state_worker.cycle_finished.connect(self.on_fsm_finished)

            # STATE MANAGER OBTIENE RECIPE MANAGER PARA ACCEDER A LAS RECETAS DESDE EL WORKER
        self.state_manager.set_recipe_manager(self.recipe_manager)
        self.state_manager.load_selected_recipe()
        self.selected_recipe = self.recipe_manager.get_selected()
        self.apply_rois_from_recipe()

        # LOG
        self.state_worker.log.connect(print)

        self.state_thread.start()

    def set_indicator_base(self):
        self.ui.indicator_1.setStyleSheet(self.BASE_STYLE)

    def set_indicator_result_style(self, result):
        if result == "OK":
            self.ui.indicator_1.setStyleSheet(self.OK_STYLE)
        else:
            self.ui.indicator_1.setStyleSheet(self.NG_STYLE)

    def clear_indicator_for_new_cycle(self):
        """
        Limpia el resultado visual anterior cuando comienza un nuevo ciclo valido.
        Esto evita que un NG anterior se borre por tiempo, pero permite que el
        operador vea claramente que una nueva inspeccion inicio.
        """
        self.indicator_epoch += 1
        self.indicator_latched_result = None
        self.last_esp_result = None
        self.set_indicator_base()

    def clear_indicator_from_reset(self):
        """
        Limpia el resultado visual por RESET/llave de calidad recibido desde ESP32/PLC.
        """
        self.indicator_epoch += 1
        self.indicator_latched_result = None
        self.last_esp_result = None
        self.set_indicator_base()

    def update_indicator(self, result, delay=None, latch=False):
        """
        Actualiza el indicador.

        latch=True se usa para resultados finales desde ESP32/PLC.
        En ese modo el color permanece hasta un nuevo ciclo valido o RESET.

        delay se usa solo para avisos locales temporales, por ejemplo errores de
        sistema listo. Un aviso temporal no debe borrar un resultado enclavado.
        """
        result = "OK" if result == "OK" else "NG"

        if latch:
            self.indicator_epoch += 1
            self.indicator_latched_result = result
            self.last_esp_result = result
            self.set_indicator_result_style(result)
            return

        # Si existe un resultado final enclavado de ESP, no lo sobreescribimos
        # con avisos locales temporales. Especialmente protege el NG bloqueante.
        if self.indicator_latched_result is not None:
            return

        self.indicator_epoch += 1
        epoch = self.indicator_epoch

        self.set_indicator_result_style(result)

        if delay is not None and delay > 0:
            QTimer.singleShot(delay, lambda: self.reset_temporary_indicator(epoch))

    def reset_temporary_indicator(self, epoch):
        if epoch != self.indicator_epoch:
            return

        if self.indicator_latched_result is not None:
            return

        self.set_indicator_base()

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

    def is_focus_config_complete(self, focus):
        if not isinstance(focus, dict) or not focus.get("enabled", False):
            return False

        value = focus.get("value")
        min_score = focus.get("min_score")

        if value is None or min_score is None:
            return False

        return True

    def validate_active_recipe_for_production(self):
        recipe = self.selected_recipe or self.recipe_manager.get_selected()

        if not recipe:
            return "No hay receta activa"

        steps = recipe.get("steps")
        if not isinstance(steps, list) or not steps:
            return f"La receta {recipe.get('name')} no tiene steps"

        dmtx_steps = [step for step in steps if step.get("tool") == "dmtx"]

        if self.require_single_dmtx_recipe:
            if len(steps) != 1 or len(dmtx_steps) != 1:
                return "Produccion configurada para una sola receta con un unico step DMTX"

        if not dmtx_steps:
            return "La receta activa no contiene step DMTX"

        step = dmtx_steps[0]
        params = step.get("params", {})

        expected_code = params.get("expected_code")
        if not isinstance(expected_code, str) or not expected_code.strip():
            return "El step DMTX no tiene expected_code valido"

        roi = params.get("roi")
        if not isinstance(roi, (list, tuple)) or len(roi) != 4:
            return "El step DMTX no tiene ROI valida"

        try:
            x1, y1, x2, y2 = [int(float(v)) for v in roi]
        except Exception:
            return f"ROI DMTX invalida: {roi}"

        if x2 <= x1 or y2 <= y1:
            return f"ROI DMTX sin area valida: {roi}"

        return None

    def get_system_ready_error(self):
        if not hasattr(self, "state_thread") or not self.state_thread.isRunning():
            return "State thread no esta corriendo"

        if not hasattr(self, "state_manager") or self.state_manager.state != "IDLE":
            state = self.state_manager.state if hasattr(self, "state_manager") else "NO_STATE_MANAGER"
            return f"FSM ocupada en estado {state}"

        recipe_error = self.validate_active_recipe_for_production()
        if recipe_error:
            return recipe_error

        if not hasattr(self, "camera") or not self.camera.has_fresh_frame(max_age=self.max_frame_age):
            return "No hay frame fresco de camara"

        if self.require_serial_ready:
            if not hasattr(self, "serial") or not self.serial.is_connected():
                return "Serial no conectado"

            if self.require_serial_sync and not self.serial.synced:
                return "Serial sin handshake SYNC_OK"

        return None

    def run_fsm(self):
        if self.fsm_busy:
            print("[FSM] Ciclo ocupado, trigger ignorado")
            return

        if self.focus_check_busy:
            print("[FOCUS] Verificacion/recalibracion de enfoque en proceso, trigger ignorado")
            return

        ready_error = self.get_system_ready_error()
        if ready_error:
            print(f"[SYSTEM][BLOQUEADO] Trigger rechazado: {ready_error}")
            self.update_indicator("NG", delay=1500)
            return

        self.clear_indicator_for_new_cycle()

        if self.should_check_focus_before_trigger():
            self.start_focus_check_before_trigger()
            return

        self.start_fsm_cycle(reset_indicator=False)

    def get_active_focus_config(self):
        recipe = self.selected_recipe or self.recipe_manager.get_selected()

        if not recipe:
            return {}

        focus = recipe.get("focus", {})
        return focus if isinstance(focus, dict) else {}

    def focus_check_is_supported_for_current_platform(self):
        return (
            self.production_focus_required
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

        self.focus_check_busy = True
        self.pending_trigger_after_focus = True
        self.camera_worker.request_focus_check_before_trigger(focus_config)

    def start_fsm_cycle(self, reset_indicator=True):
        if self.fsm_busy:
            print("[FSM] Ciclo ocupado, trigger ignorado")
            return

        ready_error = self.get_system_ready_error()
        if ready_error:
            print(f"[SYSTEM][BLOQUEADO] Ciclo no iniciado: {ready_error}")
            self.fsm_busy = False
            return

        if reset_indicator:
            self.clear_indicator_for_new_cycle()

        self.fsm_busy = True

        if self.state_thread.isRunning():
            QMetaObject.invokeMethod(
                self.state_worker,
                "run_once",
                Qt.QueuedConnection
            )

    def on_fsm_finished(self):
        self.fsm_busy = False
        
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

        self.ui.lbl_model.setText(model_name)

    def open_config(self):
        if self.fsm_busy or self.focus_check_busy or (hasattr(self, "state_manager") and self.state_manager.state != "IDLE"):
            print("[CONFIG][BLOQUEADO] No se puede abrir configuracion durante un ciclo activo")
            return

        self.config_window = ConfigWindow(
            recipe_manager=self.recipe_manager,
            get_frame_callback=self.get_current_frame,
            state_manager=self.state_manager,
            platform=self.platform,
            camera_worker=self.camera_worker
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

        if self.platform == "linux": 
            self.config_window.showFullScreen()
        else:
            self.config_window.resize(480, 320)
            self.config_window.show()

    def request_camera_focus_from_config(self, focus_config):
        print(f"[APP] Solicitud de calibración recibida desde ConfigWindow: {focus_config}")

        if not hasattr(self, "camera_worker") or self.camera_worker is None:
            print("[APP][ERROR] camera_worker no disponible")
            return

        self.camera_worker.request_manual_focus_from_config(focus_config)

    def on_focus_check_finished(self, result):
        print(f"[APP] Resultado verificación enfoque: {result}")

        self.focus_check_busy = False

        if not isinstance(result, dict) or not result.get("ok"):
            print("[APP][ERROR] Verificación de enfoque no válida")
            self.pending_trigger_after_focus = False
            return

        self.focus_ready_for_active_recipe = True
        self.focus_runtime_verified = True

        if result.get("focus_updated") and self.selected_recipe:
            focus_data = {
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
        self.update_indicator("NG", delay=1500)

    def shutdown_thread(self,thread, worker, name="thread"):
        # DETENER WORKERS
        if worker:
            worker.stop()

        # MANEJO SEGURO DEL THREAD
        if thread and thread.isRunning():
            print(f"Esperando thread de {name}")
            thread.quit()

            if not thread.wait(3000):
                print(f"{name} no responde, intentando stop extra...")

                if worker:
                    worker.stop()
                
                if not thread.wait(2000):
                    print(f"Forzando terminate en {name}")
                    thread.terminate()
                    thread.wait()

    def closeEvent(self, event):
        print("Close Event ejecutado")

        self.shutdown_thread(self.camera_thread, self.camera_worker, "camera")
        self.shutdown_thread(self.state_thread, self.state_worker, "state")
        self.shutdown_thread(self.serial_thread, self.serial, "serial")

        print("App cerrada correctamente")
        event.accept()
