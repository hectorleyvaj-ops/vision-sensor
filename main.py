import sys
from app.app import MainWindow
from utils.qt_compat import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.showFullScreen()

    if hasattr(app, "exec"):
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())