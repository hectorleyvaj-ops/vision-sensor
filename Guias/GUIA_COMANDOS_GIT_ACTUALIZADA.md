# Guía práctica de Git y patches — Vision Sensor / Worksurface

Esta guía está adaptada al flujo del proyecto `vision-sensor`: ramas `develop` y `main`, ramas de mejora, worktrees, checkpoints, pruebas en Windows/Raspberry Pi y aplicación de archivos `.patch`.

> Regla principal: antes de descartar, fusionar o aplicar un patch, ejecuta `git status` y revisa exactamente qué archivos serán afectados.

## 1. Respuesta rápida: descartar archivos específicos antes de un patch

### Caso A: el archivo está modificado, pero no se agregó con `git add`

```bash
git status --short
git diff -- config/system.json
git restore --source=HEAD -- config/system.json
```

Para varios archivos específicos:

```bash
git restore --source=HEAD -- config/system.json app.py core/config.py
```

El separador `--` indica que lo siguiente son rutas de archivos, no opciones de Git.

### Caso B: el archivo también está preparado, es decir, ya se ejecutó `git add`

Restaura al último commit tanto el área preparada como el archivo de trabajo:

```bash
git restore --source=HEAD --staged --worktree -- config/system.json
```

Para varios archivos:

```bash
git restore --source=HEAD --staged --worktree -- config/system.json app.py core/config.py
```

### Caso C: quieres conservar una copia antes de descartarlo

La opción más segura es guardar solamente los archivos elegidos en un stash:

```bash
git stash push -m "Respaldo antes de aplicar fase 4" -- config/system.json app.py
git stash list
```

Después puedes recuperar ese respaldo con:

```bash
git stash apply stash@{0}
```

En PowerShell, conviene escribir la referencia entre comillas:

```powershell
git stash apply "stash@{0}"
```

### Verificación final antes de aplicar el patch

```bash
git status --short
git diff -- config/system.json
git diff --staged -- config/system.json
git apply --check universal_engine_hardening_phase4.patch
```

Si `git apply --check` no muestra errores, aplica el patch:

```bash
git apply universal_engine_hardening_phase4.patch
```

Después verifica, prueba y crea el commit:

```bash
git status
git diff --check
python -m unittest discover -s tests -p "test_*.py" -v
git add .
git commit -m "Aplica endurecimiento universal de fase 4"
```

## 2. Diagnóstico recomendado para el patch de fase 4

### Paso 1: confirmar la carpeta y rama correctas

```bash
git rev-parse --show-toplevel
git branch --show-current
git status
```

### Paso 2: revisar qué intenta cambiar el patch

```bash
git apply --stat universal_engine_hardening_phase4.patch
git apply --summary universal_engine_hardening_phase4.patch
git apply --numstat universal_engine_hardening_phase4.patch
```

### Paso 3: comprobar sin modificar nada

```bash
git apply --check universal_engine_hardening_phase4.patch
```

Para obtener más detalle:

```bash
git apply --check --verbose universal_engine_hardening_phase4.patch
```

### Paso 4: restaurar únicamente los archivos locales que bloquean el patch

Ejemplo para `config/system.json`:

```bash
git diff -- config/system.json
git diff --staged -- config/system.json
git restore --source=HEAD --staged --worktree -- config/system.json
git status --short
```

### Paso 5: comprobar y aplicar nuevamente

```bash
git apply --check universal_engine_hardening_phase4.patch
git apply universal_engine_hardening_phase4.patch
```

### Si quieres excluir `config/system.json`

Hazlo solo si conservarás o integrarás manualmente la configuración después:

```bash
git apply --check --exclude=config/system.json universal_engine_hardening_phase4.patch
git apply --exclude=config/system.json universal_engine_hardening_phase4.patch
```

Si las rutas del patch comienzan con `a/` y `b/`, normalmente Git las interpreta correctamente. Si el patrón de exclusión no coincide, consulta las rutas reales con `git apply --stat` y usa exactamente esa ruta.

### Si el patch fue creado desde una base diferente

Intenta una aplicación de tres vías; Git usará los identificadores incluidos en el patch cuando estén disponibles:

```bash
git apply --check --3way universal_engine_hardening_phase4.patch
git apply --3way universal_engine_hardening_phase4.patch
```

Si quedan conflictos:

```bash
git status
```

Corrige cada archivo, elimina las marcas `<<<<<<<`, `=======` y `>>>>>>>`, y luego ejecuta:

```bash
git add ruta/archivo_corregido.py
git commit -m "Resuelve conflictos del patch de fase 4"
```

### Si quieres aplicar lo posible y generar archivos `.rej`

```bash
git apply --reject --whitespace=fix universal_engine_hardening_phase4.patch
```

Git dejará fragmentos no aplicados en archivos `.rej`. Esta opción requiere revisión manual y no debe confirmarse sin ejecutar las pruebas.

