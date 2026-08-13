# Guia fase 8 - instalacion y recetas Worksurface

## 1. Resultado entregado

La fase 8 separa Worksurface del motor universal mediante un paquete en
`installations/worksurface/`:

- `system.json`: camara, controlador, runtime y trazabilidad de la estacion;
- `recipes.json`: recetas A/B/C en schema v3;
- `commissioning.json`: identidad, politica y datos fisicos pendientes;
- directorios de capturas OK/NG e imagenes maestras por modelo;
- validador offline que no abre camara, serial, ESP32 ni PLC.

No se modificaron `config/system.json` ni `core/models/recipes.json`. La
instalacion predeterminada del motor permanece intacta.

## 2. Seguridad deliberada

Los datos confirmados son:

| ID externo | Receta | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|---|
| A | `MODELO_A` | `0402012XA` | OK | NG |
| B | `MODELO_B` | `0402012XB` | NG | OK |
| C | `MODELO_C` | `0402012XC` | OK | OK |

Los patrones de sensores solo estan en el manifiesto externo; no intervienen
en el pipeline de vision.

No estan confirmados el contenido DataMatrix, las ROI, los umbrales, las
imagenes maestras, el enfoque, el asentamiento mecanico ni los niveles
electricos. Por ello las tres recetas usan `commissioned: false`. Aunque el
usuario seleccione una, el motor debe rechazar su ejecucion productiva.

## 3. Aplicar el parche

Partir de fase 7 ya instalada y verificada. Antes de aplicar, comprobar que no
quedaron archivos de fase 7 solamente agregados al index:

```bash
git status --short
```

El arbol debe estar limpio o los cambios propios deben estar guardados en un
commit. Luego:

```bash
git apply --check Patchs/0001-Add-Worksurface-installation-package.patch
git apply --index Patchs/0001-Add-Worksurface-installation-package.patch
git status --short
python -m unittest discover -s tests -v
python -m compileall app core processing services tools ui vision scripts
```

No volver a aplicar el parche si sus archivos ya aparecen en el index. En ese
caso primero se revisa `git status`; normalmente significa que el parche ya se
aplico y solo falta probarlo/confirmarlo.

## 4. Validacion inicial offline

Desde la raiz del repositorio:

```bash
python scripts/validate_installation.py
```

Resultado esperado inicial:

```text
Resultado: LISTA PARA CALIBRAR
```

Es correcto ver pendientes para cada modelo:

- ROI y codigo maestro DataMatrix;
- imagen maestra y umbral de histograma;
- enfoque calibrado;
- receta no comisionada.

No debe aparecer ningun `[ERROR]`. Para obtener el informe estructurado:

```bash
python scripts/validate_installation.py --json
```

El control estricto debe fallar de forma intencional en este punto:

```bash
python scripts/validate_installation.py --require-commissioned
```

Codigo esperado: `3`, que significa calibracion pendiente. Codigo `2` significa
paquete/configuracion invalida.

## 5. Activar la instalacion para calibracion

Ejecutar siempre desde la raiz del proyecto.

PowerShell:

```powershell
$env:VISION_SYSTEM_CONFIG = "installations/worksurface/system.json"
python main.py
```

CMD:

```bat
set VISION_SYSTEM_CONFIG=installations\worksurface\system.json
python main.py
```

Linux/Raspberry Pi:

```bash
export VISION_SYSTEM_CONFIG=installations/worksurface/system.json
python main.py
```

Durante fase 8 mantener desenergizada la liberacion hacia PLC y no aceptar
triggers automaticos. El firmware actual no implementa el protocolo definitivo;
el estado esperado del enlace es no listo hasta completar fase 9.

## 6. Comisionar cada modelo

Realizar el procedimiento por separado para A, B y C, sin copiar valores entre
modelos salvo que una medicion documentada demuestre que son equivalentes.

### 6.1 Capturas

1. Fijar camara, iluminacion, distancia y orientacion mecanica.
2. Capturar una poblacion de piezas OK en
   `commissioning_captures/model_x/ok/`.
3. Capturar defectos conocidos y casos limite en `.../ng/`.
4. Conservar resolucion original; no recortar ni reescalar los archivos fuente.
5. Registrar condiciones de captura y numero de pieza en el nombre o bitacora.

### 6.2 DataMatrix

1. Leer varias piezas del mismo modelo.
2. Confirmar si el numero de parte es el texto completo, solo un prefijo o no
   coincide con el contenido codificado.
3. Guardar el texto confirmado en `expected_code`.
4. Elegir `match_mode: exact` o `prefix` segun evidencia, no por conveniencia.
5. Dibujar la ROI sobre el frame de 1920x1080 y guardar
   `[x1,y1,x2,y2]` con limites exclusivos.
6. Probar giros, contraste, marcados debiles y codigos de otro modelo.

El valor historico de otra receta no se reutilizo porque no prueba el contenido
de A/B/C.

### 6.3 Imagen e histograma

1. Definir que caracteristica visual debe aceptar o rechazar el step.
2. Definir su ROI canonica.
3. Elegir maestras solo de piezas OK representativas.
4. Copiarlas a `master_images/model_x/`.
5. Guardar rutas relativas a la raiz, por ejemplo:
   `installations/worksurface/master_images/model_a/master_01.png`.
6. Medir scores con muestras OK y NG y fijar un umbral mayor que cero con margen.

Si no existe una caracteristica visual que justifique el histograma, aplicar la
decision documentada indicada en el README del paquete; no simular aprobacion
con un umbral cero.

### 6.4 Enfoque

1. Seleccionar una ROI estable de textura real.
2. Ejecutar el barrido con el hardware final de Raspberry Pi.
3. Guardar `value`, `min_score`, `median_score` y `peak_score` medidos.
4. Confirmar `mode: calibrated` y `enabled: true`.
5. Verificar arranque frio y primer trigger para cada modelo.

### 6.5 Tiempo mecanico y rutas fisicas

- medir desde clamps/trigger hasta inmovilizacion antes de cambiar
  `mechanical_settle_ms=0`;
- sustituir `camera.device=0` por `/dev/v4l/by-id/...` si la Raspberry lo ofrece;
- confirmar que el puerto CP2102 configurado coincide con el adaptador real;
- no relajar los tres `runtime.require_*` para ocultar un fallo de enlace o foco.

## 7. Cierre de fase 8

Despues de completar y probar una receta, marcarla `commissioned: true`. No
marcar las tres en bloque.

El cierre tecnico se comprueba con:

```bash
python scripts/validate_installation.py --require-commissioned
```

Debe terminar con codigo `0` y:

```text
Resultado: LISTA PARA PRODUCCION
```

Esto valida configuracion y recursos, pero no sustituye las pruebas fisicas de
fallas y repetibilidad previstas en fase 10.

## 8. Limite de esta fase

Fase 8 no cambia firmware ni ladder. Fase 9 migrara el ESP32 a
`vision_controller_v1` y verificara el PLC, pinout, polaridades y salida segura.
Hasta entonces no conectar esta plantilla no comisionada como reemplazo de la
estacion productiva.
