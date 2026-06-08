import cv2
from utils.qt_compat import QLabel, QTimer, QImage, QPixmap, Qt, QPainter, QColor, Signal
import numpy as np

class VideoWidget(QLabel):
    def __init__(self, get_frame_callback=None, enable_edition=False):
        super().__init__()

        self.get_frame = get_frame_callback
        self.setMinimumSize(225,180)
        self.setMaximumSize(225,180)
        self.setMouseTracking(True)

        # TIMER
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)    # LIMITAR FPS

        # FRAME ACTUAL
        self.current_frame = None

        # ROI
        self.enable_edition = enable_edition
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.rois = []     # ROI EN COORDS REALES DEL FRAME ORIGINAL
        self.roi = None

        # ESCALADO
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def update_frame(self):
        frame = self.get_frame()

        if frame is None:
            return
        
        if not isinstance(frame, (list, tuple)) and not hasattr(frame, "shape"):
            print("Frame invalido:", type(frame))
            return
        
        self.current_frame = frame.copy()

        zoom_factor = 0.75
        h, w, _ = frame.shape

        if zoom_factor > 1.0:
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)

            x1 = (w - new_w) // 2
            y1 = (w - new_h) // 2
            x2 = x1 + new_w
            y2 = y1 + new_h

            cropped = frame[y1:y2, x1:x2]
            display_frame = cv2.resize(cropped, (w,h))
        else:
            display_frame = frame.copy()

        # DIBUJAR ROI SI EXISTE
        if self.rois:
            for roi in self.rois:
                x1, y1, x2, y2 = roi
                cv2.rectangle(display_frame, (x1,y1), (x2,y2), (255, 0, 0), 2)

        # DIBUJAR ROI EN PROCESO
        if self.drawing and self.start_point and self.end_point:
            p1 = self.map_to_frame(self.start_point)
            p2 = self.map_to_frame(self.end_point)

            if p1 and p2:
                cv2.rectangle(display_frame, p1, p2, (0, 255, 255), 2)
        
        # CONVERTIR A RGB
        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape

        # ESCALAR MANTENIENDO ASPECTO
        label_w = self.width()
        label_h = self.height()

        scale_w = label_w/w
        scale_h = label_h/h

        self.scale = max(scale_w, scale_h)

        new_w = int(w*self.scale)
        new_h = int(h*self.scale)

        resized = cv2.resize(rgb, (new_w, new_h))

        # CENTRAR LA IMAGEN EN EL LABEL - WIDGET
        self.offset_x = (label_w - new_w) // 2
        self.offset_y = (label_h - new_h) // 2

        qt_image = QImage(
            resized.data,
            new_w,
            new_h,
            ch*new_w,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qt_image)

        # CREAR LIENZO NEGRO
        canvas = QPixmap(label_w, label_h)
        canvas.fill(Qt.black)

        painter = QPainter(canvas)
        painter.drawPixmap(self.offset_x, self.offset_y, pixmap)
        painter.end()

        self.setPixmap(canvas)

    def map_to_frame(self, pos):
        # CONVIERTE LAS COORDS DEL WIDGET A COORDS DEL FRAME REAL
        if self.current_frame is None:
            return None
        
        x = (pos.x() - self.offset_x) / self.scale
        y = (pos.y() - self.offset_y) / self.scale

        h,w, _ = self.current_frame.shape

        x = int(max(0, min(w - 1, x)))
        y = int(max(0, min(h - 1, y)))

        return(x,y)
    
    def mousePressEvent(self, event):
        if not self.enable_edition:
            return
        
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = self.start_point

    def mouseMoveEvent(self, ev):
        if not self.enable_edition:
            return
        if self.drawing:
            self.end_point = ev.pos()

    def mouseReleaseEvent(self, ev):
        if not self.enable_edition:
            return
        
        if ev.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.end_point = ev.pos()

            p1 = self.map_to_frame(self.start_point)
            p2 = self.map_to_frame(self.end_point)

            if p1 and p2:
                x1,y1 = p1
                x2,y2 = p2

                # NORMALIZAR
                x1, x2 = sorted([x1,x2])
                y1, y2 = sorted([y1,y2])

                self.roi = (x1, y1, x2, y2)
                print("Nuevo ROI desde config: ",self.roi)
                self.rois.append(self.roi)

        self.enable_edition = False


    def get_roi(self):
        return self.roi
    
    def set_rois(self, rois):
        # PERMITE DIBUJAR ROIS EXISTENTES FUERA DE CONFIG
        self.rois = list(rois)
        print("ROIs aplicados: ", self.rois)
        self.update()

