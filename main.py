import os
import sys
from pathlib import Path
from app.app import MainWindow
from core.display_profile import build_display_profile
from core.runtime_health import write_runtime_health
from ui.theme import interface_stylesheet
from utils.qt_compat import QApplication, QMessageBox

if __name__ == "__main__":
    runtime_root = os.getenv("VISION_DEPLOYMENT_RUNTIME", "")
    health_path = Path(runtime_root) / "health.json" if runtime_root else None
    if health_path:
        write_runtime_health(
            health_path,
            "starting",
            version=os.getenv("VISION_RELEASE_VERSION", ""),
        )
    app = QApplication(sys.argv)
    app.setStyleSheet(interface_stylesheet(build_display_profile(800, 480)))
    
    try:
        window = MainWindow()
    except Exception as exc:
        message = (
            "La aplicacion no puede iniciar porque su configuracion base no "
            f"es utilizable.\n\nDetalle: {exc}\n\n"
            "Revisa VISION_SYSTEM_CONFIG, system.json y el catalogo de recetas."
        )
        print(f"[STARTUP][FATAL] {message}", file=sys.stderr)
        QMessageBox.critical(None, "Error de arranque", message)
        if health_path:
            write_runtime_health(
                health_path,
                "stopped",
                version=os.getenv("VISION_RELEASE_VERSION", ""),
                diagnostic=str(exc),
            )
        sys.exit(2)

    if health_path:
        write_runtime_health(
            health_path,
            "degraded",
            version=os.getenv("VISION_RELEASE_VERSION", ""),
            diagnostic="Interfaz iniciada; READY productivo se valida por separado.",
        )
        app.aboutToQuit.connect(
            lambda: write_runtime_health(
                health_path,
                "stopped",
                version=os.getenv("VISION_RELEASE_VERSION", ""),
            )
        )

    if sys.platform.startswith("linux"):
        window.showFullScreen()
    elif sys.platform.startswith("win"):
        window.show()
    else:
        window.show()

    if hasattr(app, "exec"):
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())
