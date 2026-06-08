from utils.qt_compat import QObject, Signal
import serial
import time

STX = b'\x02'
ETX = b'\x03'

class SerialComm(QObject):
    trigger_received = Signal()
    model_received = Signal(str)

    def __init__(self, port="COM7", baudrate=115200, timeout=1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.ack_recibido = False
        self._running = False

        self.ser = None
        self.max_retries = 3    # MAXIMO DE INTENTOS DE MENSAJE
        self.retry_delay = 0.5      # TIEMPO DE ESPERA ANTES DE RETRY

        self.synced = False
        self.current_model = None

        self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            print(f"[SERIAL] Conectado a {self.port}")

            self.ser.reset_output_buffer()

            self.synced = False

        except Exception as e:
            print(f"[SERIAL][ERROR] No se pudo conectar: {e}")
            self.ser = None

    def start_handshake(self):
        if not self.is_connected():
            return
        
        print("[SERIAL] Iniciando handshake...")

        for attempt in range(5):
            try:
                self.ser.reset_input_buffer()

                packet = self.build_command("SYNC")
                self.ser.write(packet)

                t0 = time.time()

                buffer = b""
                receiving = False

                while time.time() - t0 < 2.0:

                    if self.ser.in_waiting > 0:
                        byte = self.ser.read(1)

                        if byte == STX:
                            buffer = b""
                            receiving = True

                        elif byte == ETX and receiving:
                            receiving = False
                            msg = buffer.decode("utf-8").strip()

                            if msg.startswith("SYNC_OK"):
                                self.process_message(msg)
                                return True
                        elif receiving:
                            buffer += byte
                    time.sleep(0.01)

                print("[SERIAL] Sin respuesta, reintentando handshake...")

            except Exception as e:
                print(f"[SERIAL][ERROR] durante handshake: {e}")
                self.reconnect()
            
            time.sleep(0.5)
        print("[SERIAL] Hanshake fallido")
        return False

    def is_connected(self):
        return self.ser is not None and self.ser.is_open
    
    def reconnect(self):
        print("[SERIAL] Intentando reconectar...")
        if self.ser:
            self.ser.close()
        time.sleep(0.5)
        self.connect()

    def close(self):
        if self.is_connected():
            self.ser.close()
            print("[SERIAL] Puerto cerrado correctamente")

    def start_listening(self):
        self._running = True
        print("[SERIAL] Iniciando escucha...")

        time.sleep(0.5)  # ESPERA BREVE ANTES DE EMPEZAR A LEER
        self.start_handshake()  # INICIA EL HANDSHAKE ANTES DE LEER CUALQUIER MENSAJE

        buffer = b""
        receiving = False

        while self._running:
            if self.is_connected() and self.ser.in_waiting > 0:
                try:
                    byte = self.ser.read(1)

                    if byte == STX:
                        receiving = True
                        buffer = b""
                    elif byte == ETX and receiving:
                        receiving = False
                        msg = buffer.decode("utf-8").strip()
                        self.process_message(msg)
                    elif receiving:
                        buffer += byte

                except Exception as e:
                    print(f"[SERIAL][ERROR] al recibir: {e}")

            time.sleep(0.01)

    def process_message(self, msg: str):
        print(f"[SERIAL] Mensaje recibido: {msg}")

        if msg == "TRIGGER":
            self.trigger_received.emit()

        elif msg == "ACK":
            self.ack_recibido = True

        elif msg.startswith("MODEL:"):
            model = msg.split(":")[1].strip()

            if model == "A":
                model = "MODELO_A"
            elif model == "B":
                model = "MODELO_B"
            elif model == "C":
                model = "MODELO_C"

            print(f"[SERIAL] Modelo detectado: {model}")
            self.model_received.emit(model)

        elif msg.startswith("SYNC_OK"):
            try: 
                parts = msg.split("|")

                for p in parts:
                    if p.startswith("MODEL:"):
                        model = p.split(":")[1].strip()

                        if model == "A":
                            self.current_model = "MODELO_A"
                        elif model == "B":
                            self.current_model = "MODELO_B"
                        elif model == "C":
                            self.current_model = "MODELO_C"

                        print(f"[SERIAL] Sincronizado con modelo: {self.current_model}")
                self.synced = True
                self.model_received.emit(self.current_model)

            except Exception as e:
                print(f"[SERIAL][ERROR] al procesar SYNC_OK: {e}")

    def stop(self):
        self._running = False
        self.close()

    def build_command(self, cmd: str) -> bytes:
        return STX + cmd.encode("utf-8") + ETX
    
    def send_command(self, cmd: str) -> bool:

        if not self.is_connected():
            return {"status": "[ERROR]", "error": "Puerto no conectado"}

        packet = self.build_command(cmd)

        for attemp in range(self.max_retries):
            try:
                print(f"[FSM] Enviando comando: {cmd}, intento: {attemp+1}")
                
                self.ser.reset_input_buffer()   # LIMPIAR BUFFER ANTES DE ENVIAR
                self.ser.reset_output_buffer()
                self.ser.write(packet)          # ENVIAR COMANDO

                t0 = time.time()
                timeout = 1.0
                
                while time.time() - t0 < timeout:
                    if self.ack_recibido:
                        print("[SERIAL] ACK recibido")
                        self.ack_recibido = False
                        return {"status": "OK"}
                    time.sleep(0.01)
                
                print("[FSM] Sin respuesta valida, reintentando...")

            except Exception as e:
                print(f"[SERIAL][ERROR] al enviar: {e}")
                self.reconnect()

            time.sleep(self.retry_delay)

        print("[FSM] Fallo total, reiniciando FSM")
        return{"status": "ERROR", "error": "NO_ACK"}


    