### Si necesitas revertir un patch que acaba de aplicarse

Primero comprueba que la reversión es posible:

```bash
git apply --check --reverse universal_engine_hardening_phase4.patch
```

Después:

```bash
git apply --reverse universal_engine_hardening_phase4.patch
```

## 3. Error `index file corrupt` o `bad signature 0x00000000`

Este mensaje normalmente señala el índice local `.git/index`, no necesariamente el contenido del patch. Primero confirma el problema:

```bash
git status
```

En Windows PowerShell, crea un respaldo del índice y reconstrúyelo:

```powershell
Copy-Item .git\index .git\index.backup
Remove-Item .git\index
git reset
git status
```

En Git Bash o Linux:

```bash
cp .git/index .git/index.backup
rm .git/index
git reset
git status
```

`git reset` sin `--hard` reconstruye el índice y conserva el contenido de los archivos de trabajo. No uses `git reset --hard` para esta reparación.

Después repite:

```bash
git apply --check universal_engine_hardening_phase4.patch
```

## 4. Configuración inicial

```bash
git --version
git config --global user.name "Tu Nombre"
git config --global user.email "tu_correo@example.com"
git config --global --list
```

Para revisar solamente la configuración del repositorio actual:

```bash
git config --local --list
```

## 5. Crear, clonar y comprobar un repositorio

Inicializar una carpeta existente:

```bash
cd "C:\ruta\vision-sensor"
git init
```

Clonar un repositorio:

```bash
git clone https://github.com/USUARIO/vision-sensor.git
cd vision-sensor
```

Comprobar raíz, remoto y rama:

```bash
git rev-parse --show-toplevel
git remote -v
git branch --show-current
```

## 6. Inspeccionar cambios

```bash
git status
git status --short
git diff
git diff --staged
git diff --name-only
git diff --staged --name-only
git diff --check
```

Revisar un archivo concreto:

```bash
git diff -- config/system.json
git diff --staged -- config/system.json
```

Comparar dos ramas:

```bash
git diff develop..improve-config-ui
git diff --name-status develop..improve-config-ui
```

Ver historial compacto:

```bash
git log --oneline --graph --decorate --all
git log -n 10 --stat
```

## 7. Preparar y guardar cambios

Agregar archivos específicos, opción recomendada:

```bash
git add config/system.json core/config.py tests/test_config.py
git diff --staged
git commit -m "Integra configuración universal del sistema"
```

Agregar todos los cambios rastreados y archivos nuevos:

```bash
git add .
```

Quitar un archivo del área preparada sin perder sus cambios:

```bash
git restore --staged -- config/system.json
```

Modificar el último commit conservando su mensaje:

```bash
git add ruta/archivo_olvidado.py
git commit --amend --no-edit
```

No uses `--amend` si ese commit ya fue compartido y otras personas trabajan desde él, salvo que hayan coordinado la reescritura.

## 8. Ramas de trabajo

Ver ramas:

```bash
git branch
git branch -a
git branch -vv
```

Cambiar de rama:

```bash
git switch develop
```

Crear una rama desde `develop` actualizado:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c improve-tool-editor-ui
git push -u origin improve-tool-editor-ui
```

Actualizar una rama de mejora con `develop`:

```bash
git switch improve-tool-editor-ui
git fetch origin
git merge origin/develop
```

Integrar una rama terminada:

```bash
git switch develop
git pull --ff-only origin develop
git merge --no-ff improve-tool-editor-ui
git push origin develop
```

Publicar `develop` en `main` cuando ya sea estable:

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff develop
git push origin main
```

## 9. Worktrees para cambios aislados

Crear otra carpeta conectada al mismo repositorio:

```bash
git worktree add ../Proyecto_vision_harden -b harden-production-dmtx develop
```

Listar worktrees:

```bash
git worktree list
```

Retirar un worktree cuando ya no se necesita y no tiene cambios pendientes:

```bash
git worktree remove ../Proyecto_vision_harden
git worktree prune
```

La rama continúa existiendo después de retirar el worktree. Compruébalo con `git branch` antes de eliminarla.

## 10. Stash: guardar trabajo temporal

Guardar cambios rastreados:

```bash
git stash push -m "Trabajo temporal de UI"
```

Incluir archivos nuevos todavía no rastreados:

```bash
git stash push -u -m "Trabajo temporal con archivos nuevos"
```

Guardar solamente rutas específicas:

```bash
git stash push -m "Respaldo de configuración" -- config/system.json core/config.py
```

Inspeccionar y recuperar:

```bash
git stash list
git stash show --stat stash@{0}
git stash show -p stash@{0}
git stash apply stash@{0}
```

`apply` conserva el stash. `pop` lo elimina si la aplicación tiene éxito, por lo que `apply` es preferible cuando quieres verificar antes.

## 11. Tags y checkpoints

