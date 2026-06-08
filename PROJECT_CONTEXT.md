# Vision Sensor System - PROJECT CONTEXT

## 📌 Propósito del sistema
Sistema de visión industrial para inspección automatizada con:
- Cámara en tiempo real
- Máquina de estados (FSM)
- Pipeline de procesamiento por recetas
- Comunicación con ESP32
- UI en PyQt (pyside6 principalmente y pyqt5 como opcion para modelos viejos)

---

## 🧠 Arquitectura general

### Main.py
- importa MainWindow de app.py y ejecuta para mostrarlo
- Separa Mainwindow de la ejecucion inicial

### UI Layer
- app.py (MainWindow)
- Qt Threads (Camera, State, Serial)

### Core Logic
- StateManager → FSM principal
- VisionPipeline → ejecución de herramientas

### Data Layer
- RecipeManager → manejo de recetas JSON

### Hardware Layer
- Camera (captura de frames)
- SerialComm (ESP32 comunicación)

---

## 🔁 Flujo del sistema
Cuando TRIGGER desde SerialComm:
IDLE → CAPTURING → PROCESSING → COMMUNICATING → IDLE

---

## ⚙️ Componentes clave

### StateManager
Controla toda la máquina de estados.

### VisionPipeline
Ejecuta tools definidos por receta.

### RecipeManager
Carga y selecciona configuraciones de inspección.

### ConfigWindow
Controla la interfaz de edicion de recetas y steps (herramientas) por receta.
Llama a ToolEditor quien crea una interfaz dinamica para modificar los parametros de cada herramienta segun dicha herramienta, usa schemas.py para vaciar la informacion de los widgets y parametros requeridos

---

## ⚠️ Notas importantes
- UI usa Qt Threads
- Pipeline es dinámico por recetas
- Sistema depende de sincronización de frame en tiempo real
- ESP32 recibe resultado OK/NG

---

## 📌 Objetivo actual
- Estabilizar UI (evitar freezes)
- Mejorar diseño de interfaz de configuracion, tanto la ventana dinamica (ventana escalada y en pantalla completa, widgets escaldos, copiar paleta de colores de la ventana principal)
- Mejorar FSM
- Preparar V2.0 para producción en otra máquina