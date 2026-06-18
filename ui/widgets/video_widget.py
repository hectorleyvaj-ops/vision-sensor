import cv2
from utils.qt_compat import QLabel, QTimer, QImage, QPixmap, Qt, QPainter, QColor, QPen, QSizePolicy
import numpy as np

class VideoWidget(QLabel):
    def __init__(self, get_frame_callback=None, enable_edition=False, platform="windows", video_size=None,fill_mode="cover"):
        super().__init__()

        self.get_frame = get_frame_callback
        self.enable_edition = enable_edition
        self.platform = platform
        self.fill_mode = fill_mode

        if video_size:
            self.setMinimumSize(video_size[0], video_size[1])
            self.setMinimumHeight(video_size[1])
            self.setMaximumHeight(video_size[1])
        else:
            if self.platform == "linux":
                self.setMinimumSize(260, 210)
                self.setMinimumHeight(210)
                self.setMaximumHeight(210)
            else:
                self.setMinimumSize(480, 270)
                self.setMinimumHeight(270)
                self.setMaximumHeight(270)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: black; border: 1px solid rgb(91, 192, 190);")

        # TIMER
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)    # LIMITAR FPS

        # FRAME ACTUAL
        self.current_frame = None
        self.frame_w = 1
        self.frame_h = 1

        # ROI
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.rois = []     # ROI EN COORDS REALES DEL FRAME ORIGINAL
        self.roi = None

        # ESCALADO
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.draw_w = 1
        self.draw_h = 1

    def update_frame(self):
        frame = self.get_frame() if self.get_frame else None

        if frame is None:
            return
        
        if not isinstance(frame, (list, tuple)) and not hasattr(frame, "shape"):
            print("[VIDEO_WIDGET] Frame invalido:", type(frame))
            return
        
        self.current_frame = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.frame_h, self.frame_w, ch = rgb.shape

        label_w = max(1, self.width())
        label_h = max(1, self.height())

        scale_w = label_w / self.frame_w
        scale_h = label_h / self.frame_h

        if self.fill_mode == "fit":
            self.scale = min(scale_w, scale_h)
        else:
            self.scale = max(scale_w, scale_h)

        self.draw_w = int(self.frame_w * self.scale)
        self.draw_h = int(self.frame_h * self.scale)

        resized = cv2.resize(rgb, (self.draw_w, self.draw_h))

        self.offset_x = (label_w - self.draw_w) // 2
        self.offset_y = (label_h - self.draw_h) // 2

        qt_image = QImage(
            resized.data,
            self.draw_w,
            self.draw_h,
            ch* self.draw_w,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qt_image)

        # CREAR LIENZO NEGRO
        canvas = QPixmap(label_w, label_h)
        canvas.fill(Qt.black)

        painter = QPainter(canvas)
        painter.drawPixmap(self.offset_x, self.offset_y, pixmap)

        self.draw_saved_rois(painter)
        self.draw_roi_in_progress(painter)

        painter.end()
        self.setPixmap(canvas)

    def frame_to_widget(self, point):
        x, y = point

        wx = int(x * self.scale + self.offset_x)
        wy = int(y * self.scale + self.offset_y)

        return wx, wy
    
    def widget_to_frame(self, pos):
        if self.current_frame is None:
            return None
        
        x = (pos.x() - self.offset_x) / self.scale
        y = (pos.y() - self.offset_y) / self.scale

        x = int(max(0, min(self.frame_w - 1, x)))
        y = int(max(0, min(self.frame_h - 1, y)))

        return x, y
    
    def draw_saved_rois(self, painter):
        if not self.rois:
            return
        
        pen = QPen(QColor(0,180,255))
        pen.setWidth(3)
        painter.setPen(pen)

        for roi in self.rois:
            x1, y1, x2, y2 = roi

            p1 = self.frame_to_widget((x1, y1))
            p2 = self.frame_to_widget((x2, y2))

            painter.drawRect(
                p1[0], 
                p1[1],
                p2[0] - p1[0],
                p2[1] - p1[1] 
            )

    def draw_roi_in_progress(self, painter):
        if not self.drawing or not self.start_point or not self.end_point:
            return

        pen = QPen(QColor(255, 220, 0))
        pen.setWidth(3)
        painter.setPen(pen)

        x1 = self.start_point.x()
        y1 = self.start_point.y()
        x2 = self.end_point.x()
        y2 = self.end_point.y()

        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        painter.drawRect(left, top, width, height)
    
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
            self.update()

    def mouseReleaseEvent(self, ev):
        if not self.enable_edition:
            return
        
        if ev.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.end_point = ev.pos()

            p1 = self.widget_to_frame(self.start_point)
            p2 = self.widget_to_frame(self.end_point)

            if p1 and p2:
                x1,y1 = p1
                x2,y2 = p2

                # NORMALIZAR
                x1, x2 = sorted([x1,x2])
                y1, y2 = sorted([y1,y2])

                min_size = 5

                if abs(x2 - x1) >= min_size and abs(y2-y1) >= min_size:
                    self.roi = (x1, y1, x2, y2)
                    self.rois = [self.roi]
                    print("[VIDEO_WIDGET] Nuevo ROI desde config: ",self.roi)
                
            self.enable_edition = False
            self.update()


    def get_roi(self):
        return self.roi
    
    def set_rois(self, rois):
        # PERMITE DIBUJAR ROIS EXISTENTES FUERA DE CONFIG
        self.rois = list(rois)

        if self.rois:
            self.roi = self.rois[-1]
        else:
            self.roi = None

        print("[VIDEO_WIDGET] ROIs aplicados: ", self.rois)
        self.update()

