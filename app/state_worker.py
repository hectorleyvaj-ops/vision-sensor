from utils.qt_compat import QObject, Signal, Slot

class StateWorker(QObject):
    finished = Signal()
    log = Signal(str)

    def __init__(self, state_manager):
        super().__init__()
        self.sm = state_manager
        self._running = True

    @Slot()
    def run_once(self):
        # EJECUTA UN CICLO COMPLETO DE LA FSM
        self.log.emit(f"Estado inicial: {self.sm.state}")

        # DISPARAR FSM
        self.sm.step(trigger=True)

        while self._running and self.sm.state != "IDLE":
            self.sm.step()


        self.log.emit("FSM completada")
        self.finished.emit()


    def stop(self):
        self._running = False
