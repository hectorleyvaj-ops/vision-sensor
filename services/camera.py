import threading
import time


class Camera:
    """
    Puente seguro entre CameraWorker y StateManager.

    Guarda el ultimo frame recibido junto con timestamp y frame_id para evitar
    que el sistema inspeccione una imagen vieja si la camara se congela o deja
    de emitir frames.
    """

    def __init__(self, max_frame_age=0.50):
        self.last_frame = None
        self.last_frame_time = None
        self.frame_id = 0
        self.max_frame_age = float(max_frame_age)
        self._lock = threading.Lock()

    def update_frame(self, frame):
        if frame is None:
            return

        with self._lock:
            self.last_frame = frame.copy()
            self.last_frame_time = time.monotonic()
            self.frame_id += 1

    def has_fresh_frame(self, max_age=None):
        with self._lock:
            if self.last_frame is None or self.last_frame_time is None:
                return False

            limit = self.max_frame_age if max_age is None else float(max_age)
            return (time.monotonic() - self.last_frame_time) <= limit

    def capture(self, max_age=None):
        with self._lock:
            if self.last_frame is None or self.last_frame_time is None:
                return {
                    "status": "ERROR",
                    "error": "No frame"
                }

            now = time.monotonic()
            age = now - self.last_frame_time
            limit = self.max_frame_age if max_age is None else float(max_age)

            if age > limit:
                return {
                    "status": "ERROR",
                    "error": f"Frame viejo: {age:.3f}s > {limit:.3f}s",
                    "frame_age": age,
                    "frame_id": self.frame_id,
                }

            return {
                "status": "OK",
                "frame": self.last_frame.copy(),
                "frame_id": self.frame_id,
                "frame_timestamp": self.last_frame_time,
                "frame_age": age,
            }
