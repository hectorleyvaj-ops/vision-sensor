# Runtime Raspberry Pi OS de 32 bits

Esta variante usa PyQt5, OpenCV y NumPy empaquetados por Raspberry Pi OS/Debian
para `armhf`. No intenta descargar PySide6 ni wheels binarios de OpenCV desde
PyPI.

## Paquetes del sistema

```bash
sudo apt update
sudo apt install -y python3-venv python3-pyqt5 python3-opencv python3-numpy libdmtx0b v4l-utils
```

## Entorno virtual

No reutilices el entorno que fallo, porque fue creado sin acceso a los paquetes
APT. Crea otro con un nombre distinto:

```bash
cd /home/worksurface/calibration/Proyecto_vision_sensor_phase8
python3 -m venv --system-site-packages venv-rpi32
source venv-rpi32/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-rpi32.txt
```

`--system-site-packages` es obligatorio en esta variante: permite que el entorno
vea `/usr/lib/python3/dist-packages`, donde APT instala PyQt5, OpenCV y NumPy.
`v4l-utils` proporciona `v4l2-ctl`, requerido para detectar y modificar
`focus_absolute` en la calibracion por receta.

## Verificacion

```bash
export VISION_QT_API=pyqt5
python scripts/check_qt_runtime.py
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/validate_installation.py
```

La salida debe identificar `Qt: PyQt5`. Antes de cargar datos reales, el
validador Worksurface debe indicar `LISTA PARA CALIBRAR`.

## Inicio de la interfaz

```bash
export VISION_QT_API=pyqt5
export VISION_SYSTEM_CONFIG=installations/worksurface/system.json
python main.py
```

La seleccion tambien es automatica cuando PySide6 no existe y PyQt5 si esta
instalado. La variable explicita se recomienda en la Raspberry para que una
instalacion accidental de otro binding no cambie el backend en produccion.

## Notas

- No ejecutes `pip install -r requirements.txt` en esta Raspberry.
- No ejecutes `pip install PyQt5` ni `pip install opencv-python` en `armhf`.
- No desactives los bloqueos de controlador para ocultar que el firmware de
  fase 9 aun no esta instalado.
- Si `apt` no encuentra alguno de los paquetes, identifica primero la version
  de Raspberry Pi OS con `cat /etc/os-release`; no agregues repositorios de otra
  distribucion.
