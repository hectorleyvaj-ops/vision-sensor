QT_LIB = None

try:
    # PRIORIDAD DE LIBRERIA: PYSIDE6
    from PySide6.QtWidgets import (
        QApplication, QWidget, QLabel, QMainWindow,
        QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QFormLayout,
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QDialog,
        QInputDialog, QScrollArea, QSizePolicy, QTabWidget, QTableWidget,
        QTableWidgetItem, QMessageBox, QPlainTextEdit
    )
    from PySide6.QtCore import QObject, QThread, Signal, Qt, QTimer, Slot, QMetaObject
    from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import QFile

    QT_LIB = "PySide6"

    def load_ui(path):
        loader = QUiLoader()
        file = QFile(path)

        if not file.open(QFile.ReadOnly):
            raise RuntimeError(f"No se pudo abrir el archivo UI: {path}")

        ui = loader.load(file)
        file.close()

        if ui is None:
            raise RuntimeError(f"Error cargando UI: {path}")

        return ui

except ImportError:
    # FALLBACK: PYQT5
    from PyQt5.QtWidgets import (  # type: ignore
        QApplication, QWidget, QLabel, QMainWindow,
        QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QFormLayout,
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QDialog,
        QInputDialog, QScrollArea, QSizePolicy, QTabWidget, QTableWidget,
        QTableWidgetItem, QMessageBox, QPlainTextEdit,
    )
    from PyQt5.QtCore import (  # type: ignore
        QObject, QThread, pyqtSignal as Signal, pyqtSlot as Slot,
        Qt, QTimer, QMetaObject,
    )
    from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen  # type: ignore
    from PyQt5 import uic   # type: ignore

    QT_LIB = "PyQt5"

    def load_ui(path):
        try:
            return uic.loadUi(path)
        except Exception as e:
            raise RuntimeError(f"Error cargando UI: {path}\n{e}")
