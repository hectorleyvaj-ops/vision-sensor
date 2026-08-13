import json
import os
import re
from core.roi import (
    CANONICAL_FORMAT,
    LEGACY_XYWH_FORMAT,
    ROIError,
    normalize_roi,
)
from core.step_conditions import ConditionError, validate_condition

class RecipeManager:
    SCHEMA_VERSION = 3

    def __init__(self, path="recipes.json", auto_migrate=True):
        self.path = os.fspath(path)
        self.auto_migrate = bool(auto_migrate)
        self._ensure_file()

    def _empty_data(self):
        return {"schema_version": self.SCHEMA_VERSION, "recipes": []}

    # INIT FILE - CREA UNA RECETA CON EL ESQUELETO BASE SI NO EXISTE ARCHIVO PREVIO
    def _ensure_file(self):
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump(self._empty_data(), f, indent=4)

    # LOAD AND SAVE FILE
    def _load_file(self):
        try:
            with open(self.path, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return self._empty_data()

            if "recipes" not in data or not isinstance(data["recipes"], list):
                data["recipes"] = []

            return data

        except json.JSONDecodeError as e:
            print(f"[RECIPE_MANAGER][ERROR] JSON corrupto: {e}")

            bak_path = self.path + ".bak"
            if os.path.exists(bak_path):
                try:
                    with open(bak_path, "r") as f:
                        data = json.load(f)
                    print("[RECIPE_MANAGER] Backup cargado correctamente")
                    return data
                except Exception as e2:
                    print(f"[RECIPE_MANAGER][ERROR] Backup invalido: {e2}")

            return self._empty_data()

        except FileNotFoundError:
            return self._empty_data()

    def _save_file(self, data):
        data = dict(data or {})
        data["schema_version"] = self.SCHEMA_VERSION
        data.setdefault("recipes", [])
        tmp_path = self.path + ".tmp"
        bak_path = self.path + ".bak"

        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as src, open(bak_path, "w") as bak:
                    bak.write(src.read())
            except Exception as e:
                print(f"[RECIPE_MANAGER][WARNING] No se pudo crear backup: {e}")

        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=4)

        os.replace(tmp_path, self.path)

    # PUBLIC API
    # VALIDA Y ARREGLA RECETAS VIEJAS PARA EVITAR CRASHES
    def get_all(self):
        data = self._load_file()
        recipes = data.get("recipes", [])

        schema_version = data.get("schema_version", 1)
        if schema_version != self.SCHEMA_VERSION and not self.auto_migrate:
            raise ValueError(
                f"Recetas schema v{schema_version}; se requiere v{self.SCHEMA_VERSION}"
            )
        if not isinstance(schema_version, int) or schema_version > self.SCHEMA_VERSION:
            raise ValueError(f"Version de recetas no soportada: {schema_version}")

        updated = schema_version != self.SCHEMA_VERSION

        for r in recipes:
            if not isinstance(r, dict):
                continue

            # ASEGURAR STEPS
            if "steps" not in r or not isinstance(r["steps"], list):
                r["steps"] = []
                updated = True

            # ASEGURAR SELECTED
            if "selected" not in r:
                r["selected"] = False
                updated = True

            # ASEGURAR FOCUS
            if self.ensure_focus(r):
                updated = True

            # NORMALIZAR TODAS LAS ROI A [x1, y1, x2, y2]. La herramienta
            # img_hist heredada era la unica que persistia [x, y, w, h].
            if self.ensure_canonical_rois(r, source_schema=schema_version):
                updated = True

            # ASEGURAR IDENTIDAD Y ESTADO DE COMISIONAMIENTO
            if self.ensure_recipe_metadata(r):
                updated = True

            # ASEGURAR PARAMETROS DE STEPS/HERRAMIENTAS
            if self.ensure_step_params(r):
                updated = True

        selected_found = False

        for r in recipes:
            if r.get("selected"):
                if not selected_found:
                    selected_found = True
                else:
                    r["selected"] = False
                    updated = True

        # GUARDAR LOS CAMBIOS
        if updated:
            self._save_file(
                {"schema_version": self.SCHEMA_VERSION, "recipes": recipes}
            )

        return recipes

    # SE ENCARGA DE OBETENER EL DICCIONARIO CON LA INFORMACION DE LA RECETA SELECCIONADA
    def get(self, name):    # NAME CONTIENE LA RECETA QUE BUSCAMOS, YA SEA EL MODELO, PIEZA, ETC.
        recipes = self.get_all()

        for r in recipes:
            if r["name"] == name:
                return r    # REGRESA UN UNICO DICCIONARIO CON LA RECETA ENCONTRADA

        return None

    # GUARDAR O ACTUALIZAR UNA RECETA
    def save(self, recipe):
        self.ensure_recipe_metadata(recipe)
        self.ensure_focus(recipe)
        self.ensure_step_params(recipe)
        self.ensure_canonical_rois(recipe, source_schema=self.SCHEMA_VERSION)
        self.validate(recipe)

        data = self._load_file()
        data["schema_version"] = self.SCHEMA_VERSION
        recipes = data.get("recipes", [])

        for existing in recipes:
            if (
                existing.get("name") != recipe.get("name")
                and existing.get("id") == recipe.get("id")
            ):
                raise ValueError(f"Recipe id duplicado: {recipe.get('id')}")

        # BUSCAR SI YA EXISTE
        for i, r in enumerate(recipes):
            if r["name"] == recipe["name"]:
                recipes[i] = recipe     # UPDATE
                self._save_file(data)
                return

        # AGREGAR SI NO EXISTE
        recipes.append(recipe)
        data["recipes"] = recipes
        self._save_file(data)

    def validate(self, recipe):
        if not isinstance(recipe, dict):
            raise ValueError("La receta debe ser un objeto")

        if not isinstance(recipe.get("name"), str) or not recipe["name"].strip():
            raise ValueError("Falta 'name'")

        if not isinstance(recipe.get("id"), str) or not recipe["id"].strip():
            raise ValueError("Falta 'id'")

        if not isinstance(recipe.get("steps"), list):
            raise ValueError("Falta 'steps'")

        step_ids = set()
        previous_step_ids = []
        for step in recipe["steps"]:
            if not isinstance(step, dict):
                raise ValueError("Step invalido")

            if not isinstance(step.get("tool"), str) or not step["tool"].strip():
                raise ValueError("Step sin 'tool'")

            step_id = step.get("id")
            if not isinstance(step_id, str) or not step_id.strip():
                raise ValueError("Step sin 'id'")

            if step_id in step_ids:
                raise ValueError(f"Step id duplicado: {step_id}")
            step_ids.add(step_id)

            if not isinstance(step.get("enabled", True), bool):
                raise ValueError(f"enabled invalido en {step_id}")
            if not isinstance(step.get("required", True), bool):
                raise ValueError(f"required invalido en {step_id}")
            try:
                validate_condition(
                    step.get("condition"),
                    available_step_ids=previous_step_ids,
                )
            except ConditionError as exc:
                raise ValueError(
                    f"Condicion invalida en {step_id}: {exc}"
                ) from exc
            previous_step_ids.append(step_id)

    def delete(self, name):
        data = self._load_file()
        data["schema_version"] = self.SCHEMA_VERSION
        recipes = data.get("recipes", [])

        # GUARDA EN LA VARIABLE R LAS RECETAS QUE CUMPLEN LA CONDICION Y SE LAS ENTREGA A NEW_RECIPES
        new_recipes = [r for r in recipes if r["name"] != name]

        # ACTUALIZA LA LISTA CON LAS RECETAS QUE QUEDARONs
        data["recipes"] = new_recipes
        self._save_file(data)

    def create_recipe(self, name, expected_code="", roi=None, selected=False):

        new_recipe = {
            "id": self.slugify(name),
            "name": name,
            "selected": selected,
            "commissioned": False,
            "steps": [
                {
                    "id": "dmtx_1",
                    "tool": "dmtx",
                    "enabled": True,
                    "required": True,
                    "condition": {"type": "always"},
                    "params": self.default_tool_params("dmtx")
                }
            ],
            "focus": self.default_focus_config()
        }

        new_recipe["steps"][0]["params"]["expected_code"] = expected_code
        new_recipe["steps"][0]["params"]["roi"] = roi

        self.save(new_recipe)


    def exists(self, name):
        return self.get(name) is not None

    def set_selected(self, name):
        data = self._load_file()
        data["schema_version"] = self.SCHEMA_VERSION
        recipes = data.get("recipes", [])

        found = False

        # PARA CADA RECETA EL CAMPO SELECTED SERA EL VALOR DE EVALUAR EL NOMBRE DE DICHA RECETA CON EL NOMBRE SELECCIONADO
        for r in recipes:
            if r["name"] == name:
                r["selected"] = True
                found = True
            else:
                r["selected"] = False

        if not found and recipes:
            print(f"[RECIPES_MANAGER] '{name}' no existe, fallback: {recipes[0]['name']}")
            recipes[0]["selected"] = True

        data["recipes"] = recipes
        self._save_file(data)

    def get_selected(self):
        recipes = self.get_all()

        for r in recipes:
            if r.get("selected"):
                print(f"[RECIPES_MANAGER] {r['name']} seleccionada: {r.get('selected')}")
                return r

        if recipes:
            print("[RECIPE_MANAGER] No hay receta seleccionada, usando default...")
            recipes[0]["selected"] = True
            self._save_file(
                {"schema_version": self.SCHEMA_VERSION, "recipes": recipes}
            )
            return recipes[0]

        print("[RECIPES_MANAGER] No hay recetas disponibles, creando DEFAULT...")
        default_recipe = {
            "id": "default",
            "name": "DEFAULT",
            "selected": True,
            "commissioned": False,
            "steps": []
        }
        self.save(default_recipe)
        return default_recipe

    def default_focus_config(self):
        return{
            "mode": "calibrated",
            "enabled": False,
            "roi": None,
            "value": None,
            "min_score": None,
            "median_score": None,
            "peak_score": None,
            "verify_on_first_trigger": True,
            "auto_refocus_if_failed": True,
        }

    def default_tool_params(self, tool_name):
        """
        Parametros base por herramienta.
        Sirve para migrar recetas viejas sin romper compatibilidad.
        """
        defaults = {
            "dmtx": {
                "roi": None,
                "expected_code": "",
                "match_mode": "exact",
                "retries": 8,
                "delay": 0.04,
                "min_expected_reads": 2,
                "max_wrong_reads": 0,
                "roi_padding": 12,
                "preprocess": True,
                "upscale": 2.0,
                "decode_timeout_ms": 250,
                "max_total_time": 15.0,
                "show_roi": False,
            },

            "img_hist": {
                "roi": None,
                "threshold": 0.0,
                "mode": "below",
                "template_paths": [],
                "show_roi": True,
            }
        }

        return dict(defaults.get(tool_name, {}))


    def ensure_step_params(self, recipe):
        """
        Asegura que cada step tenga params y que los params de su herramienta
        tengan todas las llaves nuevas sin borrar valores existentes.
        """
        if not isinstance(recipe, dict):
            return False

        steps = recipe.get("steps")
        if not isinstance(steps, list):
            recipe["steps"] = []
            return True

        updated = False

        used_ids = set()
        tool_counters = {}

        for step in steps:
            if not isinstance(step, dict):
                continue

            tool_name = step.get("tool")
            tool_key = self.slugify(tool_name or "step") or "step"
            tool_counters[tool_key] = tool_counters.get(tool_key, 0) + 1

            step_id = step.get("id")
            if not isinstance(step_id, str) or not step_id.strip() or step_id in used_ids:
                candidate = f"{tool_key}_{tool_counters[tool_key]}"
                while candidate in used_ids:
                    tool_counters[tool_key] += 1
                    candidate = f"{tool_key}_{tool_counters[tool_key]}"
                step["id"] = candidate
                step_id = candidate
                updated = True

            used_ids.add(step_id)

            if "params" not in step or not isinstance(step["params"], dict):
                step["params"] = {}
                updated = True

            if "enabled" not in step:
                step["enabled"] = True
                updated = True

            if "required" not in step:
                step["required"] = bool(
                    step["params"].get("required", True)
                )
                updated = True

            if "condition" not in step:
                step["condition"] = {"type": "always"}
                updated = True

            defaults = self.default_tool_params(tool_name)

            for key, value in defaults.items():
                if key not in step["params"]:
                    step["params"][key] = value
                    updated = True

            # required es politica del paso, no un parametro de la herramienta.
            if "required" in step["params"]:
                step["params"].pop("required")
                updated = True

        return updated

    def ensure_canonical_rois(self, recipe, source_schema=None):
        """Migrate every persisted ROI to the schema-v3 xyxy contract.

        Focus and DataMatrix already used xyxy in legacy recipes. Histogram
        comparison used xywh, so only that known representation is converted.
        Invalid rectangles are left untouched and commissioning validation will
        report them without silently changing the intended region.
        """
        if not isinstance(recipe, dict):
            return False

        updated = False
        legacy = not isinstance(source_schema, int) or source_schema < 3

        focus = recipe.get("focus")
        if isinstance(focus, dict) and focus.get("roi") is not None:
            try:
                canonical = normalize_roi(
                    focus.get("roi"),
                    source_format=CANONICAL_FORMAT,
                )
                if canonical != focus.get("roi"):
                    focus["roi"] = canonical
                    updated = True
            except ROIError:
                pass

        for step in recipe.get("steps", []):
            if not isinstance(step, dict):
                continue
            params = step.get("params")
            if not isinstance(params, dict) or params.get("roi") is None:
                continue

            source_format = (
                LEGACY_XYWH_FORMAT
                if legacy and step.get("tool") == "img_hist"
                else CANONICAL_FORMAT
            )
            try:
                canonical = normalize_roi(
                    params.get("roi"),
                    source_format=source_format,
                )
                if canonical != params.get("roi"):
                    params["roi"] = canonical
                    updated = True
            except ROIError:
                pass

        return updated

    @staticmethod
    def slugify(value):
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_")

    def ensure_recipe_metadata(self, recipe):
        if not isinstance(recipe, dict):
            return False

        updated = False
        if not isinstance(recipe.get("id"), str) or not recipe["id"].strip():
            recipe["id"] = self.slugify(recipe.get("name")) or "recipe"
            updated = True

        # Las recetas heredadas ya estaban activas. Las creadas desde el editor
        # comienzan sin comisionar hasta completar herramientas y enfoque.
        if "commissioned" not in recipe:
            recipe["commissioned"] = True
            updated = True

        return updated

    def ensure_focus(self, recipe):
        if "focus" not in recipe or not isinstance(recipe["focus"], dict):
            recipe["focus"] = self.default_focus_config()
            return True

        default = self.default_focus_config()
        updated = False

        for key, value in default.items():
            if key not in recipe["focus"]:
                recipe["focus"][key] = value
                updated = True

        return updated

    def get_focus(self, recipe_name):
        recipe = self.get(recipe_name)

        if not recipe:
            return self.default_focus_config()

        self.ensure_focus(recipe)
        return recipe.get("focus", self.default_focus_config())

    def get_selected_focus(self):
        recipe = self.get_selected()

        if not recipe:
            return self.default_focus_config()

        self.ensure_focus(recipe)
        return recipe.get("focus", self.default_focus_config())

    def update_focus(self, recipe_name, focus_config):
        recipe = self.get(recipe_name)

        if not recipe:
            print(f"[RECIPES_MANAGER][ERROR] No se encontro receta para actualizar enfoque: {recipe_name}")
            return False

        self.ensure_focus(recipe)

        focus_roi = normalize_roi(focus_config.get("roi"))
        recipe["focus"].update({
            "mode": focus_config.get("mode", recipe["focus"].get("mode", "calibrated")),
            "enabled": bool(focus_config.get("enabled", True)),
            "roi": focus_roi,
            "value": focus_config.get("value"),
            "min_score": focus_config.get("min_score"),
            "median_score": focus_config.get("median_score"),
            "peak_score": focus_config.get("peak_score"),
            "verify_on_first_trigger": bool(focus_config.get("verify_on_first_trigger", True)),
            "auto_refocus_if_failed": bool(focus_config.get("auto_refocus_if_failed", True)),
        })

        self.save(recipe)
        return True

    def get_execution_error(self, recipe, available_tools=None):
        """Return a safe, user-facing reason when a recipe cannot run."""
        if not isinstance(recipe, dict):
            return "La receta debe ser un objeto"
        if recipe.get("commissioned") is not True:
            return f"La receta {recipe.get('name')} aun no esta comisionada"
        return self.get_commissioning_error(
            recipe,
            available_tools=available_tools,
        )

    def get_commissioning_error(self, recipe, available_tools=None):
        """Return why a recipe is not safe to mark as commissioned."""
        try:
            self.ensure_recipe_metadata(recipe)
            self.ensure_focus(recipe)
            self.ensure_step_params(recipe)
            self.validate(recipe)
        except ValueError as exc:
            return str(exc)

        steps = recipe.get("steps", [])
        if not steps:
            return f"La receta {recipe.get('name')} no tiene steps"

        available = set(available_tools or [])
        enabled_steps = 0
        for step in steps:
            if not step.get("enabled", True):
                continue
            enabled_steps += 1
            tool_name = step["tool"]
            step_id = step["id"]
            params = step.get("params", {})

            if available and tool_name not in available:
                return f"Herramienta no disponible: {tool_name} ({step_id})"

            if tool_name == "dmtx":
                expected_code = params.get("expected_code")
                if not isinstance(expected_code, str) or not expected_code.strip():
                    return f"El step {step_id} no tiene expected_code valido"

            if tool_name == "img_hist":
                template_paths = params.get("template_paths")
                if not isinstance(template_paths, list) or not template_paths:
                    return f"El step {step_id} no tiene imagenes maestras"

            roi = params.get("roi")
            if tool_name == "dmtx" and roi is None:
                return f"El step {step_id} no tiene ROI valida"
            if roi is not None:
                try:
                    normalize_roi(roi, allow_none=False)
                except ROIError as exc:
                    return f"ROI invalida en {step_id}: {exc}"

            if tool_name == "dmtx":
                match_mode = str(params.get("match_mode", "exact")).lower()
                if match_mode not in ("exact", "prefix"):
                    return (
                        f"Modo de comparacion DataMatrix invalido en "
                        f"{step_id}: {match_mode}"
                    )

        if not enabled_steps:
            return f"La receta {recipe.get('name')} no tiene steps habilitados"

        return None
