# ES QUIEN MANEJA LA MAQUINA DE ESTADOS Y ORQUESTA A LOS SCRIPTS
# CONTROLA EL FLUJO DEL PROCESO Y CORRE EN BUCLE

from utils.qt_compat import Signal, QObject

class StateManager(QObject):
    inspectionResult = Signal(str)
    def __init__(self, camera, processor, comunicator):
        super().__init__()
        self.camera = camera
        self.processor = processor
        self.comm = comunicator
        self.state = "IDLE"
        self.context = {}
        #EXAMPLE OF RECIPE IT WOULD BE TAKEN BY RECIPE_LOADER 
        #MEJORA: CREAR RECIPE_LOADER E INTERFAZ PARA GENERAR RECETAS
        self.recipe = None
        self.active_recipe_name = None
        self.recipe_manager = None

    def load_selected_recipe(self):
        if not self.recipe_manager:
            return
        
        selected = self.recipe_manager.get_selected()

        if selected:
            self.active_recipe_name = selected["name"]
            print(f"Receta activa cargada: {self.active_recipe_name}")

    def set_recipe_manager(self, recipe_manager):
        self.recipe_manager = recipe_manager

    def set_active_recipe(self, name):
        self.active_recipe_name = name
        self.recipe_manager.set_selected(self.active_recipe_name)

    #MAQUINA DE ESTADOS FINITOS - FSM
    def step(self, trigger = False):
        if self.state == "IDLE":
            if trigger:
                print("[FSM]: Trigger recibido - CAPTURING")
                self.state = "CAPTURING"

        elif self.state == "CAPTURING":

            def get_frame():
                result = self.camera.capture()

                if result["status"] == "OK":
                    return result["frame"]

            self.context["frame_provider"] = get_frame
            print("[FSM] Frame capturado correctamente")
            self.state = "PROCESSING"

            

        elif self.state == "PROCESSING":
            self.context["frame"] = self.context.get("frame")

            if not self.recipe_manager or not self.active_recipe_name:
                self.handle_error("NO_RECIPE", {"error": "No hay receta activa"})
                return
            
            recipe = self.recipe_manager.get(self.active_recipe_name)

            if not recipe:
                self.handle_error("INVALID RECIPE", {"error": f"Receta '{self.active_recipe_name}' no encontrada"})
                return
            
            result = self.processor.run(recipe, self.context)

            if result["success"]:
                self.inspectionResult.emit("OK")
                print("[FSM] Resultado final: OK")
                self.context["result"] = result["results"]
                self.context["final_result"] = "OK"
                self.state = "COMMUNICATING"
            else:
                self.inspectionResult.emit("NG")
                print("[FSM] Resultado final: NG")
                self.context["final_result"] = "NG"
                self.handle_error("PROCESS_FAILED", {
                    "error": result["errors"]
                })
            
        elif self.state == "COMMUNICATING":
            cmd = self.context.get("final_result", "NG")
            print(f"[FSM] Enviando comando a ESP32: {cmd}")

            result = self.comm.send_command(cmd)

            if result["status"] == "OK":
                print("[FSM] Confirmacion recibida desde ESP32")
                self.reset()
            else:
                print("[FSM] Fallo en comunicacion, reinicio de ciclo")
                self.reset()

    # MANEJA LOS LOGS DE ERROR PARA REDIRECCIONARLOS AL LOG EN LA INTERFAZ PRINCIPAL EN UN FUTURO
    def handle_error(self, stage, details):
        print(f"Error at stage {stage}: {details.get('error')}")
        # FORZAR NG PARA CONTINUAR EN ESP
        self.context["final_result"] = "NG"

        # ENVIAR RESULTADO NG FORZADO
        self.state = "COMMUNICATING"

    def reset(self):
        print("[FSM] Reset - IDLE")
        self.state = "IDLE"
        self.context = {}