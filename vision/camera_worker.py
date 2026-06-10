import cv2
import time
import re
import shutil
import subprocess

from utils.qt_compat import QObject, Signal, QTimer, Slot

class CameraWorker(QObject):
    frame_ready = Signal(object)
    cap_ready = Signal(object)
    finished = Signal()
    recalibrate_request = Signal()

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
        self.max_focus_retries_windows = 5

        self.min_focus_score_linux = 350
        self.max_focus_retries_linux = 5

        # DETECTAR SI SE TRABAJA EN WINDOWS(PRUEBAS) O RASPBERRY/LINUX(PRODUCCION)
        self.platform = platform

        self.v4l2_available = False
        self.v4l2_controls = set()
        self.autofocus_supported = False
        self.focus_absolute_supported = False
        self.can_freeze_focus = False

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

            self.can_freeze_focus = self.autofocus_supported

            print(f"[CAMERA] Controles v4l2 detectados: {sorted(self.v4l2_controls)}")

            if self.can_freeze_focus:
                print("[CAMERA] Autofocus controlable disponible. Calibracion habilitada")
            else:
                print("[CAMERA][WARNING] Camara sin controles completos de autofocus. Calibracion omitida.")

        except Exception as e:
            print(f"[CAMERA][ERROR] Error detectando controles: {e}")

    def has_v4l2_control(self, control_name):
        return self.v4l2_available and control_name in self.v4l2_controls
        
    def run_v4l2(self, args, check=True, capture_output=False):
        if not self.is_linux():
            raise RuntimeError("[CAMERA][ERROR] v4l2 solo esta disponible para Linux")
        
        if not self.v4l2_available:
            raise RuntimeError("[CAMERA][ERROR] v4l2 no esta disponible")
        
        if self.device is None:
            raise RuntimeError("[CAMERA][ERROR] No hay dispositivo valido")
        
        cmd = ["v4l2-ctl", "-d", self.device] + args

        if capture_output:
            return subprocess.run(cmd, check=check, capture_output=True, text=True)
        
        return subprocess.run(
            cmd,
            check=check,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    
    # API GENERAL PARA SETEAR CONTROLES
    def set_v4l2_controls(self, control_name, value, check=False):
        if not self.has_v4l2_control(control_name):
            print(f"[CAMERA][WARNING] Control no disponible, omitido: {control_name}")
            return False
        
        try:
            self.run_v4l2([f"--set-ctrl={control_name}={value}"], check=check)
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


            output = (result.stdout or result.stderr or "").strip()
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
            return False

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

        value = int(max(1, min(1023, value)))
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
                self.set_v4l2_controls(control, value)

        if self.autofocus_supported:
            self.set_autofocus_linux(True)

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

    def focus_score(self, frame):
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return int(cv2.Laplacian(gray, cv2.CV_64F).var())
        
        except Exception:
            return -1
        
    def wait_focus_stable(self, stable_samples=8, max_seconds=8.0, focus_delta=2):
        if not self.can_freeze_focus:
            return None
        
        last_focus = None
        stable_count = 0
        deadline = time.time() + max_seconds

        while self._running and time.time() < deadline:
            ret, frame = self.cap.read()

            if not ret or frame is None or not hasattr(frame, "shape") or frame.size == 0:
                time.sleep(0.05)
                continue

            current_focus = self.get_focus_absolute()

            if current_focus is None:
                time.sleep(0.05)
                continue

            if last_focus is not None and abs(current_focus - last_focus) <= focus_delta:
                stable_count += 1

            else:
                stable_count = 0

            last_focus = current_focus

            self.current_frame = frame.copy()
            self.frame_ready.emit(frame.copy())


            if stable_count >= stable_samples:
                print(f"[CAMERA] Foco estable detectado: {current_focus}")
                return current_focus
            
            time.sleep(0.05)

        print(f"[CAMERA] Estabilidad no confirmada, ultimo foco: {last_focus}")
        return last_focus
    
    def autofocus_calibration(self):
        self.calibrating = True

        best_score = -1
        best_frame = None

        invalid_frames = 0
        max_invalid_frames = 10

        try:
            if not self.autofocus_supported:
                print("[CAMERA][WARNING] Calibración omitida: cámara sin autofocus")
                return None, -1, None

            if self.cap is None or not self.cap.isOpened():
                print("[CAMERA] Cámara no disponible para calibración")
                return None, -1, None

            print("[CAMERA] Iniciando autofocus...")
            self.set_autofocus_linux(True)

            # TIEMPO PARA QUE LA CAMARA INTENTE ENFOCAR
            self.emit_preview_during_focus(seconds=3.0, interval=0.03)

            for _ in range(100):
                if not self._running:
                    break

                ret, frame = self.cap.read()

                if not ret or frame is None or not hasattr(frame, "shape") or frame.size == 0:
                    invalid_frames += 1
                    print(f"[CAMERA][WARNING] Frame inválido durante calibración ({invalid_frames})")

                    if invalid_frames >= max_invalid_frames:
                        print("[CAMERA][ERROR] Demasiados frames inválidos durante calibración")
                        return None, -1

                    time.sleep(0.03)
                    continue

                # USANDO LAPLACE CON CV2
                score = self.focus_score(frame)

                self.current_frame = frame.copy()
                self.frame_ready.emit(frame.copy())

                if score > best_score:
                    best_score = score
                    best_frame = frame.copy()

                time.sleep(0.03)

            print(f"[CAMERA] Mejor score enfoque: {best_score}")
            return best_frame, best_score
        
        except Exception as e:
            print(f"[CAMERA] Error en calibración Linux: {e}")
            return None, -1, None

        finally:
            self.calibrating = False

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

    def reset_autofocus_linux_for_retry(self):
        try:
            print("[CAMERA] Reiniciando autofocus Linux para nuevo intento")

            self.set_autofocus_linux(False)
            time.sleep(0.04)

            self.set_autofocus_linux(True)
            time.sleep(0.4)

            self.emit_preview_during_focus(seconds=1.0, interval=0.03)

        except Exception as e:
            print(f"[CAMERA][WARNING] No se pudo reiniciar autofocus Linux: {e}")

    def reset_autofocus_windows_for_retry(self):
        try:
            print("[CAMERA] Reiniciando autofocus Windows para nuevo intento")

            self.set_autofocus_windows(False)
            time.sleep(0.04)

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

    def autofocus_calibration_linux_with_retries(self):
        best_global_frame = None
        best_global_score = -1

        for attempt in range(1, self.max_focus_retries_linux + 1):
            print(f"[CAMERA] Intento autofocus Linux {attempt}/{self.max_focus_retries_linux}")

            best_frame, score = self.autofocus_calibration()

            if score > best_global_score:
                best_global_frame = best_frame
                best_global_score = score

            if score > self.min_focus_score_linux:
                print(f"[CAMERA] Enfoque Linux aceptado score={score}")
                return best_frame, score
            
            print(
                f"[CAMERA][WARNING] Enfoque Linux bajo o foco inválido. "
                f"score={score}. Reintentando..."
            )

            if attempt < self.max_focus_retries_linux:
                self.reset_autofocus_linux_for_retry()

        print(
            f"[CAMERA][ERROR] No se alcanzó score mínimo Linux. "
            f"Mejor score={best_global_score}"
        )

        return best_global_frame, best_global_score


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

    def freeze_camera(self):
        if not self.can_freeze_focus:
            print("[CAMERA][WARNING] Congelamiento omitido: cámara sin controles de enfoque requeridos")
            return None

        try:

            self.set_autofocus_linux(False)
            time.sleep(0.3)

            self.locked_focus_value = None

            print("[CAMERA] Autofocus detenido. Enfoque congelado")
            return True

        except Exception as e:
            print(f"[CAMERA][ERROR] Error congelando foco: {e}")
            return None

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
            if not self.autofocus_supported:
                print("[CAMERA][WARNING] Linux: cámara sin autofocus. Recalibración omitida.")
                return

            self.apply_base_controls_linux()
            self.warmup_camera(frames=30, delay=0.02)

            best_frame, score = self.autofocus_calibration_linux_with_retries()

            if score < self.min_focus_score_linux:
                print(
                    f"[CAMERA][WARNING] Linux: score bajo en recalibración ({score}). "
                    "No se congela foco; se deja autofocus activo."
                )
                self.set_autofocus_linux(True)
                return

            locked = self.freeze_camera()

            if locked is None:
                print("[CAMERA][WARNING] Linux: no se pudo congelar recalibración, se deja autofocus activo")
                self.set_autofocus_linux(True)
            else:
                print(f"[CAMERA] Linux recalibrado score={score}, focus={locked}")

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

        if not self.can_freeze_focus:
            print("[CAMERA][WARNING] Cámara sin autofocus controlable. Se usará video sin congelar enfoque.")
            return

        best_frame, score = self.autofocus_calibration_linux_with_retries()

        if score < self.min_focus_score_linux:
            print(
                f"[CAMERA][WARNING] Linux: score bajo ({score}). "
                "No se congela foco; se deja autofocus activo."
            )
            self.set_autofocus_linux(True)
            return
        
        locked = self.freeze_camera()

        if not locked:
            print("[CAMERA][WARNING] Linux: no se pudo congelar foco, se deja autofocus activo")
            self.set_autofocus_linux(True)
        else:
            print(f"[CAMERA] FOCUS CALIBRADO SCORE: {score}")

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