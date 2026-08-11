# ES QUIEN MANEJA LA MAQUINA DE ESTADOS Y ORQUESTA A LOS SCRIPTS
# CONTROLA EL FLUJO DEL PROCESO Y CORRE EN BUCLE

from utils.qt_compat import Signal, QObject
import time
import threading
from core.outcome import controller_result_for_pipeline
from tools.result import ToolStatus

class StateManager(QObject):
    inspectionResult = Signal(str)
    def __init__(
        self,
        camera,
        processor,
        comunicator,
        mechanical_settle_ms=0,
        inspection_timeout_seconds=20.0,
    ):
        super().__init__()
        self.camera = camera
        self.processor = processor
        self.comm = comunicator
        self.mechanical_settle_ms = max(0, int(mechanical_settle_ms))
        self.inspection_timeout_seconds = max(
            0.1,
            float(inspection_timeout_seconds),
        )

        self.state = "IDLE"
        self.context = {}

        self.recipe = None
        self.active_recipe_name = None
        self.recipe_manager = None
        self.pending_cycle = None
        self.cancel_requested = threading.Event()
        self.cancel_reason = None

    def prepare_cycle(self, cycle_context):
        if not isinstance(cycle_context, dict):
            raise ValueError("El contexto de ciclo debe ser un diccionario")
        if not cycle_context.get("cycle_id"):
            raise ValueError("El protocolo del controlador requiere cycle_id")
        if self.state != "IDLE" or self.pending_cycle is not None:
            raise RuntimeError("La FSM ya tiene un ciclo pendiente o activo")

        self.cancel_requested.clear()
        self.cancel_reason = None
        self.pending_cycle = dict(cycle_context)

    def cancel_cycle(self, cycle_id=None, reason="CANCELLED"):
        active_cycle = self.context.get("cycle_id") if self.context else None
        pending_cycle = (
            self.pending_cycle.get("cycle_id")
            if isinstance(self.pending_cycle, dict)
            else None
        )
        known_cycle = active_cycle or pending_cycle
        if cycle_id and known_cycle and str(cycle_id) != str(known_cycle):
            print(
                f"[FSM][WARNING] Cancelacion ignorada para ciclo {cycle_id}; "
                f"ciclo local={known_cycle}"
            )
            return False

        self.cancel_reason = reason
        self.cancel_requested.set()
        return True

    def load_selected_recipe(self):
        if not self.recipe_manager:
            return

        selected = self.recipe_manager.get_selected()

        if selected:
            self.active_recipe_name = selected["name"]
            print(f"[STATE_MANAGER] Receta activa cargada: {self.active_recipe_name}")

    def set_recipe_manager(self, recipe_manager):
        self.recipe_manager = recipe_manager

    def set_active_recipe(self, name):
        self.active_recipe_name = name

        if self.recipe_manager:
            self.recipe_manager.set_selected(self.active_recipe_name)

    #MAQUINA DE ESTADOS FINITOS - FSM
    def step(self, trigger = False):
        try:
            if self.cancel_requested.is_set():
                print(f"[FSM] Ciclo cancelado: {self.cancel_reason}")
                self.reset()
                return

            # IDLE
            if self.state == "IDLE":
                if trigger:
                    print("[FSM]: Trigger recibido - CAPTURING")
                    self.context = dict(self.pending_cycle or {})
                    self.pending_cycle = None
                    self.context["cancel_event"] = self.cancel_requested
                    self.context["started_at"] = time.monotonic()
                    self.context["deadline"] = (
                        self.context["started_at"]
                        + self.inspection_timeout_seconds
                    )
                    self.state = "CAPTURING"

            # CAPTURING
            elif self.state == "CAPTURING":

                if self.mechanical_settle_ms > 0:
                    print(
                        f"[FSM] Esperando asentamiento mecanico: "
                        f"{self.mechanical_settle_ms} ms"
                    )
                    if self.cancel_requested.wait(
                        self.mechanical_settle_ms / 1000.0
                    ):
                        print(
                            f"[FSM] Ciclo cancelado durante asentamiento: "
                            f"{self.cancel_reason}"
                        )
                        self.reset()
                        return

                if time.monotonic() >= self.context.get("deadline", 0):
                    self.handle_error(
                        "CAPTURE_TIMEOUT",
                        {"error": "Timeout antes de capturar el frame"},
                    )
                    return

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

                if self.cancel_requested.is_set():
                    print(
                        f"[FSM] Resultado descartado por cancelacion: "
                        f"{self.cancel_reason}"
                    )
                    self.reset()
                    return

                pipeline_status = (
                    result.get("status") if isinstance(result, dict) else None
                )
                controller_result = controller_result_for_pipeline(
                    pipeline_status
                )

                if controller_result == "OK":
                    self.inspectionResult.emit("OK")
                    print("[FSM] Resultado final: OK")

                    self.context["result"] = result.get("results")
                    self.context["final_result"] = "OK"
                    self.state = "COMMUNICATING"

                elif controller_result == "NG":
                    self.inspectionResult.emit("NG")
                    print("[FSM] Resultado final: NG")

                    self.context["result"] = result.get("results")
                    self.context["final_result"] = "NG"
                    self.context["pipeline_status"] = pipeline_status
                    self.context["pipeline_errors"] = result.get("errors", [])
                    self.state = "COMMUNICATING"

                else:
                    self.inspectionResult.emit("ERROR")
                    errors = (
                        result.get("errors")
                        if isinstance(result, dict)
                        else "Resultado invalido del Pipeline"
                    )
                    print(
                        f"[FSM] Inspeccion sin decision de producto: "
                        f"{pipeline_status or 'ERROR'}"
                    )
                    self.context["pipeline_status"] = (
                        pipeline_status or ToolStatus.ERROR.value
                    )
                    self.handle_error("PROCESS_ERROR", {"error": errors})

            # COMMUNICATING
            elif self.state == "COMMUNICATING":
                cmd = self.context.get("final_result", "NG")
                print(f"[FSM] Enviando comando a ESP32: {cmd}")

                result = self.comm.send_command(
                    cmd,
                    cycle_id=self.context.get("cycle_id"),
                )

                if result and result.get("status") == "OK":
                    print("[FSM] Confirmacion recibida desde ESP32")
                else:
                    print("[FSM] Fallo en comunicacion, reinicio de ciclo")

                self.reset()

        except Exception as e:
            self.handle_error("FSM_EXEPTION", {"error": str(e)})

    # MANEJA LOS LOGS DE ERROR PARA REDIRECCIONARLOS AL LOG EN LA INTERFAZ PRINCIPAL EN UN FUTURO
    def handle_error(self, stage, details):
        print(f"[STATE_MANAGER][FSM] Error at stage {stage}: {details.get('error')}")

        # ERROR significa que vision no obtuvo una decision de producto. El
        # controlador conserva la autoridad para llevar la maquina a seguro.
        self.context["final_result"] = "ERROR"

        # ENVIAR ERROR DE EJECUCION SIN DISFRAZARLO COMO RECHAZO DE PIEZA
        self.state = "COMMUNICATING"

    def reset(self):
        print("[FSM] Reset - IDLE")
        self.state = "IDLE"
        self.context = {}
        self.pending_cycle = None
        self.cancel_reason = None
        self.cancel_requested.clear()
