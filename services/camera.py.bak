# MODIFICAR PARA OBTENER EL FRAME DESDE CAMERA WORKER..
# USAR EL ULTIMO FRAME DEL WORKER Y ENVIARLO A STATE_MANAGER

class Camera:
    def __init__(self):
        self.last_frame = None

    def update_frame(self, frame):
        self.last_frame = frame

    def capture(self):
        if self.last_frame is None:
            return {
                "status": "ERROR", 
                "error": "No frame"
            }
        
        return {
            "status": "OK",
            "frame": self.last_frame.copy()
        }
    