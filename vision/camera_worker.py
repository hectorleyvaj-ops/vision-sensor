import cv2
import time
from utils.qt_compat import QObject, Signal, QTimer

class CameraWorker(QObject):
    frame_ready = Signal(object)
    cap_ready = Signal(object)
    finished = Signal()

    def __init__(self,camera_index=0, width=640, height=480):
        super().__init__()
        self.camera_index = camera_index
        
        self.width = width
        self.height = height
        self.cap = None

        self._running = False
        self.Trigger = False

        self.current_frame = None
        

    def start(self):
        # LOOP PRINCIPAL DE CAPTURA
        self._running = True
        
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

            if not self.cap.isOpened():
                print("No se pudo abrir la camara")
                self._running = False
                self.finished.emit()
                return

            #Configura la resolución - OPCIONAL, dependiendo de tu cámara puede no ser necesario
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            self.cap.set(cv2.CAP_PROP_FOCUS, 45)  # AJUSTA ESTE VALOR SEGÚN TU ESCENA

            self.cap.set(cv2.CAP_PROP_ZOOM, 0.0)

            while self._running:
                
                ret, frame = self.cap.read()

                if not ret:
                    time.sleep(0.005)
                    continue
                
                self.frame_ready.emit(frame)
                self.current_frame = frame

                if self.Trigger:
                    self.cap_ready.emit(frame)
                    self.Trigger = False

                time.sleep(0.005)

        except Exception as e:
            print(f"Error en camara: {e}")

        finally:
            print("Liberando camara...")
            if self.cap:
                self.cap.release()

            print("Worker terminado")
            self.finished.emit()

    def capture(self):
        self.Trigger = True

    def stop(self):
        print("solicitud de cierre")
        self._running = False

        if self.cap is not None:
            print("Forzando liberacion de camara desde stop")
            self.cap.release()