import sys
from app.app import MainWindow
from utils.qt_compat import QApplication, QMessageBox

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
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
        sys.exit(2)

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
