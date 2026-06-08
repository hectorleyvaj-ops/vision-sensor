from utils.qt_compat import QWidget, QVBoxLayout, QPushButton, QListWidget
import os
import cv2
from uuid import uuid4

class ImageListWidget(QWidget):
    def __init__(self, get_frame_callback, base_path, max_images=10):
        super().__init__()

        self.get_frame = get_frame_callback
        self.base_path = base_path
        self.max_images = max_images

        self.paths = []

        self.btn_capture = QPushButton("Capturar Imagen")
        self.btn_clear = QPushButton("Limpiar")

        layout = QVBoxLayout()
        layout.addWidget(self.btn_capture)
        layout.addWidget(self.btn_clear)
        self.setLayout(layout)

        self.btn_capture.clicked.connect(self.capture_image)
        self.btn_clear.clicked.connect(self.clear_images)

    def capture_image(self):
        frame = self.get_frame()
        if frame is None:
            print("No hay frame para guardar")
            return
        
        os.makedirs(self.base_path, exist_ok=True)   # CREAR CARPETA SI NO EXISTE
        filename = f"{uuid4().hex}.png"
        path = os.path.join(self.base_path, filename)
        
        cv2.imwrite(path, frame)

        self.paths.append(path)

        if len(self.paths) > self.max_images:
            remove_path = self.paths.pop(0)
            if os.path.exists(remove_path):
                os.remove(remove_path)

    def clear_images(self):
        for path in self.paths:
            if os.path.exists(path):
                os.remove(path)

        self.paths.clear()

    def get_value(self):
        return self.paths
    