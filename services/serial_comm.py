from utils.qt_compat import QObject, Signal,Slot
import serial
import time
import threading

STX = b'\x02'
ETX = b'\x03'

class SerialComm(QObject):
    trigger_received = Signal()
    model_received = Signal(str)
    esp_result_received = Signal(str)
    reset_received = Signal()

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

        self._serial_lock = threading.RLock()

        self.connect()

    def connect(self):
        try:
            with self._serial_lock:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )

            print(f"[SERIAL] Conectado a {self.port}")
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            self.synced = False

        except Exception as e:
            print(f"[SERIAL][ERROR] No se pudo conectar: {e}")
            self.ser = None

    def is_connected(self):
        return self.ser is not None and self.ser.is_open
    
    def reconnect(self):
        print("[SERIAL] Intentando reconectar...")

        with self._serial_lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
            except:
                pass

        time.sleep(0.5)
        self.connect()

    def close(self):
        with self._serial_lock:
            try:
                if self.is_connected():
                    self.ser.close()
                    self.synced = False
                    print("[SERIAL] Puerto cerrado correctamente")
            except Exception as e:
                print(f"[SERIAL][ERROR] al cerrar puerto: {e}")

    def build_command(self, cmd: str) -> bytes:
        return STX + cmd.encode("utf-8") + ETX
    
    def send_raw_ack(self):
        """Responde ACK a mensajes asincronos de la ESP32."""
        try:
            with self._serial_lock:
                if not self.is_connected():
                    print("[SERIAL][WARNING] No se pudo enviar ACK: puerto no conectado")
                    return False

                self.ser.write(self.build_command("ACK"))
                print("[SERIAL] ACK enviado")
                return True

        except Exception as e:
            print(f"[SERIAL][ERROR] No se pudo enviar ACK: {e}")
            return False

    # PRODUCCION ACTUAL: UNA SOLA RECETA/MODELO.
    # Si en el futuro se vuelven a usar varias recetas, aqui se puede restaurar
    # el mapeo A/B/C -> MODELO_A/MODELO_B/MODELO_C.
    def normalize_model(self, model):
        return "MODELO_A"

    def process_message(self, msg: str):
        msg = (msg or "").strip()
        print(f"[SERIAL] Mensaje recibido: {msg}")

        if msg == "TRIGGER":
            self.trigger_received.emit()

        elif msg in ("OK", "NG"):
            # Resultado final del sistema enviado por la ESP32/PLC.
            # La ESP lo reintentara si no recibe ACK, por eso se responde aqui.
            self.send_raw_ack()
            self.esp_result_received.emit(msg)

        elif msg == "RESET":
            self.send_raw_ack()
            self.reset_received.emit()

        elif msg == "ACK":
            # ACK ya se maneja directamente en send_command().
            print("[SERIAL] ACK recibido fuera de envio activo")

        elif msg.startswith("MODEL:"):
            model = msg.split(":", 1)[1].strip()
            model = self.normalize_model(model)

            if not model:
                print("[SERIAL][WARNING] Modelo no reconocido, mensaje ignorado")
                return

            print(f"[SERIAL] Modelo detectado: {model}")
            self.model_received.emit(model)

        elif msg.startswith("SYNC_OK"):
            try:
                parts = msg.split("|")

                for p in parts:
                    if p.startswith("MODEL:"):
                        model = p.split(":", 1)[1].strip()
                        self.current_model = self.normalize_model(model)

                        print(f"[SERIAL] Sincronizado con modelo: {self.current_model}")

                self.synced = True

                if self.current_model:
                    self.model_received.emit(self.current_model)

            except Exception as e:
                print(f"[SERIAL][ERROR] al procesar SYNC_OK: {e}")

        else:
            print(f"[SERIAL][WARNING] Mensaje no reconocido: {msg}")

    def read_packet_blocking(self, timeout=1.0):
        if not self.is_connected():
            return None
        
        buffer = b""
        receiving = False
        t0 = time.time()

        while time.time() - t0 < timeout:
            if not self.is_connected():
                return None
            
            if self.ser.in_waiting > 0:
                byte = self.ser.read(1)

                if byte == STX:
                    receiving = True
                    buffer = b""

                elif byte == ETX and receiving:
                    receiving = False
                    try:
                        return buffer.decode("utf-8").strip()
                    except Exception:
                        return None
                    
                elif receiving:
                    buffer += byte

            time.sleep(0.005)
        return None

    def start_handshake(self):
        if not self.is_connected():
            return
        
        print("[SERIAL] Iniciando handshake...")

        for attempt in range(5):
            try:
                with self._serial_lock:
                    if not self.is_connected():
                        return False
                    
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()

                    packet = self.build_command("SYNC")
                    self.ser.write(packet)

                    msg = self.read_packet_blocking(timeout=2.0)

                if msg and msg.startswith("SYNC_OK"):
                    self.process_message(msg)
                    return True
                
                print("[SERIAL] Sin respuesta, reintentando handshake...")

            except Exception as e:
                print(f"[SERIAL][ERROR] durante handshake: {e}")
                self.reconnect()

            time.sleep(0.5)

        print("[SERIAL] Handshake fallido")
        return False

    @Slot()
    def start_listening(self):
        self._running = True
        print("[SERIAL] Iniciando escucha...")

        time.sleep(0.5)  # ESPERA BREVE ANTES DE EMPEZAR A LEER
        self.start_handshake()  # INICIA EL HANDSHAKE ANTES DE LEER CUALQUIER MENSAJE

        buffer = b""
        receiving = False

        last_reconnect_attempt = 0

        while self._running:
            try:
                if not self.is_connected():
                    now = time.time()
                    if now - last_reconnect_attempt > 2.0:
                        last_reconnect_attempt = now
                        self.reconnect()
                        if self.is_connected():
                            self.start_handshake()
                    time.sleep(0.05)
                    continue

                acquired = self._serial_lock.acquire(blocking=False)

                if not acquired:
                    time.sleep(0.005)
                    continue
            
                try:
                    if self.is_connected() and self.ser.in_waiting > 0:
                        byte = self.ser.read(1)

                        if byte == STX:
                            receiving = True
                            buffer = b""
                            
                        elif byte == ETX and receiving:
                            receiving = False
                            try:
                                msg = buffer.decode("utf-8").strip()
                                self.process_message(msg)
                            except Exception as e:
                                print(f"[SERIAL][ERROR] decodificando mensaje: {e}")

                        elif receiving:
                            buffer += byte

                finally:
                    self._serial_lock.release()

            except Exception as e:
                print(f"[SERIAL][ERROR] al recibir: {e}")
                time.sleep(0.1)

            time.sleep(0.01)
    
    def send_command(self, cmd: str) -> bool:

        if not self.is_connected():
            return {"status": "[ERROR]", "error": "Puerto no conectado"}

        packet = self.build_command(cmd)

        for attemp in range(self.max_retries):
            try:
                with self._serial_lock:
                    if not self.is_connected():
                        return {"status": "ERROR", "error": "Puerto no encontrado"}
                
                    print(f"[FSM] Enviando comando: {cmd}, intento: {attemp+1}")
                    
                    self.ser.reset_input_buffer()   # LIMPIAR BUFFER ANTES DE ENVIAR
                    self.ser.reset_output_buffer()
                    self.ser.write(packet)          # ENVIAR COMANDO

                    msg = self.read_packet_blocking(timeout=1.0)

                    if msg == "ACK":
                        print("[SERIAL] ACK Recibido")
                        return {"status": "OK"}
                    
                    if msg:
                        print(f"[SERIAL] Respuesta inesperada durante envio: {msg}")
                        self.process_message(msg)

                    print("[SERIAL] Sin ACK, reintentando...")
            
            except Exception as e:
                print(f"[SERIAL][ERROR] al enviar: {e}")
                self.reconnect()

            time.sleep(self.retry_delay)

        print("[FSM] Fallo total, reiniciando FSM")
        return{"status": "ERROR", "error": "NO_ACK"}

    @Slot()
    def stop(self):
        self._running = False
        self.close()
    