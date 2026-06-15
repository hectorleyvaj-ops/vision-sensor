from utils.qt_compat import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, Qt, Signal, Slot, QSizePolicy
)

from ui.widgets.video_widget import VideoWidget

class FocusConfigDialog(QDialog):
    calibration_requested = Signal(object)

    def __init__(self, recipe, get_frame_callback, platform="windows", parent=None):
        super().__init__(parent)

        self.recipe = recipe
        self.get_frame = get_frame_callback
        self.platform = platform

        self.focus_result = None

        self.setWindowTitle("Calibracion de enfoque")
        self.setStyleSheet(parent.styleSheet() if parent else "")

        self.build_ui()
        self.load_focus_config()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.spacing(14)

        self.lbl_status = QLabel("Selecciona una ROI de enfoque o usa la existente")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(38)
        self.lbl_status.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 8px;
                background-color: rgb(15, 27, 61);
                border: 1px solid rgb(91, 192, 190);
            }
        """)

        self.video = VideoWidget(
            get_frame_callback=self.get_frame,
            enable_edition=False,
            platform=self.platform,
            fill_mode="fit"
        )
        self.video.sizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.btn_select_roi = QPushButton("SELECT ROI")
        self.btn_clear_roi = QPushButton("FRAME COMPLETO")
        self.btn_calibrate = QPushButton("CALIBRAR")
        self.btn_save = QPushButton("GUARDAR")
        self.btn_cancel = QPushButton("CANCELAR")

        buttons = [
            self.btn_select_roi,
            self.btn_clear_roi,
            self.btn_calibrate,
            self.btn_save,
            self.btn_cancel,
        ]

        for btn in buttons:
            btn.setCursor(Qt.PointingHandCursor)
            btn.minimumHeight(36)
            btn.sizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        buttons_top = QHBoxLayout()
        buttons_top.setContentsMargins(0, 4, 0, 4)
        buttons_top.spacing(12)
        buttons_top.addWidget(self.btn_select_roi)
        buttons_top.addWidget(self.btn_clear_roi)
        buttons_top.addWidget(self.btn_calibrate)

        buttons_bott = QHBoxLayout()
        buttons_bott.setContentsMargins(0, 4, 0, 4)
        buttons_bott.spacing(12)
        buttons_bott.addWidget(self.btn_cancel)
        buttons_bott.addWidget(self.btn_save)

        layout.addWidget(self.lbl_status)
        layout.addWidget(self.video, stretch=1)
        layout.addSpacing(6)
        layout.addLayout(buttons_top)
        layout.addLayout(buttons_bott)

        self.btn_select_roi.clicked.connect(self.enable_roi_selection)
        self.btn_clear_roi.clicked.connect(self.clear_roi)
        self.btn_calibrate.clicked.connect(self.request_calibration)
        self.btn_save.clicked.connect(self.save_focus_config)
        self.btn_cancel.clicked.connect(self.reject)

    def load_focus_config(self):
        focus = self.recipe.get("focus", {})

        roi = focus.get("roi")
        value = focus.get("value")
        min_score = focus.get("min_score")

        if roi and len(roi) == 4:
            self.video.set_rois([tuple(roi)])
            roi_text = f"ROI actual: {roi}"
        else:
            roi_text = "ROI actual: frame completo"

        self.lbl_status.setText(
            f"{roi_text} | Focus: {value} | Min Score: {min_score}"
        )

    def enable_roi_selection(self):
        self.video.enable_edition = True
        self.lbl_status.setText("Dibuja la ROI de enfoque sobre el video.")

    def clear_roi(self):
        self.video.set_rois([])
        self.lbl_status.setText("ROI eliminada. Se usara el frame completo para enfocar.")

    def request_calibration(self):
        roi = self.video.get_roi()

        focus_config = {
            "roi": list(roi) if roi is not None else None
        }

        print(f"[FOCUS_DIALOG] Solicitud de calibración emitida: {focus_config}")

        self.btn_calibrate.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.lbl_status.setText("Calibrando enfoque, espere un momento...")

        self.calibration_requested.emit(focus_config)

    @Slot(object)
    def on_calibration_finished(self, result):
        print(f"[FOCUS_DIALOG] Resultado recibido: {result}")

        self.btn_calibrate.setEnabled(True)
        self.btn_save.setEnabled(True)

        if not isinstance(result, dict) or not result.get("ok"):
            self.lbl_status.setText("La calibracion no devolvio un resultado valido")
            return
        
        self.focus_result = result

        roi = result.get("roi")
        focus_value = result.get("focus_value")
        median_score = result.get("median_score")
        min_score = result.get("min_score")

        if roi:
            self.video.set_rois([tuple(roi)])

        self.lbl_status.setText(
            f"Calibración OK | Focus: {focus_value} | "
            f"Score: {median_score} | Min score: {min_score}"
        )

    @Slot(str)
    def on_calibration_failed(self, message):
        print(f"[FOCUS_DIALOG][ERROR] {message}")

        self.btn_calibrate.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.lbl_status.setText(f"Error de calibracion: {message}")

    def save_focus_config(self):
        if "focus" not in self.recipe or not isinstance(self.recipe["focus"], dict):
            self.recipe["focus"] = {}

        roi = self.video.get_roi()

        if self.focus_result:
            self.recipe["focus"] = {
                "enabled": True,
                "roi": self.focus_result.get("roi"),
                "value": self.focus_result.get("focus_value"),
                "min_score": self.focus_result.get("min_score"),
                "median_score": self.focus_result.get("median_score"),
                "peak_score": self.focus_result.get("peak_score"),
                "verify_on_first_trigger": True,
                "auto_refocus_if_failed": True,
            }

        else:
            self.recipe["focus"]["enabled"] = True
            self.recipe["focus"]["roi"] = list(roi) if roi is not None else None
            self.recipe["focus"].setdefault("value", None)
            self.recipe["focus"].setdefault("min_score", None)
            self.recipe["focus"].setdefault("verify_on_first_trigger", True)
            self.recipe["focus"].setdefault("auto_refocus_if_failed", True)

        self.accept()