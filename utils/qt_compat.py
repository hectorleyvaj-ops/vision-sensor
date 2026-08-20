"""
Determina el backend Qt a utilizar y proporciona funciones de compatibilidad para cargar interfaces de usuario.
"""
import os

from utils.qt_backend import normalize_qt_request

#Constante Global para almacenar la libreria Qt seleccionada
QT_LIB = None


def _requested_backend():
    """
    Return the requested Qt binding without coupling it to the OS name.
    Regresa el binding Qt solicitado sin acoplarlo al nombre del sistema operativo.
    """
    value = os.getenv("VISION_QT_API", "auto")
    try:
        return normalize_qt_request(value)
    except ValueError as exc:
        raise RuntimeError(
            str(exc)
        ) from exc


REQUESTED_QT_LIB = _requested_backend()


def _can_try(name):
    return REQUESTED_QT_LIB in ("auto", name)

try:
    if not _can_try("PySide6"):
        raise ImportError("PySide6 no fue seleccionado")
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

except ImportError as pyside_error:
    if not _can_try("PyQt5"):
        raise RuntimeError(
            "Se solicito PySide6 mediante VISION_QT_API, pero no esta "
            f"disponible: {pyside_error}"
        ) from pyside_error
    # FALLBACK: PYQT5
    try:
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
    except ImportError as pyqt_error:
        raise RuntimeError(
            "No hay un backend Qt utilizable. Instala PySide6 o PyQt5. "
            f"PySide6: {pyside_error}; PyQt5: {pyqt_error}"
        ) from pyqt_error

    QT_LIB = "PyQt5"

    def load_ui(path):
        try:
            return uic.loadUi(path)
        except Exception as e:
            raise RuntimeError(f"Error cargando UI: {path}\n{e}")
