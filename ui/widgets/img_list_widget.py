from utils.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLabel
)
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

        self.lbl_count = QLabel("0 imagenes seleccionadas")
        self.list_paths = QListWidget()
        self.list_paths.setMinimumHeight(86)
        self.btn_capture = QPushButton("CAPTURAR IMAGEN")
        self.btn_remove = QPushButton("QUITAR SELECCIONADA")
        self.btn_clear = QPushButton("LIMPIAR LISTA")

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_capture)
        buttons.addWidget(self.btn_remove)
        buttons.addWidget(self.btn_clear)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.lbl_count)
        layout.addWidget(self.list_paths)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.btn_capture.clicked.connect(self.capture_image)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_images)

    def capture_image(self):
        if len(self.paths) >= self.max_images:
            self.lbl_count.setText(
                f"Limite de {self.max_images} imagenes; quita una antes de capturar"
            )
            return
        frame = self.get_frame()
        if frame is None:
            print("No hay frame para guardar")
            return
        
        os.makedirs(self.base_path, exist_ok=True)   # CREAR CARPETA SI NO EXISTE
        filename = f"{uuid4().hex}.png"
        path = os.path.join(self.base_path, filename)
        
        if not cv2.imwrite(path, frame):
            self.lbl_count.setText("No se pudo guardar la imagen capturada")
            return

        self.paths.append(path)
        self._refresh()

    def _refresh(self):
        self.list_paths.clear()
        for path in self.paths:
            self.list_paths.addItem(os.path.basename(path))
        self.lbl_count.setText(f"{len(self.paths)} imagenes seleccionadas")

    def remove_selected(self):
        row = self.list_paths.currentRow()
        if row >= 0:
            self.paths.pop(row)
            self._refresh()

    def clear_images(self):
        # Clearing the editor must not delete files before the parent dialog is
        # saved; otherwise Cancel would still destroy recipe resources.
        self.paths.clear()
        self._refresh()

    def get_value(self):
        return list(self.paths)

    def set_value(self, paths):
        self.paths = [str(path) for path in (paths or []) if path]
        self._refresh()
