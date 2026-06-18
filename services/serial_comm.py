from utils.qt_compat import QObject, Signal, Slot
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

    connection_lost = Signal(str)
    connection_restored = Signal()

    def __init__(self, port="COM7", baudrate=115200, timeout=1, reset_on_connect=True):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reset_on_connect = reset_on_connect

        self.ack_recibido = False
        self._running = False

        self.ser = None
        self.max_retries = 3
        self.retry_delay = 0.5

        self.synced = False
        self.current_model = None

        self.last_rx_time = time.time()
        self.last_ping_time = 0
        self.ping_interval = 2.0
        self.connection_timeout = 6.0

        self.duplicate_window = 1.5
        self.last_trigger_rx_time = 0
        self.last_result_rx = None
        self.last_result_rx_time = 0
        self.last_reset_rx_time = 0


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

                # RESET USB
                if self.port and self.reset_on_connect:
                    try:
                        print("[SERIAL] Reset USB por DTR...")
                        self.ser.setDTR(False)
                        time.sleep(0.3)
                        self.ser.setDTR(True)
                        time.sleep(2.5)
                    except Exception as e:
                        print(f"[SERIAL][WARNING] No se pudo hacer reset DTR: {e}")

                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()

                self.synced = False
                self.last_rx_time = time.time()
                self.last_ping_time = 0

            print("[SERIAL] Puerto listo para comunicacion")

        except Exception as e:
            print(f"[SERIAL][ERROR] No se pudo conectar: {e}")
            self.ser = None
            self.synced = False

    def is_connected(self):
        return self.ser is not None and self.ser.is_open
    
    def mark_disconnected(self, reason=""):
        """
        Marca el puerto como desconectado aunque pyserial todavía crea que está abierto.
        Esto es necesario en Windows cuando se desconecta USB y quedan errores tipo
        ClearCommError / WriteFile.
        """

        if reason:
            print(f"[SERIAL][DESCONECTADO] {reason}")

        self.synced = False
        self.connection_lost.emit(reason)

        with self._serial_lock:
            try:
                if self.ser is not None:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
            finally:
                self.ser = None

    def reconnect(self):
        print("[SERIAL] Intentando reconectar...")

        with self._serial_lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass

        time.sleep(0.5)
        self.connect()

    def after_reconnect(self):
        """
        Se llama despues de reconectar correctamente el puerto.
        Primero limpia la FSM de la ESP y luego reintenta SYNC.
        """
        if not self.is_connected():
            return False

        print("[SERIAL] Ejecutando recuperacion post-reconexion")
        self.synced = False

        return self.start_handshake()

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

    def send_raw_message(self, message: str):
        """
        Envia un mensaje simple enmarcado con STX/ETX.
        No espera ACK.
        Sirve para avisos asincronos como CALIBRATING o comandos como RESET_FSM.
        """
        try:
            with self._serial_lock:
                if not self.is_connected():
                    return {"status": "ERROR", "error": "Serial no conectado"}

                packet = self.build_command(message)
                self.ser.write(packet)
                self.ser.flush()

            if message not in ("PING",):
                print(f"[SERIAL] Mensaje enviado: {message}")
            return {"status": "OK"}

        except Exception as e:
            print(f"[SERIAL][ERROR] No se pudo enviar mensaje {message}: {e}")
            self.mark_disconnected(f"Fallo al escribir mensaje {message}: {e}")
            return {"status": "ERROR", "error": str(e)}

    def reset_esp_fsm(self):
        """
        Reset logico de la FSM de la ESP.
        Es el recomendado durante reconexion porque libera estados internos
        sin reiniciar fisicamente el microcontrolador.
        """
        print("[SERIAL] Solicitando RESET_FSM a ESP32")
        return self.send_raw_message("RESET_FSM")

    def restart_esp(self):
        """
        Reinicio completo de la ESP32.
        Usar solo si la ESP queda en estado raro y el reset logico no basta.
        """
        print("[SERIAL] Solicitando ESP_RESTART a ESP32")
        result = self.send_raw_message("ESP_RESTART")
        self.synced = False
        return result

    def notify_calibrating(self):
        """
        Aviso hacia la ESP para alargar timeout de vision durante enfoque/calibracion.
        """
        print("[SERIAL] Avisando CALIBRATING a ESP32")
        return self.send_raw_message("CALIBRATING")

    def notify_focus_busy(self):
        """
        Alias opcional para indicar enfoque ocupado.
        """
        print("[SERIAL] Avisando FOCUS_BUSY a ESP32")
        return self.send_raw_message("FOCUS_BUSY")
    
    def notify_rpi_ready(self):
        """
        Avisa a la ESP que la Raspberry ya puede recibir triggers de inspeccion.
        La ESP sigue siendo la autoridad del ciclo; este mensaje solo habilita
        la disponibilidad del sensor inteligente.
        """
        return self.send_raw_message("RPI_READY")
    
    def notify_rpi_not_ready(self):
        """
        Avisa a la ESP que la Raspberry no esta lista para aceptar inspecciones.
        La ESP debe ignorar triggers mientras este estado este activo.
        """
        return self.send_raw_message("RPI_NOT_READY")

    def send_raw_ack(self):
        """Responde ACK a mensajes asincronos de la ESP32."""
        try:
            with self._serial_lock:
                if not self.is_connected():
                    print("[SERIAL][WARNING] No se pudo enviar ACK: puerto no conectado")
                    return False

                self.ser.write(self.build_command("ACK"))
                self.ser.flush()
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
        self.last_rx_time = time.time()
        msg = (msg or "").strip()

        if msg not in ("PONG",):
            print(f"[SERIAL] Mensaje recibido: {msg}")

        if msg == "TRIGGER":
            self.send_raw_ack()
            now = time.time()

            if now - self.last_trigger_rx_time < self.duplicate_window:
                print("[SERIAL] TRIGGER duplicado/reitento ignorado")
                return
            
            self.last_trigger_rx_time = now
            self.trigger_received.emit()

        elif msg in ("OK", "NG"):
            # Resultado final del sistema enviado por la ESP32/PLC.
            # La ESP lo reintentara si no recibe ACK, por eso se responde aqui.
            self.send_raw_ack()
            now = time.time()

            if now - self.last_result_rx_time < self.duplicate_window and self.last_result_rx == msg:
                print(f"[SERIAL] Resultado final duplicado/reitento ignorado: {msg}")
                return
            
            self.last_result_rx_time = now
            self.esp_result_received.emit(msg)

        elif msg == "RESET":
            # RESET enviado por ESP al liberar con llave de calidad.
            self.send_raw_ack()
            now = time.time()

            if now - self.last_reset_rx_time < self.duplicate_window:
                print("[SERIAL] RESET duplicado/reitento ignorado")
                return
            
            self.last_reset_rx_time = now
            self.reset_received.emit()

        elif msg == "ACK":
            # ACK ya se maneja directamente en send_command().
            print("[SERIAL] ACK recibido fuera de envio activo")

        elif msg == "PONG":
            # WatchDog vivo. No imprimir cada PONG para no saturar el log
            return

        elif msg.startswith("MODEL:"):
            # En esta maquina se fuerza MODELO_A, pero se conserva compatibilidad.
            model = msg.split(":", 1)[1].strip()
            model = self.normalize_model(model)

            if not model:
                print("[SERIAL][WARNING] Modelo no reconocido, mensaje ignorado")
                return

            print(f"[SERIAL] Modelo detectado: {model}")
            self.model_received.emit(model)

        elif msg.startswith("SYNC_OK"):
            try:
                was_synced = self.synced
                self.synced = True
                self.current_model = "MODELO_A"

                if not was_synced:
                    self.connection_restored.emit()

                print("[SERIAL] Sincronizado con ESP32")
                # No emitir model_received para evitar recargar receta/enfoque en cada reconexion o handshake
                # Para la prueba del sistema SUMMIT USB solo tiene un modelo que se carga al iniciar app.py
                # MEJORAR: AUTOMATIZAR MODEL_RECEIVED PARA QUE DECIDA POR SU CUENTA SI DEBE O NO EMITIR LA RECETA CUANDO SEA VARIAS O UNA Y NO REENVIAR SI NO CAMBIA DE MODELO
                # self.model_received.emit(self.current_model)

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
            return False

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
                    self.ser.flush()

                    msg = self.read_packet_blocking(timeout=2.0)

                if msg == "ACK":
                    # La ESP puede responder ACK primero y luego SYNC_OK.
                    msg = self.read_packet_blocking(timeout=2.0)

                if msg and msg.startswith("SYNC_OK"):
                    self.process_message(msg)
                    return True

                print("[SERIAL] Sin respuesta SYNC_OK, reintentando handshake...")

            except Exception as e:
                print(f"[SERIAL][ERROR] durante handshake: {e}")
                self.reconnect()

            time.sleep(0.5)

        print("[SERIAL] Handshake fallido")
        self.synced = False
        return False
    
    def is_printable_log(self, text: str) -> bool:
        if not text:
            return False
        
        allowed = 0
        total = len(text)

        for ch in text:
            if ch in "\t" or ch.isprintable():
                allowed += 1

        return total > 0 and (allowed / total) >= 0.85 and "�" not in text
    
    def print_esp_log(self, raw: bytes):
        text = raw.decode("utf-8", errors="replace").strip()

        if not text:
            return
        
        # EN ESTA FUNCION SE MANDA A LLAMAR A UNA QUE SE ASEGURA DE MOSTRAR UN MENSAJE VALIDO, SINO, LO INVALIDA
        if not self.is_printable_log(text):
            print("[ESP_LOG][CLEANER] Basura/ruido serial descartado")
            return
        
        print(f"[ESP_LOG] {text}")

    @Slot()
    def start_listening(self):
        self._running = True
        print("[SERIAL] Iniciando escucha...")

        time.sleep(0.5)

        # Primer handshake al iniciar.
        self.start_handshake()

        buffer = b""
        log_buffer = b""
        receiving = False

        last_reconnect_attempt = 0
        last_try_handshake = 0

        while self._running:
            try:
                now = time.time()

                if self.synced and now - self.last_ping_time >= self.ping_interval:
                    self.last_ping_time = now
                    self.send_raw_message("PING")

                if self.synced and now - self.last_rx_time >= self.connection_timeout:
                    print("[SERIAL][WATCHDOG] ESP32 sin respuesta, sincronizacion perdida")
                    self.synced = False

                if self.is_connected() and not self.synced and now - last_try_handshake > 5.0:
                    last_try_handshake = now
                    self.start_handshake()

                if not self.is_connected():
                        
                    if now - last_reconnect_attempt > 2.0:
                        last_reconnect_attempt = now
                        self.reconnect()

                        if self.is_connected():
                            self.after_reconnect()

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
                            if log_buffer.strip():
                                try:
                                    self.print_esp_log(log_buffer)
                                except Exception:
                                    pass
                            log_buffer = b""
                            receiving = True
                            buffer = b""

                        elif byte == ETX and receiving:
                            receiving = False
                            try:
                                msg = buffer.decode("utf-8").strip()
                                self.process_message(msg)
                            except Exception as e:
                                print(f"[SERIAL][ERROR] decodificando mensaje: {e}")
                            buffer = b""

                        elif receiving:
                            buffer += byte

                        else:
                            if byte in (b"\n", b"\r"):
                                if log_buffer.strip():
                                    self.print_esp_log(log_buffer)
                                log_buffer = b""
                            else:
                                log_buffer += byte

                finally:
                    self._serial_lock.release()

            except Exception as e:
                print(f"[SERIAL][ERROR] al recibir: {e}")
                self.mark_disconnected(f"Fallo al recibir: {e}")
                time.sleep(0.1)

            time.sleep(0.01)

    def send_command(self, cmd: str) -> dict:
        """
        Envia comando a ESP32 esperando ACK.
        Se usa principalmente para resultado de receta OK/NG enviado desde Raspberry.
        """
        if not self.is_connected():
            return {"status": "ERROR", "error": "Puerto no conectado"}

        packet = self.build_command(cmd)

        for attempt in range(self.max_retries):
            try:
                with self._serial_lock:
                    if not self.is_connected():
                        return {"status": "ERROR", "error": "Puerto no encontrado"}

                    print(f"[SERIAL] Enviando comando: {cmd}, intento: {attempt + 1}")

                    # DEJAMOS DE LIMPIAR LOS BUFFERS DE ENTRADA Y SALIDA ANTES DE CADA SEND_COMAND
                    self.ser.write(packet)
                    self.ser.flush()

                    msg = self.read_packet_blocking(timeout=1.0)

                    if msg == "ACK":
                        print("[SERIAL] ACK recibido")
                        return {"status": "OK"}

                    if msg:
                        print(f"[SERIAL] Respuesta inesperada durante envio: {msg}")
                        self.process_message(msg)

                    print("[SERIAL] Sin ACK, reintentando...")

            except Exception as e:
                print(f"[SERIAL][ERROR] al enviar: {e}")
                self.reconnect()

            time.sleep(self.retry_delay)

        print("[SERIAL] Fallo total enviando comando")
        return {"status": "ERROR", "error": "NO_ACK"}

    @Slot()
    def stop(self):
        self._running = False
        self.close()
    