import sys
from app.app import MainWindow
from utils.qt_compat import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()

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