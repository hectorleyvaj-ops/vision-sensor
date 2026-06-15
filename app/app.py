import sys
import cv2
# IMPORTS DE QT
from utils.qt_compat import load_ui, QT_LIB, QThread, QImage, QPixmap, QMainWindow, QMetaObject, Qt, QTimer
# IMPORTS DE UI
from ui.ui_main_window import Ui_MainWindow
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

        print(f"Qt backend: {QT_LIB}")

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

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

        self.current_frame = None
        self.selected_recipe = None
        self.rois_to_apply = []

        self.fsm_busy = False

        self.BASE_STYLE = """
        border: 2px solid;
        font-size: 16px;
        border-radius: 17px;
        border-color: rgb(46, 196, 182);
        color: rgb(46, 196, 182);
        background-color: rgb(15, 27, 61);
        """

        self.OK_STYLE = """
        border: 2px solid;
        font-size: 16px;
        border-radius: 17px;
        border-color: rgb(0, 200, 0);
        color: rgb(0, 200, 0);
        background-color: rgb(15, 27, 61);
        """

        self.NG_STYLE = """
        border: 2px solid;
        font-size: 16px;
        border-radius: 17px;
        border-color: rgb(220, 50, 50);
        color: rgb(220, 50, 50);
        background-color: rgb(15, 27, 61);
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

        self.state_manager.inspectionResult.connect(self.update_indicator)

        self.state_worker.cycle_finished.connect(self.on_fsm_finished)

            # STATE MANAGER OBTIENE RECIPE MANAGER PARA ACCEDER A LAS RECETAS DESDE EL WORKER
        self.state_manager.set_recipe_manager(self.recipe_manager)
        self.state_manager.load_selected_recipe()
        self.selected_recipe = self.recipe_manager.get_selected()
        self.apply_rois_from_recipe()

        # LOG
        self.state_worker.log.connect(print)

        self.state_thread.start()

    def update_indicator(self, result, delay=1000):
        if result == "OK":
            self.ui.indicator_1.setStyleSheet(self.OK_STYLE)
        else:
            self.ui.indicator_1.setStyleSheet(self.NG_STYLE)

        QTimer.singleShot(delay, lambda: self.ui.indicator_1.setStyleSheet(self.BASE_STYLE))

    def run_fsm(self):
        if self.fsm_busy:
            print("[FSM] Ciclo ocupado, trigger ignorado")
            return
        
        if not self.state_thread.isRunning():
            print("[FSM] State thread no esta corriendo")
            return
        
        if self.state_manager.state != "IDLE":
            print(f"[FSM] Ocupada en estado {self.state_manager.state}, trigger ignorado")
            return
        
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
            
        print(f"Cambiando receta a modelo: {model_name}")
        self.state_manager.set_active_recipe(model_name)
        self.apply_rois_from_recipe()
        self.ui.lbl_model.setText(model_name)

    def open_config(self):
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

