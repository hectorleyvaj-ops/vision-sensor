"""Report the Qt/vision runtime selected for this installation."""

import platform
import struct
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    from utils.qt_compat import QT_LIB

    import cv2
    import numpy

    print(f"Python: {sys.version.split()[0]}")
    print(f"Ejecutable: {sys.executable}")
    print(f"Arquitectura: {platform.machine()} ({struct.calcsize('P') * 8} bits)")
    print(f"Qt: {QT_LIB}")
    print(f"OpenCV: {cv2.__version__}")
    print(f"NumPy: {numpy.__version__}")

    if QT_LIB == "PyQt5":
        from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR

        print(f"PyQt: {PYQT_VERSION_STR}")
        print(f"Qt runtime: {QT_VERSION_STR}")
    else:
        import PySide6

        print(f"PySide: {PySide6.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