```bash
git tag
git tag -a v2.0-config-ui-ok -m "Versión estable con mejoras de configuración"
git push origin v2.0-config-ui-ok
git fetch --tags
```

Inspeccionar temporalmente un tag:

```bash
git switch --detach v2.0-config-ui-ok
```

Crear una rama recuperable desde el tag:

```bash
git switch -c recovery-config-ui v2.0-config-ui-ok
```

## 12. Remoto y sincronización

```bash
git remote -v
git fetch origin
git pull --ff-only origin develop
git push origin develop
```

Configurar el remoto por primera vez:

```bash
git remote add origin https://github.com/USUARIO/vision-sensor.git
git push -u origin develop
```

Corregir la URL:

```bash
git remote set-url origin https://github.com/USUARIO/vision-sensor.git
```

`git fetch` descarga referencias sin modificar tu rama. `git pull --ff-only` actualiza solamente cuando no necesita crear una fusión inesperada.

## 13. Conflictos de merge

Git marca conflictos así:

```text
<<<<<<< HEAD
Versión actual
=======
Versión entrante
>>>>>>> nombre-rama
```

Después de elegir o integrar el contenido correcto:

```bash
git add ruta/archivo_corregido.py
git commit -m "Resuelve conflictos de integración"
```

Cancelar un merge en curso:

```bash
git merge --abort
```

## 14. Archivos no rastreados

`git restore` no funciona con archivos que Git nunca ha registrado. Primero revisa cuáles serían eliminados:

```bash
git clean -n -- ruta/archivo_temporal.py
```

Para eliminar solamente ese archivo después de verificarlo:

```bash
git clean -f -- ruta/archivo_temporal.py
```

No uses `git clean -fd` de forma general sin revisar primero `git clean -nd`, porque puede eliminar carpetas y archivos no recuperables por Git.

## 15. Validaciones usadas en Worksurface

Ejecutar pruebas unitarias:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Comprobar sintaxis de Python:

```bash
python -m compileall -q .
```

Comprobar errores de espacios o marcadores de conflicto:

```bash
git diff --check
```

Buscar marcadores de conflicto pendientes con `rg`:

```bash
rg -n "^(<<<<<<<|=======|>>>>>>>)" .
```

Flujo mínimo de validación:

```bash
git status
git diff --check
python -m compileall -q .
python -m unittest discover -s tests -p "test_*.py" -v
```

## 16. Flujo recomendado para una fase nueva

```bash
git switch develop
git pull --ff-only origin develop
git status
git switch -c phase-4-universal-hardening
```

Antes de aplicar el patch:

```bash
git status --short
git apply --stat universal_engine_hardening_phase4.patch
git apply --check universal_engine_hardening_phase4.patch
```

Aplicar y validar:

```bash
git apply universal_engine_hardening_phase4.patch
git diff --check
python -m compileall -q .
python -m unittest discover -s tests -p "test_*.py" -v
```

Guardar el avance:

```bash
git add .
git diff --staged
git commit -m "Implementa endurecimiento universal de fase 4"
git push -u origin phase-4-universal-hardening
```

## 17. Despliegue de prueba en Raspberry Pi

En la computadora:

```bash
git switch develop
git push origin develop
```

En la Raspberry Pi:

```bash
cd /home/worksurface/Proyecto_vision_sensor
git status
git switch develop
git pull --ff-only origin develop
python -m unittest discover -s tests -p "test_*.py" -v
```

No ejecutes `git pull` en la Raspberry si `git status` muestra cambios locales sin entender primero de dónde provienen. Guárdalos en un commit o stash, o descarta únicamente las rutas confirmadas.

## 18. Tabla rápida de recuperación

| Situación | Comando recomendado |
|---|---|
| Ver qué cambió | `git status --short` |
| Descartar un archivo no preparado | `git restore --source=HEAD -- archivo` |
| Descartar un archivo preparado y no preparado | `git restore --source=HEAD --staged --worktree -- archivo` |
| Quitar de `git add` sin perder cambios | `git restore --staged -- archivo` |
| Guardar archivos concretos temporalmente | `git stash push -m "mensaje" -- archivo1 archivo2` |
| Validar un patch sin aplicarlo | `git apply --check archivo.patch` |
| Aplicar un patch | `git apply archivo.patch` |
| Revertir un patch | `git apply --reverse archivo.patch` |
| Excluir una ruta del patch | `git apply --exclude=ruta/archivo archivo.patch` |
| Cancelar un merge | `git merge --abort` |
| Ver archivos no rastreados que se borrarían | `git clean -n` |

## 19. Comandos que deben usarse con especial cuidado

Evita estos comandos mientras haya trabajo sin respaldo:

```bash
git reset --hard
git clean -fd
git checkout -- .
git push --force
```

Pueden sobrescribir archivos, borrar contenido no rastreado o reescribir la historia compartida. Para este proyecto, prefiere restaurar rutas específicas, usar stash y validar con `git status` entre cada paso.
