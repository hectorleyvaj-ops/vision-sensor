import sys
from app.app import MainWindow
from utils.qt_compat import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)


    window = MainWindow()
    window.show()

    sys.exit(app.exec())