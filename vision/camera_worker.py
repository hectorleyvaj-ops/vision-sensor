import cv2
import time
import re
import shutil
import subprocess
import threading

from utils.qt_compat import QObject, Signal, Slot
from vision.manual_focus_controller import ManualFocusController

class CameraWorker(QObject):
    frame_ready = Signal(object)
    cap_ready = Signal(object)
    finished = Signal()
    recalibrate_request = Signal()

    manual_focus_started = Signal()
    manual_focus_finished = Signal(object)
    manual_focus_failed = Signal(str)

    focus_check_started = Signal()
    focus_check_finished = Signal(object)
    focus_check_failed = Signal(str)

    def __init__(self,camera_index=0, width=1920, height=1080, platform="other"):
        super().__init__()
        self.camera_index = camera_index
        
        self.width = width
        self.height = height

        self.cap = None
        self.device = None

        self._running = False
        self.Trigger = False

        self.current_frame = None
        self.frame_for_inspection = None

        self.locked_focus_value = None
        self.calibrating = False

        self.min_focus_score_windows = 350
        self.max_focus_retries_windows = 10

        self.min_focus_score_linux = 350
        self.max_focus_retries_linux = 10

        self.max_focus_freeze_retries_linux = 3

        self.focus_min = 1
        self.focus_max = 1023
        self.focus_step = 1

        # TEMPORAL PARA PRIMERA INTEGRACION Y PRUEBAS
        # DESPUES ESTOS DATOS VENDRAN DE LA RECETA ACTIVA OBTENIDOS DESDE CONFIGURACION
        self.focus_roi = None
        self.focus_value = None
        self.focus_min_score = self.min_focus_score_linux

        self.manual_focus_controller = None

        # DETECTAR SI SE TRABAJA EN WINDOWS(PRUEBAS) O RASPBERRY/LINUX(PRODUCCION)
        self.platform = platform

        self.v4l2_available = False
        self.v4l2_controls = set()
        self.autofocus_supported = False
        self.focus_absolute_supported = False
        self.can_freeze_focus = False

        self.focus_request_lock = threading.Lock()
        self.pending_focus_config = None

        self.pending_focus_check_config = None
        self.focus_reference_score = None
        self.focus_peak_score = None
        self.focus_verify_ratio = 0.70  # UMBRAL DE VALIDACION DE SCORE

        self.recalibrate_request.connect(self.recalibrate_focus)
    
    def is_linux(self):
        return self.platform == "linux"
    
    def is_windows(self):
        return self.platform == "windows"
    
    def find_camera_device(self):
        # SOLO BSUCAMOS EL DEVICE PARA LA RASPBERRY, SI SE TRABAJA EN WIDOWS SE USA CAMERA INDEX 
        if not self.is_linux():
            return self.camera_index
        
        candidates = [
            f"/dev/video{self.camera_index}",
            "/dev/video0",
            "/dev/video1",
            "/dev/video2",
            "/dev/video3",
        ]

        seen = set()

        for dev in candidates:
            if dev in seen:
                continue

            seen.add(dev)

            cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)

            try:
                if not cap.isOpened():
                    continue

                ret,frame = cap.read()

                if ret and frame is not None and hasattr(frame, "shape") and frame.size > 0:
                    print(f"[CAMERA] Dispositivo detectado: {dev}")
                    return dev
            finally:
                cap.release()

        print("[CAMERA] No se encontro ningun dispositivo valido")
        return None
    
    def open_camera(self):
        # INTENTA ABRIR LA CAMARA SEGUN EL SISTEMA DONDE CORRA
        self.device = self.find_camera_device()

        if self.device is None:
            print("[CAMERA] No hay camara disponible")
            return False
        
        if self.is_linux():
            self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        elif self.is_windows():
            self.cap = cv2.VideoCapture(self.device, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(self.device)

        if self.cap is None or not self.cap.isOpened():
            print(f"[CAMERA][ERROR] No se pudo abrir la camara {self.device}")
            return False
        
        self.configure_resolution()

        return True
    
    def configure_resolution(self):
        # INTENTA DEFINIR LA RESOLUCION DADA
        if self.cap is None:
            return
        
        if self.is_linux():
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        for _ in range(5):
            self.cap.read()
            time.sleep(0.03)

        real_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        real_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        real_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[CAMERA] Resolucion solicitada: {self.width} x {self.height}")
        print(f"[CAMERA] Resolucion activa: {real_width} x {real_height}")
        print(f"[CAMERA] FPS activo: {real_fps}")

    def warmup_camera(self, frames=30, delay=0.02):
        # LEE CIERTOS FRAMES PARA ESTABILIZAR CAMARA
        if self.cap is None:
            return
        
        for _ in range(frames):
            if not self._running:
                break

            self.cap.read()
            time.sleep(delay)

    def detect_v4l2_controls(self):
        # INTENTA BUSCAR LOS CONTROLES PARA LA CAMARA SI EL SISTEMA ES LINUX (PRODUCCION)
        self.v4l2_available = False
        self.v4l2_controls = set()
        self.autofocus_supported = False
        self.focus_absolute_supported = False
        self.can_freeze_focus = False

        if not self.is_linux():
            print("[CAMERA] Plataforma Windows/otra: v4l2 no aplica")
            return
        
        if shutil.which("v4l2-ctl") is None:
            print("[CAMERA] v4l2-ctl no esta instalado. Se omitira calibracion avanzada.")
            return
        
        if not isinstance(self.device, str) or not self.device.startswith("/dev/video"):
            print("[CAMERA] Dispositivo Linux invalido para v4l2")
            return
        
        try:
            # COMANDO PARA OBTENER LA LISTA DE CONTROLES
            result = subprocess.run(
                ["v4l2-ctl", "-d", self.device, "--list-ctrls"],
                check=False,
                capture_output=True,
                text=True
            )

            # OBTIENE LA RESPUESTA DEL COMANDO
            output = (result.stdout or "") + "\n" + (result.stderr or "")

            if result.returncode != 0:
                print(f"[CAMERA] No se pudieron extraer los controles v4l2: {output.strip()}")
                return

            # SEPARA LA RESPUESTA EN LINEAS PARA OBTENER LOS CONTROLES DESEADOS
            for line in output.splitlines():
                line = line.strip()

                if not line:
                    continue

                match = re.match(r"^([a-zA-Z0-9_]+)\s", line)

                if match:
                    self.v4l2_controls.add(match.group(1))

            self.v4l2_available = len(self.v4l2_controls) > 0

            self.autofocus_supported = "focus_automatic_continuous" in self.v4l2_controls
            self.focus_absolute_supported = "focus_absolute" in self.v4l2_controls

            self.can_freeze_focus = self.autofocus_supported and self.focus_absolute_supported
            print(f"[CAMERA] Controles v4l2 detectados: {sorted(self.v4l2_controls)}")

            if self.can_freeze_focus:
                print("[CAMERA] Autofocus controlable disponible. Calibracion habilitada")
            else:
                print("[CAMERA][WARNING] Camara sin controles completos de autofocus. Calibracion omitida.")

            self.focus_min, self.focus_max, self.focus_step = self.parse_focus_absolute_range(output)

            print(
                f"[CAMERA] Rango focus_absolute: "
                f"min={self.focus_min}, max={self.focus_max}, step={self.focus_step}"
            )

        except Exception as e:
            print(f"[CAMERA][ERROR] Error detectando controles: {e}")

    def has_v4l2_control(self, control_name):
        return self.v4l2_available and control_name in self.v4l2_controls
        
    def run_v4l2(self, args, check=False, capture_output=True):
        if not self.is_linux():
            raise RuntimeError("[CAMERA][ERROR] v4l2 solo esta disponible para Linux")
        
        if not self.v4l2_available:
            raise RuntimeError("[CAMERA][ERROR] v4l2 no esta disponible")
        
        if self.device is None:
            raise RuntimeError("[CAMERA][ERROR] No hay dispositivo valido")
        
        cmd = ["v4l2-ctl", "-d", self.device] + args

        print(f"[V4L2][CMD] {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        print(f"[V4L2][RC] {result.returncode}")

        if stdout:
            print(f"[V4L2][OUT] {stdout}")

        if stderr:
            print(f"[V4L2][ERR] {stderr}")

        if check and result.returncode != 0:
            raise RuntimeError(f"Comando v4l2 falló: {' '.join(cmd)}")

        return result
        
    # API GENERAL PARA SETEAR CONTROLES
    def set_v4l2_controls(self, control_name, value, check=False, verify=True):
        if not self.has_v4l2_control(control_name):
            print(f"[CAMERA][WARNING] Control no disponible, omitido: {control_name}")
            return False
        
        try:
            result = self.run_v4l2(
                [f"--set-ctrl={control_name}={value}"],
                check=check,
                capture_output=True
            )

            if result.returncode != 0:
                print(f"[CAMERA][ERROR] v4l2 rechazó {control_name}={value}")
                return False

            if verify:
                actual = self.get_v4l2_control(control_name)
                print(f"[CAMERA] Control aplicado/verificado: {control_name} pedido={value}, leído={actual}")

            else:
                print(f"[CAMERA] Control aplicado: {control_name}={value}")

            return True
        
        except Exception as e:
            print(f"[CAMERA][ERROR] Error aplicando {control_name}={value}: {e}")
            return False
        
    # API GENERAL PARA OBTENER EL VALOR DE LOS CONTROLES
    def get_v4l2_control(self, control_name):
        if not self.has_v4l2_control(control_name):
            return None

        try:
            result = self.run_v4l2(
                [f"--get-ctrl={control_name}"],
                check=False,
                capture_output=True
            )

            if result.returncode != 0:
                output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
                print(f"[CAMERA][WARNING] No se pudo leer {control_name}: {output}")
                return None

            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
            match = re.search(rf"{re.escape(control_name)}\s*:\s*(-?\d+)", output)

            if not match:
                match = re.search(r"(-?\d+)\s*$", output)

            if match:
                return int(match.group(1))
            
            print(f"[CAMERA][WARNING] No se pudo leer {control_name}: {output}")
            return None
        
        except Exception as e:
            print(f"[CAMERA][ERROR] Error leyendo {control_name}: {e}")
            return None
        
    def set_autofocus_linux(self, enabled):
        if not self.autofocus_supported:
            print("[CAMERA][WARNING] Control focus_automatic_continuous no disponible, se omite")
            return True

        value = 1 if enabled else 0
        return self.set_v4l2_controls("focus_automatic_continuous", value)
    
    def set_autofocus_windows(self, enabled):
        try:
            if self.cap is None:
                return False

            value = 1 if enabled else 0
            ok = self.cap.set(cv2.CAP_PROP_AUTOFOCUS, value)

            if ok:
                print(f"[CAMERA] Autofocus en windows {'activado' if enabled else 'desactivado'}")

            else:
                print("[CAMERA][WARNING] No se pudo cambiar autofocus Windows")

            return ok

        except Exception as e:
            print(f"[CAMERA][ERROR] Error cambiando focus en Windows: {e}")
            return False
    
    # INTENTA OBTENER EL VALOR DEL FOCO PARA WINDOWS(PRUEBAS)
    def get_focus_windows(self):
        try:
            if self.cap is None:
                return None
            
            value = self.cap.get(cv2.CAP_PROP_FOCUS)
            
            if value is None or value < 0:
                return None

            return int(value)
        
        except Exception as e:
            print(f"[CAMERA][ERROR] Error leyendo foco en Windows: {e}")
            return None
    
    def get_focus_absolute(self):
        return self.get_v4l2_control("focus_absolute")
    
    def set_focus_absolute(self, value):
        if not self.focus_absolute_supported:
            return False
        
        if value is None:
            return False

        value = int(max(self.focus_min, min(self.focus_max, value)))
        return self.set_v4l2_controls("focus_absolute", value)
    
    def set_focus_windows(self, value):
        try:
            if self.cap is None or value is None:
                return False

            ok  = self.cap.set(cv2.CAP_PROP_FOCUS, value)

            if ok:
                print(f"[CAMERA] Foco Windows aplicado: {value}")

            else:
                print(f"[CAMERA] No se pudo aplicar foco Windows: {value}")

            return ok

        except Exception as e:
            print(f"[CAMERA][ERROR] Error aplicando foco en Windows: {e}")
            return False
    
    def apply_base_controls_linux(self):
        if not self.is_linux() or not self.v4l2_available:
            return

        optional_controls = {
            "auto_exposure": 3,
            "exposure_dynamic_framerate": 1,
            "gain": 10,
            "brightness": 0,
            "contrast": 32,
            "sharpness": 3,
            "power_line_frequency": 1,
            "white_balance_automatic": 1,
        }

        for control, value in optional_controls.items():
            if self.has_v4l2_control(control):
                self.set_v4l2_controls(control, value, verify=False)

        if self.autofocus_supported:
            self.set_autofocus_linux(False)

    def apply_base_controls_windows(self):
        if self.cap is None:
            return

        try:
            ok_autofocus = self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            if ok_autofocus:
                print("[CAMERA] Autofocus OpenCV activado en Windows")
            else:
                print("[CAMERA][WARNING] Autofocus OpenCV no disponible en esta cámara/backend")

        except Exception as e:
            print(f"[CAMERA][ERROR] Error activando autofocus OpenCV: {e}")

        try:
            self.cap.set(cv2.CAP_PROP_ZOOM, 0.0)
        except Exception:
            pass

    def apply_base_controls(self):
        if self.is_linux():
            self.detect_v4l2_controls()
            self.apply_base_controls_linux()

        elif self.is_windows():
            self.apply_base_controls_windows()

    def focus_score(self, frame, roi=None):
        return ManualFocusController.focus_score(frame, roi)
        
    def verify_frozen_focus(self, expected_focus=None, min_score=None, samples=12, delay=0.04, focus_tolerance=3):
        if min_score is None:
            min_score = self.min_focus_score_linux if self.is_linux() else self.min_focus_score_windows

        best_score = -1
        best_frame = None


        for _ in range(samples):
            if not self._running:
                break

            ret, frame = self.cap.read()

            if not ret or frame is None or not hasattr(frame, "shape") or frame.size == 0:
                time.sleep(delay)
                continue

            score = self.focus_score(frame)

            self.current_frame = frame.copy()
            self.frame_ready.emit(frame.copy())

            if score > best_score:
                best_score = score
                best_frame = frame.copy()

            time.sleep(delay)

        current_focus = None

        if self.is_linux():
            current_focus = self.get_focus_absolute()
        elif self.is_windows():
            current_focus = self.get_focus_windows()

        focus_ok = True

        if expected_focus is not None and current_focus is not None:
            focus_ok = abs(current_focus - expected_focus)<=focus_tolerance

        score_ok = best_score >= min_score

        print(
            f"[CAMERA] Verificación foco congelado: "
            f"score={best_score}, min_score={min_score}, "
            f"focus={current_focus}, expected={expected_focus}, "
            f"score_ok={score_ok}, focus_ok={focus_ok}"
        )

        return score_ok and focus_ok, best_score, current_focus, best_frame
        
    def autofocus_calibration_windows(self):
        self.calibrating = True
        try:
            if self.cap is None or not self.cap.isOpened():
                return None, -1, None

            print("[CAMERA] Iniciando calibración Windows con OpenCV")

            if not self.set_autofocus_windows(True):
                print("[CAMERA] Calibración Windows omitida: autofocus no controlable")
                return None, -1, None

            self.emit_preview_during_focus(seconds=3.0, interval=0.03)

            best_score = -1
            best_frame = None
            best_focus_value = None

            for _ in range(100):
                if not self._running:
                    break

                ret, frame = self.cap.read()

                if not ret or frame is None or not hasattr(frame, "shape") or frame.size == 0:
                    time.sleep(0.03)
                    continue

                score = self.focus_score(frame)
                focus_value = self.get_focus_windows()

                self.current_frame = frame.copy()
                self.frame_ready.emit(frame.copy())

                if score > best_score:
                    best_score = score
                    best_frame = frame.copy()
                    best_focus_value = focus_value

                time.sleep(0.02)

            if best_focus_value is None:
                best_focus_value = self.get_focus_windows()

            print(f"[CAMERA] Mejor score Windows: {best_score}, focus={best_focus_value}")
            return best_frame, best_score, best_focus_value

        except Exception as e:
            print(f"[CAMERA] Error en calibración Windows: {e}")
            return None, -1, None
        
        finally:
            self.calibrating = False

    def reset_autofocus_windows_for_retry(self):
        try:
            print("[CAMERA] Reiniciando autofocus Windows para nuevo intento")

            # No forzamos CAP_PROP_FOCUS aquí porque en Windows el rango puede variar
            # mucho entre cámaras/backends. Solo reiniciamos el autofocus.
            self.set_autofocus_windows(True)
            time.sleep(0.4)

            self.emit_preview_during_focus(seconds=1.0, interval=0.03)

        except Exception as e:
            print(f"[CAMERA][WARNING] No se pudo reiniciar autofocus Windows: {e}")

    def emit_preview_during_focus(self, seconds=3.0, interval=0.03):
        deadline = time.time() + seconds

        while self._running and time.time() < deadline:
            ret, frame = self.cap.read()

            if ret and frame is not None and hasattr(frame, "shape") and frame.size > 0:
                self.current_frame = frame.copy()
                self.frame_ready.emit(frame.copy())

            time.sleep(interval)

    def autofocus_calibration_windows_with_retries(self):
        best_global_frame = None
        best_global_score = -1
        best_global_focus = None

        for attempt in range(1, self.max_focus_retries_windows + 1):
            print(f"[CAMERA] Intento autofocus Windows {attempt}/{self.max_focus_retries_windows}")

            best_frame, score, focus_value = self.autofocus_calibration_windows()

            if score > best_global_score:
                best_global_score = score
                best_global_frame = best_frame
                best_global_focus = focus_value

            if focus_value is not None and score > self.min_focus_score_windows:
                print(f"[CAMERA] Enfoque windows aceptado score={score}, focus={focus_value}")
                return best_frame, score, focus_value
            
            print(
            f"[CAMERA][WARNING] Enfoque bajo o foco inválido. "
            f"score={score}, focus={focus_value}. Reintentando..."
            )

            self.reset_autofocus_windows_for_retry()

        print(
        f"[CAMERA][ERROR] No se alcanzó score mínimo Windows. "
        f"Mejor score={best_global_score}, focus={best_global_focus}"
        )

        return best_global_frame, best_global_score, best_global_focus

    def freeze_camera_windows(self, focus_value=None):
        try:
            if focus_value is None:
                focus_value = self.get_focus_windows()

            if focus_value is None:
                print("[CAMERA] No se pudo obtener valor de foco Windows para congelar")
                return None
            
            self.set_autofocus_windows(False)
            time.sleep(0.3)
            
            if not self.set_focus_windows(focus_value):
                return None

            time.sleep(0.3)

            verified = self.get_focus_windows()

            if verified is None:
                verified = focus_value

            self.locked_focus_value = verified
            print(f"[CAMERA] Foco windows congelado en {verified}")

            return verified

        except Exception as e:
            print(f"[CAMERA][ERROR] Error congelando foco windows: {e}")
            return None
        
    @Slot()
    def recalibrate_focus(self):
        if self.calibrating:
            print("[CAMERA][WARNING] Ya hay una calibración en proceso")
            return

        print("[CAMERA] Recalibrando enfoque...")

        
        if self.is_windows():
            best_frame, score, focus_value = self.autofocus_calibration_windows_with_retries()

            if focus_value is None:
                print("[CAMERA][WARNING] Windows: recalibración sin foco válido, se deja autofocus activo")
                self.set_autofocus_windows(True)
                return

            if score < self.min_focus_score_windows:
                print(
                    f"[CAMERA][WARNING] Windows: score bajo en recalibración ({score}). "
                    "No se congela foco; se deja autofocus activo."
                )
                self.set_autofocus_windows(True)
                return

            locked = self.freeze_camera_windows(focus_value)

            if locked is None:
                print("[CAMERA][WARNING] Windows: no se pudo congelar recalibración, se deja autofocus activo")
                self.set_autofocus_windows(True)
            else:
                print(f"[CAMERA] Windows recalibrado score={score}, focus={locked}")

            return

        if self.is_linux():
            if not self.focus_absolute_supported:
                print("[CAMERA][WARNING] Linux: focus_absolute no disponible. Recalibración omitida.")
                return

            self.apply_base_controls_linux()
            self.warmup_camera(frames=20, delay=0.02)

            result = self.manual_focus_calibration_linux(roi=self.focus_roi)

            if result is None or not result.ok:
                print("[CAMERA][ERROR] Linux: recalibración manual falló.")
                return

            print(
                f"[CAMERA] Linux recalibrado con autofocus manual: "
                f"focus={result.focus_value}, "
                f"score={result.median_score}, "
                f"min_score={result.min_score}"
            )

            return

        print("[CAMERA][WARNING] Recalibración no disponible en esta plataforma")

    def initial_focus_setup(self):
        if self.is_windows():
            best_frame, score, focus_value = self.autofocus_calibration_windows_with_retries()

            if focus_value is None:
                print("[CAMERA] Windows: no se pudo obtener foco, se deja autofocus activo")
                self.set_autofocus_windows(True)
                return
            
            if score < self.min_focus_score_windows:
                print(
                    f"[CAMERA][WARNING] Windows: score bajo ({score}). "
                    "No se congela foco; se deja autofocus activo."
                )
                self.set_autofocus_windows(True)
                return
            
            locked = self.freeze_camera_windows(focus_value)

            if locked is None:
                print("[CAMERA] Windows: no se pudo congelar foco, se deja funcionamiento normal")
                self.set_autofocus_windows(True)
            else:
                print(f"[CAMERA] Windows FOCUS CALIBRADO SCORE: {score}, FOCUS: {locked}")

            return
        
        if not self.is_linux():
            print("[CAMERA] Plataforma no Linux: se omite calibración avanzada")
            return

        if not self.focus_absolute_supported:
            print("[CAMERA][WARNING] Linux: focus_absolute no disponible. Se usará video sin enfoque manual.")
            return
        
        if self.autofocus_supported:
            self.set_autofocus_linux(False)

        print("[CAMERA] Linux: enfoque manual listo. La verificación se hará en el primer trigger.")
        return


    # NUEVA INTEGRACION DE METODOS PARA MANUAL_FOCUS_CONTROLLER
    def parse_focus_absolute_range(self, list_ctrls_output):
        if not isinstance(list_ctrls_output, str):
            return 1, 1023, 1

        for line in list_ctrls_output.splitlines():
            if "focus_absolute" not in line:
                continue

            min_match = re.search(r"min=(-?\d+)", line)
            max_match = re.search(r"max=(-?\d+)", line)
            step_match = re.search(r"step=(-?\d+)", line)

            if min_match and max_match:
                focus_min = int(min_match.group(1))
                focus_max = int(max_match.group(1))
                focus_step = int(step_match.group(1)) if step_match else 1
                return focus_min, focus_max, max(1, focus_step)
            
        return 1, 1023, 1
    
    def emit_focus_frame(self, frame):
        try:
            if frame is None:
                return
            
            self.current_frame = frame.copy()
            self.frame_ready.emit(frame.copy())

        except Exception as e:
            print(f"[CAMERA][WARNING] No se pudo emitir frame de enfoque: {e}")

    def get_manual_focus_controller(self):
        if self.manual_focus_controller is not None:
            return self.manual_focus_controller
        

        if self.cap is None or not self.cap.isOpened():
            print("[CAMERA][ERROR] No hay camara abierta para autofocus manual")
            return None
        
        self.manual_focus_controller = ManualFocusController(
            cap=self.cap,
            set_focus_absolute=self.set_focus_absolute,
            get_focus_absolute=self.get_focus_absolute,
            set_autofocus=self.set_autofocus_linux,
            emit_frame=self.emit_focus_frame,
            is_running=lambda:self._running,
            focus_min=self.focus_min,
            focus_max=self.focus_max,
            focus_step=self.focus_step,
        )

        return self.manual_focus_controller
    
    def manual_focus_calibration_linux(self, roi=None):
        if not self.is_linux():
            print("[CAMERA][WARNING] Autofocus maual linux omitido: plataforma no Linux")
            return None
        
        if not self.focus_absolute_supported:
            print("[CAMERA][WARNING] Autofocus manual omitido: focus_absolute no disponible")
            return None
        
        controler = self.get_manual_focus_controller()

        if controler is None:
            return None
        
        self.calibrating = True

        try:
            focus_roi = roi if roi is not None else self.focus_roi

            result = controler.calibrate(
                roi = focus_roi,
                coarse_step=100,
                fine_span=60,
                fine_step=20,
                micro_span=15,
                micro_step=3,
                min_score_ratio=0.65,
            )

            if result is not None and result.ok:
                self.focus_value = result.focus_value
                self.locked_focus_value = result.focus_value
                self.focus_min_score = result.min_score

                print(
                    f"[CAMERA] Autofocus manual Linux OK: "
                    f"focus={result.focus_value}, "
                    f"score={result.median_score}, "
                    f"min_score={result.min_score}"
                )

            else: 
                print("[CAMERA][WARNING] Autofocus manual Linux no logro enfoque valido")

            return result
        
        except Exception as e:
            print(f"[CAMERA][ERROR] Error en autofocus manual Linux: {e}")
            return None
        
        finally:
            self.calibrating = False

    def verify_manual_focus_linux(self, focus_value=None, roi=None, min_score=None, apply_value=True):
        if not self.is_linux():
            return False

        controller = self.get_manual_focus_controller()

        if controller is None:
            return False

        focus_value = self.focus_value if focus_value is None else focus_value
        focus_roi = self.focus_roi if roi is None else roi
        min_score = self.focus_min_score if min_score is None else min_score

        if focus_value is None:
            print("[CAMERA][WARNING] No hay focus_value guardado para verificar")
            return False

        ok, median_score, peak_score = controller.verify_focus(
            focus_value=focus_value,
            roi=focus_roi,
            min_score=min_score,
            samples=12,
            delay=0.04,
            apply_value=apply_value,
        )

        print(
            f"[CAMERA] Verificación autofocus manual: "
            f"ok={ok}, focus={focus_value}, "
            f"median_score={median_score}, peak_score={peak_score}, "
            f"min_score={min_score}"
        )

        return ok
    
    # CARGAR ENFOQUE DESDE RECETA MAS ADELANTE
    @Slot()
    def set_focus_from_recipe(self, focus_config):
        if not isinstance(focus_config, dict) or not focus_config.get("enabled", False):
            self.focus_roi = None
            self.focus_value = None
            self.focus_min_score = self.min_focus_score_linux
            self.focus_reference_score = None
            self.focus_peak_score = None
            print("[CAMERA] Receta sin configuración de enfoque habilitada")
            return
        
        roi = focus_config.get("roi")
        value = focus_config.get("value")
        min_score = focus_config.get("min_score")
        median_score = focus_config.get("median_score")
        peak_score = focus_config.get("peak_score")

        self.focus_roi = tuple(roi) if roi and len(roi) == 4 else None
        self.focus_value = int(value) if value is not None else None
        self.focus_min_score = int(min_score) if min_score is not None else self.min_focus_score_linux
        self.focus_reference_score = int(median_score) if median_score is not None else None
        self.focus_peak_score = int(peak_score) if peak_score is not None else None

        print(
            f"[CAMERA] Focus config cargada: "
            f"roi={self.focus_roi}, value={self.focus_value}, "
            f"min_score={self.focus_min_score}, "
            f"reference_score={self.focus_reference_score}, "
            f"peak_score={self.focus_peak_score}"
        )

    def get_focus_required_score(self):
        candidates = [self.min_focus_score_linux]

        if self.focus_min_score is not None:
            candidates.append(int(self.focus_min_score))

        if self.focus_reference_score is not None:
            candidates.append(int(self.focus_reference_score * self.focus_verify_ratio))

        required = max(candidates)

        print(
            f"[CAMERA] Umbral enfoque requerido: {required} "
            f"(min_score={self.focus_min_score}, "
            f"reference_score={self.focus_reference_score}, "
            f"ratio={self.focus_verify_ratio})"
        )

        return required
    
    def request_focus_check_before_trigger(self, focus_config=None):
        print(f"[CAMERA] Solicitud de verificación de enfoque encolada: {focus_config}")

        with self.focus_request_lock:
            self.pending_focus_check_config = focus_config

    def consume_pending_focus_check_config(self):
        with self.focus_request_lock:
            config = self.pending_focus_check_config
            self.pending_focus_check_config = None

        return config
    
    def process_pending_focus_check_request(self):
        focus_config = self.consume_pending_focus_check_config()

        if focus_config is None:
            return
        
        print(f"[CAMERA] Procesando verificación de enfoque desde loop: {focus_config}")
        self.ensure_focus_ready_for_trigger(focus_config)

    def request_manual_focus_from_config(self, focus_config):
        print(f"[CAMERA] Solicitud manual focus encolada: {focus_config}")

        with self.focus_request_lock:
            self.pending_focus_config = focus_config

    def consume_pending_focus_config(self):
        with self.focus_request_lock:
            config = self.pending_focus_config
            self.pending_focus_config = None

        return config
    
    def process_pending_focus_request(self):
        focus_config = self.consume_pending_focus_config()

        if focus_config is None:
            return
        
        print(f"[CAMERA] Procesando solicitud de enfoque desde el loop: {focus_config}")

        self.calibrate_focus_from_config(focus_config)
    
    # ESTE METODO PERMITE RECIBIR UN ROI DE LA VENTANA DE CALIBRACION:
    # {
    #   "roi": [833, 224, 1217, 577]
    # }
    @Slot(object)
    def calibrate_focus_from_config(self, focus_config):
        print(f"[CAMERA] Slot calibrate_focus_from_config recibido: {focus_config}")

        if self.calibrating:
            self.manual_focus_failed.emit("Ya hay una calibracion en proceso.")
            return
        
        if not self.is_linux():
            self.manual_focus_failed.emit("Calibracion manua solo para linux")
            return

        if not self.focus_absolute_supported:
            self.manual_focus_failed.emit("La camara no expone focus_absolute")
            return
        
        try:
            self.manual_focus_started.emit()

            roi = None

            if isinstance(focus_config, dict):
                raw_roi = focus_config.get("roi")

                if raw_roi and len(raw_roi) == 4:
                    roi = tuple(raw_roi)

            print(f"[CAMERA] Iniciando calibración desde configuración con ROI: {roi}")
            result = self.manual_focus_calibration_linux(roi=roi)

            if result is None or not result.ok:
                self.manual_focus_failed.emit("No se pudo calibrar el enfoque manual.")
                return

            result_data = {
                "ok": True,
                "roi": list(result.roi) if result.roi is not None else None,
                "focus_value": int(result.focus_value),
                "median_score": int(result.median_score),
                "peak_score": int(result.peak_score),
                "min_score": int(result.min_score),
                "coarse_best": int(result.coarse_best) if result.coarse_best is not None else None,
                "fine_best": int(result.fine_best) if result.fine_best is not None else None,
                "micro_best": int(result.micro_best) if result.micro_best is not None else None,
            }

            print(f"[CAMERA] Calibración desde configuración terminada: {result_data}")
            self.manual_focus_finished.emit(result_data)

        except Exception as e:
            print(f"[CAMERA][ERROR] calibrate_focus_from_config: {e}")
            self.manual_focus_failed.emit(str(e))

    def ensure_focus_ready_for_trigger(self, focus_config=None):
        if self.calibrating:
            self.focus_check_failed.emit("Ya hay una calibracion en proceso")
            return
        
        if not self.is_linux():
            self.focus_check_finished.emit({
                "ok": True,
                "skipped": True,
                "reason": "Verificación manual omitida fuera de Linux"
            })
            return
    
        if not self.focus_absolute_supported:
            self.focus_check_failed.emit("La camara no expone focus_absolute")
            return
        
        try:
            self.focus_check_started.emit()

            if isinstance(focus_config, dict):
                self.set_focus_from_recipe(focus_config)

            verified_score = None
            verified_peak = None

            if self.focus_value is not None:
                required_score = self.get_focus_required_score()
                controller = self.get_manual_focus_controller()

                if controller is None:
                    self.focus_check_failed.emit("No se pudo crear ManualFocusController")
                    return
                
                ok, median_score, peak_score = controller.verify_focus(
                    focus_value=self.focus_value,
                    roi=self.focus_roi,
                    min_score=required_score,
                    samples=12,
                    delay=0.04,
                    apply_value=True,
                )

                verified_score = median_score
                verified_peak = peak_score

                print(
                    f"[CAMERA] Verificación previa al trigger: "
                    f"ok={ok}, focus={self.focus_value}, "
                    f"score={median_score}, peak={peak_score}, "
                    f"required={required_score}"
                )
                
                if ok:
                    self.focus_check_finished.emit({
                        "ok": True,
                        "focus_updated": False,
                        "focus_value": self.focus_value,
                        "roi": list(self.focus_roi) if self.focus_roi is not None else None,
                        "median_score": median_score,
                        "peak_score": peak_score,
                        "min_score": required_score,
                    })
                    return
                print("[CAMERA][WARNING] Score bajo. Recalibrando enfoque manual...")

            else:
                print("[CAMERA][WARNING] No hay focus_value guardado. Recalibrando antes del trigger...")

            result = self.manual_focus_calibration_linux(roi=self.focus_roi)

            if result is None or not result.ok:
                self.focus_check_failed.emit("No se pudo verificar ni recalibrar el enfoque.")
                return

            result_data = {
                "ok": True,
                "focus_updated": True,
                "roi": list(result.roi) if result.roi is not None else None,
                "focus_value": int(result.focus_value),
                "median_score": int(result.median_score),
                "peak_score": int(result.peak_score),
                "min_score": int(result.min_score),
                "coarse_best": int(result.coarse_best) if result.coarse_best is not None else None,
                "fine_best": int(result.fine_best) if result.fine_best is not None else None,
                "micro_best": int(result.micro_best) if result.micro_best is not None else None,
                "previous_score": verified_score,
                "previous_peak_score": verified_peak,
            }

            print(f"[CAMERA] Enfoque listo para trigger: {result_data}")
            self.focus_check_finished.emit(result_data)

        except Exception as e:
            print(f"[CAMERA][ERROR] ensure_focus_ready_for_trigger: {e}")
            self.focus_check_failed.emit(str(e))


    @Slot()
    def start(self):
        # LOOP PRINCIPAL DE CAPTURA
        self._running = True
        
        try:
            if not self.open_camera():
                print("[CAMERA][ERROR] No se pudo abrir la camara")
                self._running = False
                self.finished.emit()
                return
            
            self.apply_base_controls()
            self.warmup_camera(frames=40, delay=0.02)
            self.initial_focus_setup()

            last_emit = time.time()
            emit_interval = 1 / 30

            while self._running:
                self.process_pending_focus_request()
                self.process_pending_focus_check_request()

                if self.calibrating:
                    time.sleep(0.01)
                    continue
                
                ret, frame = self.cap.read()

                if not ret or frame is None or not hasattr(frame, "shape") or frame.size == 0:
                    time.sleep(0.005)
                    continue
                
                self.current_frame = frame
                now = time.time()

                if now - last_emit >= emit_interval:
                    self.frame_ready.emit(frame.copy())
                    last_emit = now

                time.sleep(0.001)

        except Exception as e:
            print(f"[CAMERA][ERROR] Error en camara: {e}")

        finally:
            print("[CAMERA] Liberando camara...")

            try:
                if self.cap:
                    self.cap.release()
            except Exception as e:
                print(f"[CAMERA][ERROR] Error liberando camara: {e}")

            print("[CAMERA] Worker terminado")
            self.finished.emit()

    @Slot()
    def stop(self):
        print("[CAMERA] solicitud de cierre")
        self._running = False

        if self.cap is not None:
            print("[CAMERA] Forzando liberacion de camara desde stop")
            self.cap.release()