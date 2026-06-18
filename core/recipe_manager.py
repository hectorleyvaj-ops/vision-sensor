import json
import os

class RecipeManager:
    def __init__(self, path="recipes.json"):
        self.path = path
        self._ensure_file()

    # INIT FILE - CREA UNA RECETA CON EL ESQUELETO BASE SI NO EXISTE ARCHIVO PREVIO
    def _ensure_file(self):
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump({"recipes": []}, f, indent=4)

    # LOAD AND SAVE FILE
    def _load_file(self):
        try:
            with open(self.path, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return {"recipes": []}

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

            return {"recipes": []}

        except FileNotFoundError:
            return {"recipes": []}
        
    def _save_file(self, data):
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

        updated = False

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
            self._save_file({"recipes": recipes})

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
        self.ensure_focus(recipe)
        self.ensure_step_params(recipe)
        self.validate(recipe)
        
        data = self._load_file()
        recipes = data.get("recipes", [])

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
        if "name" not in recipe:
            raise ValueError("Falta 'name'")
        
        if "steps" not in recipe:
            raise ValueError("Falta 'steps'")
        
        for step in recipe["steps"]:
            if "tool" not in step:
                raise ValueError("Step sin 'tool'")

    def delete(self, name):
        data = self._load_file()
        recipes = data.get("recipes", [])

        # GUARDA EN LA VARIABLE R LAS RECETAS QUE CUMPLEN LA CONDICION Y SE LAS ENTREGA A NEW_RECIPES
        new_recipes = [r for r in recipes if r["name"] != name] 

        # ACTUALIZA LA LISTA CON LAS RECETAS QUE QUEDARONs
        data["recipes"] = new_recipes
        self._save_file(data)

    def create_recipe(self, name, expected_code="", roi=None, selected=False):

        new_recipe = {
            "name": name,
            "selected": selected,
            "steps": [
                {
                    "tool": "dmtx",
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
            self._save_file({"recipes": recipes})
            return recipes[0]
        
        print("[RECIPES_MANAGER] No hay recetas disponibles, creando DEFAULT...")
        default_recipe = {
            "name": "DEFAULT",
            "selected": True,
            "steps": []
        }
        self.save(default_recipe)
        return default_recipe
        
    def default_focus_config(self):
        return{
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
                "required": True,
            },

            "img_hist": {
                "roi": None,
                "threshold": 0.0,
                "mode": "below",
                "template_paths": [],
                "show_roi": True,
                "required": True,
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

        for step in steps:
            if not isinstance(step, dict):
                continue

            tool_name = step.get("tool")

            if "params" not in step or not isinstance(step["params"], dict):
                step["params"] = {}
                updated = True

            defaults = self.default_tool_params(tool_name)

            for key, value in defaults.items():
                if key not in step["params"]:
                    step["params"][key] = value
                    updated = True

            # Compatibilidad: si alguna receta vieja guardó required al nivel del step,
            # lo copiamos también a params para que ToolEditor y Pipeline lo vean.
            if "required" in step and "required" not in step["params"]:
                step["params"]["required"] = bool(step["required"])
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

        recipe["focus"].update({
            "enabled": bool(focus_config.get("enabled", True)),
            "roi": focus_config.get("roi"),
            "value": focus_config.get("value"),
            "min_score": focus_config.get("min_score"),
            "median_score": focus_config.get("median_score"),
            "peak_score": focus_config.get("peak_score"),
            "verify_on_first_trigger": bool(focus_config.get("verify_on_first_trigger", True)),
            "auto_refocus_if_failed": bool(focus_config.get("auto_refocus_if_failed", True)),
        })

        self.save(recipe)
        return True
    