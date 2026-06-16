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

        if self.recipe_manager:
            self.recipe_manager.set_selected(self.active_recipe_name)

    #MAQUINA DE ESTADOS FINITOS - FSM
    def step(self, trigger = False):
        try:
            # IDLE
            if self.state == "IDLE":
                if trigger:
                    print("[FSM]: Trigger recibido - CAPTURING")
                    self.context = {}
                    self.state = "CAPTURING"

            # CAPTURING
            elif self.state == "CAPTURING":

                def get_capture():
                    return self.camera.capture()

                def get_frame():
                    result = get_capture()

                    if result and result.get("status") == "OK":
                        return result.get("frame")

                    error = result.get("error") if isinstance(result, dict) else "captura invalida"
                    print(f"[FSM][WARNING] No se pudo obtener frame fresco: {error}")
                    return None

                self.context["capture_provider"] = get_capture
                self.context["frame_provider"] = get_frame
                print("[FSM] Frame provider listo")
                self.state = "PROCESSING"

            # PROCESSING
            elif self.state == "PROCESSING":
                if not self.recipe_manager or not self.active_recipe_name:
                    self.handle_error("NO_RECIPE", {"error": "No hay receta activa"})
                    return
                
                recipe = self.recipe_manager.get(self.active_recipe_name)

                if not recipe:
                    self.handle_error("INVALID RECIPE", {"error": f"Receta '{self.active_recipe_name}' no encontrada"})
                    return
                
                result = self.processor.run(recipe, self.context)

                if result and result.get("success"):
                    self.inspectionResult.emit("OK")
                    print("[FSM] Resultado final: OK")

                    self.context["result"] = result.get("results")
                    self.context["final_result"] = "OK"
                    self.state = "COMMUNICATING"

                else:
                    self.inspectionResult.emit("NG")
                    print("[FSM] Resultado final: NG")

                    self.context["final_result"] = "NG"
                    errors = result.get("errors") if result else "Resultado invalido del Pipeline"
                    self.handle_error("PROCESS_FAILED", {
                        "error": errors
                    })
                
            # COMMUNICATING
            elif self.state == "COMMUNICATING":
                cmd = self.context.get("final_result", "NG")
                print(f"[FSM] Enviando comando a ESP32: {cmd}")

                result = self.comm.send_command(cmd)

                if result and result.get("status") == "OK":
                    print("[FSM] Confirmacion recibida desde ESP32")
                else:
                    print("[FSM] Fallo en comunicacion, reinicio de ciclo")
                    
                self.reset()

        except Exception as e:
            self.handle_error("FSM_EXEPTION", {"error": str(e)})

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