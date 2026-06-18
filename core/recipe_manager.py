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
        with open(self.path, "r") as f:
            return json.load(f)
        
    def _save_file(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)

    # PUBLIC API
    # VALIDA Y ARREGLA RECETAS VIEJAS PARA EVITAR CRASHES
    def get_all(self):
        data = self._load_file()
        recipes = data.get("recipes", [])

        upadated = False

        for r in recipes:
            if not isinstance(r, dict):
                continue

            # ASEGURAR STEPS
            if "steps" not in r or not isinstance(r["steps"], list):
                r["steps"] = []
                upadated = True

            # ASEGURAR SELECTED
            if "selected" not in r:
                r["selected"] = False
                upadated = True

            # ASEGURAR FOCUS
            if self.ensure_focus(r):
                upadated = True

        selected_found = False

        for r in recipes:
            if r.get("selected"):
                if not selected_found:
                    selected_found = True
                else:
                    r["selected"] = False
                    upadated = True

        # GUARDAR LOS CAMBIOS
        if upadated:
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

    def create_recipe(self, name, selected=False):

        new_recipe = {
            "name": name,
            "selected": selected,
            "steps": [],
            "focus": self.default_focus_config()
        }

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
    