from utils.qt_compat import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QScrollArea, QWidget, Qt, Signal, Slot, QSizePolicy
)

from core.camera_runtime import format_camera_runtime, manual_focus_preflight
from core.focus_modes import FOCUS_MODE_LABELS, focus_mode_label
from ui.widgets.video_widget import VideoWidget
from ui.responsive import compact_stylesheet, profile_from_widget
from ui.theme import interface_stylesheet

class FocusConfigDialog(QDialog):
    calibration_requested = Signal(object)

    def __init__(
        self,
        recipe,
        get_frame_callback,
        platform="windows",
        parent=None,
        display_profile=None,
        camera_runtime=None,
    ):
        super().__init__(parent)

        self.recipe = recipe
        self.get_frame = get_frame_callback
        self.platform = platform
        self.camera_runtime = dict(camera_runtime or {})
        self.display_profile = display_profile or profile_from_widget(parent or self)

        self.focus_result = None

        self.setWindowTitle("Calibracion de enfoque de la receta")
        self.setStyleSheet(
            interface_stylesheet(self.display_profile)
            + compact_stylesheet(self.display_profile)
        )

        self.build_ui()
        self.load_focus_config()

    def build_ui(self):
        layout = QVBoxLayout(self)
        margin = self.display_profile.margin
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(self.display_profile.spacing)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(self.display_profile.spacing)

        self.lbl_status = QLabel("Selecciona una ROI de enfoque o usa la existente")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(self.display_profile.touch_target)
        self.lbl_status.setProperty("uiRole", "summary")

        self.lbl_camera = QLabel(format_camera_runtime(self.camera_runtime))
        self.lbl_camera.setWordWrap(True)
        self.lbl_camera.setObjectName("cameraRuntimeStatus")
        self.lbl_camera.setToolTip(
            "El enfoque usa el dispositivo de video activo, no el puerto serial del controlador."
        )

        self.cmb_focus_mode = QComboBox()
        for value, label in FOCUS_MODE_LABELS.items():
            self.cmb_focus_mode.addItem(label, value)
        self.cmb_focus_mode.setMinimumHeight(34)

        self.video = VideoWidget(
            get_frame_callback=self.get_frame,
            enable_edition=False,
            platform=self.platform,
            fill_mode="fit"
        )
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setMinimumSize(120, 80)
        self.video.setMaximumHeight(self.display_profile.dialog_video_height)

        self.btn_select_roi = QPushButton("SELECCIONAR ROI")
        self.btn_clear_roi = QPushButton("FRAME COMPLETO")
        self.btn_calibrate = QPushButton("CALIBRAR")
        self.btn_save = QPushButton("GUARDAR")
        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_calibrate.setProperty("buttonRole", "primary")
        self.btn_save.setProperty("buttonRole", "primary")

        buttons = [
            self.btn_select_roi,
            self.btn_clear_roi,
            self.btn_calibrate,
            self.btn_save,
            self.btn_cancel,
        ]

        for btn in buttons:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(self.display_profile.touch_target)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        buttons_top = QHBoxLayout()
        buttons_top.setContentsMargins(0, 4, 0, 4)
        buttons_top.setSpacing(12)
        buttons_top.addWidget(self.btn_select_roi)
        buttons_top.addWidget(self.btn_clear_roi)
        buttons_top.addWidget(self.btn_calibrate)

        buttons_bott = QHBoxLayout()
        buttons_bott.setContentsMargins(0, 4, 0, 4)
        buttons_bott.setSpacing(12)
        buttons_bott.addWidget(self.btn_cancel)
        buttons_bott.addWidget(self.btn_save)

        body.addWidget(self.lbl_status)
        body.addWidget(self.lbl_camera)
        camera_note = QLabel("El enfoque usa /dev/video*, no el puerto serial ESP/PLC.")
        camera_note.setWordWrap(True)
        body.addWidget(camera_note)
        body.addWidget(QLabel("Modo de enfoque"))
        body.addWidget(self.cmb_focus_mode)
        body.addWidget(self.video)
        body.addLayout(buttons_top)

        self.scroll.setWidget(content)
        layout.addWidget(self.scroll, stretch=1)
        layout.addLayout(buttons_bott)

        self.btn_select_roi.clicked.connect(self.enable_roi_selection)
        self.btn_clear_roi.clicked.connect(self.clear_roi)
        self.btn_calibrate.clicked.connect(self.request_calibration)
        self.btn_save.clicked.connect(self.save_focus_config)
        self.btn_cancel.clicked.connect(self.reject)
        self.cmb_focus_mode.currentIndexChanged.connect(
            lambda _index: self.on_focus_mode_changed(self.current_focus_mode())
        )

    def current_focus_mode(self):
        return str(self.cmb_focus_mode.currentData() or "disabled")

    def load_focus_config(self):
        focus = self.recipe.get("focus", {})

        mode = focus.get("mode", "calibrated")
        mode_index = self.cmb_focus_mode.findData(mode)
        self.cmb_focus_mode.setCurrentIndex(max(0, mode_index))
        roi = focus.get("roi")
        value = focus.get("value")
        min_score = focus.get("min_score")

        if roi and len(roi) == 4:
            self.video.set_rois([tuple(roi)])
            roi_text = f"ROI actual: {roi}"
        else:
            roi_text = "ROI actual: frame completo"

        self.lbl_status.setText(
            f"Modo: {focus_mode_label(mode)} | {roi_text} | Enfoque: {value} | "
            f"Puntuacion minima: {min_score}"
        )
        self.on_focus_mode_changed(mode)

    def on_focus_mode_changed(self, mode):
        calibration_enabled = mode in ("calibrated", "manual_fixed")
        preflight_ok, preflight_message = manual_focus_preflight(self.camera_runtime)
        if not self.camera_runtime:
            preflight_ok = True
        self.btn_calibrate.setEnabled(calibration_enabled)
        self.btn_select_roi.setEnabled(calibration_enabled)
        self.btn_clear_roi.setEnabled(calibration_enabled)

        if calibration_enabled and not preflight_ok:
            self.btn_calibrate.setEnabled(False)

        descriptions = {
            "calibrated": "Barrido automatico inicial y foco congelado por receta.",
            "manual_fixed": "Usa el valor fijo guardado; CALIBRAR permite obtenerlo.",
            "auto_continuous": "La camara ajusta el foco continuamente.",
            "disabled": "La aplicacion no administra el enfoque.",
        }
        description = descriptions.get(mode, "Modo de enfoque no reconocido")
        if calibration_enabled and not preflight_ok:
            description = f"{description}\nNo disponible: {preflight_message}"
        self.lbl_status.setText(description)

    def enable_roi_selection(self):
        self.video.enable_edition = True
        self.lbl_status.setText("Dibuja la ROI de enfoque sobre el video.")

    def clear_roi(self):
        self.video.set_rois([])
        self.lbl_status.setText("ROI eliminada. Se usara el frame completo para enfocar.")

    def request_calibration(self):
        mode = self.current_focus_mode()
        if mode not in ("calibrated", "manual_fixed"):
            self.lbl_status.setText("Este modo no requiere calibracion manual.")
            return

        if self.camera_runtime:
            preflight_ok, preflight_message = manual_focus_preflight(
                self.camera_runtime
            )
            if not preflight_ok:
                self.lbl_status.setText(f"No se puede calibrar: {preflight_message}")
                return

        roi = self.video.get_roi()

        focus_config = {
            "roi": list(roi) if roi is not None else None
        }

        print(f"[FOCUS_DIALOG] Solicitud de calibración emitida: {focus_config}")

        self.btn_calibrate.setEnabled(False)
        self.btn_save.setEnabled(False)
        device = self.camera_runtime.get("resolved_device", "camara activa")
        self.lbl_status.setText(
            f"Calibrando enfoque en {device}; espere un momento..."
        )

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
        device = result.get("device") or self.camera_runtime.get("resolved_device", "?")

        if roi:
            self.video.set_rois([tuple(roi)])

        self.lbl_status.setText(
            f"Calibracion correcta en {device} | Enfoque: {focus_value} | "
            f"Puntuacion: {median_score} | Minima: {min_score}"
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
        mode = self.current_focus_mode()

        if self.focus_result and mode in ("calibrated", "manual_fixed"):
            self.recipe["focus"] = {
                "mode": mode,
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
            self.recipe["focus"]["mode"] = mode
            self.recipe["focus"]["enabled"] = mode != "disabled"
            self.recipe["focus"]["roi"] = list(roi) if roi is not None else None
            self.recipe["focus"].setdefault("value", None)
            self.recipe["focus"].setdefault("min_score", None)
            self.recipe["focus"].setdefault("verify_on_first_trigger", True)
            self.recipe["focus"].setdefault("auto_refocus_if_failed", True)

        self.accept()
