from utils.qt_compat import QObject, Signal, Slot
import time

class StateWorker(QObject):
    cycle_finished = Signal()
    log = Signal(str)

    def __init__(self, state_manager):
        super().__init__()
        self.sm = state_manager
        self._running = True
        self._busy = False

    @Slot()
    def run_once(self):
        if self._busy:
            self.log.emit("[FSM] Worker ocupado, ciclo ignorado")
            return
        
        if not self._running:
            self.log.emit("[FSM] Worker detenido, ciclo ignorado")
            return
        
        self._busy = True

        # EJECUTA UN CICLO COMPLETO DE LA FSM
        try:
            self.log.emit(f"Estado inicial: {self.sm.state}")

            if self.sm.state != "IDLE":
                self.log.emit(f"[FSM] No esta en IDLE, ciclo ignorado. Estado actual: {self.sm.state}")
                return
            
            # DISPARAR FSM
            self.sm.step(trigger=True)

            MAX_STEPS = 50
            steps = 0 

            while self._running and self.sm.state != "IDLE":
                self.sm.step()
                steps += 1

                if steps > MAX_STEPS:
                    self.log.emit("[FSM][ERROR] Se alcanzo el maximo de pasos, forzando reset...")
                    self.sm.reset()
                    break

                time.sleep(0.01)

            self.log.emit("[FSM] Ciclo completado")
        except Exception as e:
            self.log.emit(f"[FSM][ERROR] Error en StateWorker: {e}")
            try:
                self.sm.reset()
            except Exception:
                pass

        finally:
            self._busy = False
            self.cycle_finished.emit()

    @Slot()
    def stop(self):
        self._running = False
