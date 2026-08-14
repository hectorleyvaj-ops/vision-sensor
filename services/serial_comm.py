from utils.qt_compat import QObject, Signal, Slot
from services.model_mapping import normalize_model
from services.controller_protocol import (
    PROTOCOL_VERSION,
    CycleGuard,
    ProtocolError,
    decode_message,
    encode_message,
    validate_result,
)
import serial
import time
import threading

STX = b'\x02'
ETX = b'\x03'


class SerialComm(QObject):
    cycle_trigger_received = Signal(object)
    cycle_cancelled = Signal(object)
    model_received = Signal(str)
    esp_result_received = Signal(str)
    reset_received = Signal()

    connection_lost = Signal(str)
    connection_restored = Signal()
    diagnostic_update = Signal(object)

    def __init__(
        self,
        port="COM7",
        baudrate=115200,
        timeout=1,
        reset_on_connect=True,
        model_map=None,
        heartbeat_enabled=False,
        ready_notifications_enabled=False,
    ):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reset_on_connect = reset_on_connect
        self.model_map = {
            str(raw).strip().upper(): str(recipe).strip()
            for raw, recipe in (model_map or {}).items()
        }
        self.heartbeat_enabled = bool(heartbeat_enabled)
        self.ready_notifications_enabled = bool(ready_notifications_enabled)

        self.ack_recibido = False
        self._running = False

        self.ser = None
        self.max_retries = 3
        self.retry_delay = 0.5

        self.synced = False
        self.current_model = None
        self.remote_not_ready_reason = None
        self.cycle_guard = CycleGuard()
        self.heartbeat_sequence = 0

        self.last_rx_time = time.time()
        self.last_ping_time = 0
        self.ping_interval = 2.0
        self.connection_timeout = 6.0

        self.last_result_rx = None
        self.last_result_rx_time = 0
        self.last_final_cycle_id = None
        self.last_pong_sequence = None


        self._serial_lock = threading.RLock()

        self.connect()

    def emit_diagnostic(self, status, message, action="", details=None, blocking=False):
        self.diagnostic_update.emit({
            "key": "controller.runtime",
            "status": status,
            "component": "controller",
            "message": message,
            "action": action,
            "details": dict(details or {}),
            "blocking": bool(blocking),
        })

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
            self.emit_diagnostic(
                "WARNING",
                f"Puerto {self.port} abierto; handshake pendiente",
                details={
                    "port": self.port,
                    "baudrate": self.baudrate,
                    "timeout": self.timeout,
                    "connected": True,
                    "synced": False,
                },
            )

        except Exception as e:
            print(f"[SERIAL][ERROR] No se pudo conectar: {e}")
            self.ser = None
            self.synced = False
            self.emit_diagnostic(
                "ERROR",
                f"No se pudo abrir el controlador en {self.port}: {e}",
                "Revisa el puerto configurado, el cable USB y los permisos",
                details={
                    "port": self.port,
                    "baudrate": self.baudrate,
                    "connected": False,
                    "synced": False,
                },
                blocking=True,
            )

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
        self.remote_not_ready_reason = reason or "Controlador desconectado"
        self.emit_diagnostic(
            "ERROR",
            f"Conexion con controlador perdida: {reason or 'sin detalle'}",
            "Revisa cable, alimentacion y proceso del firmware",
            details={"port": self.port, "connected": False, "synced": False},
            blocking=True,
        )
        cancelled_cycle = self.cycle_guard.cancel()
        if cancelled_cycle:
            self.cycle_cancelled.emit(
                {
                    "cycle_id": cancelled_cycle,
                    "reason": "SERIAL_CONNECTION_LOST",
                }
            )
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

    def mark_link_stale(self, reason):
        """Invalidate protocol state without closing an otherwise open port."""
        if not self.synced and self.cycle_guard.active_cycle_id is None:
            return

        print(f"[SERIAL][WATCHDOG] {reason}")
        self.synced = False
        self.remote_not_ready_reason = reason
        cancelled_cycle = self.cycle_guard.cancel()
        if cancelled_cycle:
            self.cycle_cancelled.emit(
                {
                    "cycle_id": cancelled_cycle,
                    "reason": "CONTROLLER_LINK_TIMEOUT",
                }
            )
        self.emit_diagnostic(
            "ERROR",
            reason,
            "Verifica el firmware, cable USB y heartbeat PING/PONG",
            details={
                "port": self.port,
                "connected": self.is_connected(),
                "synced": False,
            },
            blocking=True,
        )
        self.connection_lost.emit(reason)

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

            if not message.startswith("PING"):
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
        print("[SERIAL] Solicitando RESET logico al controlador")
        return self.send_raw_message(encode_message("RESET", scope="CYCLE"))

    def restart_esp(self):
        """
        Reinicio completo de la ESP32.
        Usar solo si la ESP queda en estado raro y el reset logico no basta.
        """
        print("[SERIAL] Solicitando reinicio al controlador")
        result = self.send_raw_message(encode_message("RESTART"))
        self.synced = False
        return result

    def notify_calibrating(self):
        """
        Aviso hacia la ESP para alargar timeout de vision durante enfoque/calibracion.
        """
        print("[SERIAL] Avisando CALIBRATING a ESP32")
        return self.send_raw_message(
            encode_message(
                "FOCUS",
                state="BUSY",
                cycle=self.cycle_guard.active_cycle_id,
            )
        )

    def notify_focus_busy(self):
        """
        Alias opcional para indicar enfoque ocupado.
        """
        print("[SERIAL] Avisando FOCUS_BUSY a ESP32")
        return self.send_raw_message(
            encode_message(
                "FOCUS",
                state="BUSY",
                cycle=self.cycle_guard.active_cycle_id,
            )
        )

    def notify_rpi_ready(self):
        """
        Avisa a la ESP que la Raspberry ya puede recibir triggers de inspeccion.
        La ESP sigue siendo la autoridad del ciclo; este mensaje solo habilita
        la disponibilidad del sensor inteligente.
        """
        if not self.ready_notifications_enabled:
            return {"status": "SKIPPED", "reason": "READY deshabilitado"}
        return self.send_raw_message(encode_message("READY", state=1))

    def notify_rpi_not_ready(self, reason=None):
        """
        Avisa a la ESP que la Raspberry no esta lista para aceptar inspecciones.
        La ESP debe ignorar triggers mientras este estado este activo.
        """
        if not self.ready_notifications_enabled:
            return {"status": "SKIPPED", "reason": "READY deshabilitado"}
        return self.send_raw_message(
            encode_message("READY", state=0, reason=reason or "NOT_READY")
        )

    def send_protocol_ack(self, ref_type, cycle_id=None, status="OK", error=None):
        return self.send_raw_message(
            encode_message(
                "ACK",
                type=ref_type,
                cycle=cycle_id,
                status=status,
                error=error,
            )
        )

    def normalize_model(self, model):
        return normalize_model(model, self.model_map)

    def process_message(self, msg: str):
        self.process_controller_message((msg or "").strip())

    def process_controller_message(self, payload: str):
        try:
            message = decode_message(payload)
        except ProtocolError as exc:
            print(f"[SERIAL][PROTOCOL][WARNING] Mensaje invalido: {exc}")
            return

        self.last_rx_time = time.time()

        kind = message.kind
        fields = message.fields

        if kind not in ("PONG", "ACK"):
            print(f"[SERIAL][PROTOCOL] Mensaje recibido: {payload}")

        if kind == "HELLO_ACK":
            try:
                message.require("PROTO")
                if fields["PROTO"] != PROTOCOL_VERSION:
                    raise ProtocolError(
                        f"Version incompatible: ESP={fields['PROTO']} RPI={PROTOCOL_VERSION}"
                    )

                was_synced = self.synced
                self.synced = True
                raw_model = fields.get("MODEL")
                normalized_model = self.normalize_model(raw_model) if raw_model else None
                if raw_model and normalized_model is None:
                    raise ProtocolError(f"Modelo de HELLO no configurado: {raw_model}")

                model_changed = (
                    normalized_model is not None
                    and normalized_model != self.current_model
                )
                if normalized_model is not None:
                    self.current_model = normalized_model

                if fields.get("READY") == "0":
                    self.remote_not_ready_reason = fields.get(
                        "REASON",
                        "Controlador remoto no listo",
                    )
                else:
                    self.remote_not_ready_reason = None

                if not was_synced:
                    self.connection_restored.emit()
                if model_changed:
                    self.model_received.emit(self.current_model)

                print(
                    f"[SERIAL][PROTOCOL] Sincronizado con firmware "
                    f"{fields.get('FW', 'desconocido')}"
                )
                self.emit_diagnostic(
                    "PASS",
                    f"Controlador sincronizado con {PROTOCOL_VERSION}",
                    details={
                        "port": self.port,
                        "baudrate": self.baudrate,
                        "connected": True,
                        "synced": True,
                        "firmware": fields.get("FW", "desconocido"),
                        "protocol": fields.get("PROTO"),
                    },
                )
            except ProtocolError as exc:
                self.synced = False
                print(f"[SERIAL][PROTOCOL][ERROR] Handshake rechazado: {exc}")
                self.emit_diagnostic(
                    "ERROR",
                    f"Handshake del controlador rechazado: {exc}",
                    "Instala firmware compatible con vision_controller_v1",
                    details={"port": self.port, "connected": self.is_connected(), "synced": False},
                    blocking=True,
                )
            return

        if kind == "MODEL":
            try:
                message.require("CODE")
                normalized_model = self.normalize_model(fields["CODE"])
                if normalized_model is None:
                    raise ProtocolError(f"Modelo no configurado: {fields['CODE']}")
                if normalized_model != self.current_model:
                    self.current_model = normalized_model
                    self.model_received.emit(normalized_model)
            except ProtocolError as exc:
                print(f"[SERIAL][PROTOCOL][WARNING] MODEL rechazado: {exc}")
            return

        if kind == "TRIGGER":
            cycle_id = fields.get("CYCLE")
            try:
                message.require("CYCLE", "MODEL")
                event = self.cycle_guard.begin(cycle_id, fields["MODEL"])
                normalized_model = self.normalize_model(event["model"])
                if normalized_model is None:
                    raise ProtocolError(
                        f"Modelo no configurado: {event['model']}"
                    )
                self.send_protocol_ack("TRIGGER", cycle_id)
                if event.get("duplicate"):
                    print(
                        f"[SERIAL][PROTOCOL] TRIGGER {cycle_id} repetido; "
                        "ACK reenviado sin ejecutar otro ciclo"
                    )
                    return

                event["recipe_name"] = normalized_model
                if normalized_model != self.current_model:
                    self.current_model = normalized_model
                    self.model_received.emit(normalized_model)
                self.cycle_trigger_received.emit(event)
            except ProtocolError as exc:
                if self.cycle_guard.active_cycle_id == cycle_id:
                    self.cycle_guard.cancel(cycle_id)
                self.send_protocol_ack(
                    "TRIGGER",
                    cycle_id,
                    status="REJECTED",
                    error=str(exc),
                )
                print(f"[SERIAL][PROTOCOL][WARNING] TRIGGER rechazado: {exc}")
            return

        if kind == "FINAL_RESULT":
            cycle_id = fields.get("CYCLE")
            try:
                message.require("CYCLE", "RESULT")
                result = validate_result(fields["RESULT"])

                if cycle_id == self.last_final_cycle_id:
                    if result != self.last_result_rx:
                        raise ProtocolError(
                            f"Resultado final contradictorio para {cycle_id}: "
                            f"anterior={self.last_result_rx}, recibido={result}"
                        )
                    self.send_protocol_ack("FINAL_RESULT", cycle_id)
                    print(
                        f"[SERIAL][PROTOCOL] FINAL_RESULT {cycle_id} repetido; "
                        "ACK reenviado"
                    )
                    return

                self.cycle_guard.close(cycle_id)
                self.send_protocol_ack("FINAL_RESULT", cycle_id)
                self.last_result_rx = result
                self.last_final_cycle_id = cycle_id
                self.last_result_rx_time = time.time()
                self.esp_result_received.emit(result)
            except ProtocolError as exc:
                self.send_protocol_ack(
                    "FINAL_RESULT",
                    cycle_id,
                    status="REJECTED",
                    error=str(exc),
                )
                print(
                    f"[SERIAL][PROTOCOL][WARNING] "
                    f"Resultado tardio rechazado: {exc}"
                )
            return

        if kind == "CANCEL":
            cycle_id = fields.get("CYCLE")
            try:
                cancelled = self.cycle_guard.cancel(cycle_id)
                self.send_protocol_ack("CANCEL", cancelled or cycle_id)
                event = {
                    "cycle_id": cancelled or cycle_id,
                    "reason": fields.get("REASON", "CANCELLED"),
                }
                self.cycle_cancelled.emit(event)
                self.reset_received.emit()
            except ProtocolError as exc:
                self.send_protocol_ack(
                    "CANCEL", cycle_id, status="REJECTED", error=str(exc)
                )
                print(f"[SERIAL][PROTOCOL][WARNING] CANCEL rechazado: {exc}")
            return

        if kind == "RESET":
            cycle_id = fields.get("CYCLE")
            try:
                if cycle_id:
                    cancelled = self.cycle_guard.cancel(cycle_id)
                else:
                    cancelled = self.cycle_guard.cancel()
                self.send_protocol_ack("RESET", cancelled or cycle_id)
                if cancelled:
                    self.cycle_cancelled.emit(
                        {
                            "cycle_id": cancelled,
                            "reason": fields.get("REASON", "REMOTE_RESET"),
                        }
                    )
                self.reset_received.emit()
            except ProtocolError as exc:
                self.send_protocol_ack(
                    "RESET", cycle_id, status="REJECTED", error=str(exc)
                )
            return

        if kind == "PONG":
            self.last_pong_sequence = fields.get("SEQ")
            return

        if kind == "ACK":
            print(
                f"[SERIAL][PROTOCOL] ACK asincrono: "
                f"{fields.get('TYPE', 'UNKNOWN')} {fields.get('CYCLE', '')}"
            )
            return

        if kind == "ERROR":
            print(
                f"[SERIAL][PROTOCOL][REMOTE_ERROR] "
                f"{fields.get('CODE', 'UNKNOWN')}: "
                f"{fields.get('DETAIL', '')}"
            )
            return

        print(f"[SERIAL][PROTOCOL][WARNING] Tipo no reconocido: {kind}")

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

                    handshake = encode_message(
                        "HELLO",
                        proto=PROTOCOL_VERSION,
                        role="VISION_ENGINE",
                    )
                    packet = self.build_command(handshake)
                    self.ser.write(packet)
                    self.ser.flush()

                    msg = self.read_packet_blocking(timeout=2.0)

                expected_prefix = "HELLO_ACK"
                if msg and msg.startswith(expected_prefix):
                    self.process_message(msg)
                    return True

                print(
                    f"[SERIAL] Sin respuesta {expected_prefix}, "
                    "reintentando handshake..."
                )

            except Exception as e:
                print(f"[SERIAL][ERROR] durante handshake: {e}")
                self.reconnect()

            time.sleep(0.5)

        print("[SERIAL] Handshake fallido")
        self.synced = False
        self.emit_diagnostic(
            "ERROR",
            "El controlador no respondio al handshake",
            "Verifica firmware, baudrate y protocolo vision_controller_v1",
            details={"port": self.port, "connected": self.is_connected(), "synced": False},
            blocking=True,
        )
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

                if (
                    self.heartbeat_enabled
                    and self.synced
                    and now - self.last_ping_time >= self.ping_interval
                ):
                    self.last_ping_time = now
                    self.heartbeat_sequence += 1
                    ping = encode_message("PING", seq=self.heartbeat_sequence)
                    self.send_raw_message(ping)

                if (
                    self.heartbeat_enabled
                    and self.synced
                    and now - self.last_rx_time >= self.connection_timeout
                ):
                    self.mark_link_stale(
                        "ESP32 sin respuesta al heartbeat; sincronizacion perdida"
                    )

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

    def send_command(self, cmd: str, cycle_id=None) -> dict:
        """
        Envia comando a ESP32 esperando ACK.
        Envia OK/NG cuando existe decision de producto y ERROR cuando vision no
        pudo obtenerla. TIMEOUT interno se comunica como ERROR.
        """
        if not self.is_connected():
            return {"status": "ERROR", "error": "Puerto no conectado"}

        try:
            result_value = validate_result(cmd)
            cycle = self.cycle_guard.require_active(cycle_id)
            command = encode_message(
                "VISION_RESULT",
                cycle=cycle,
                result=result_value,
            )
        except ProtocolError as exc:
            return {"status": "ERROR", "error": str(exc)}

        packet = self.build_command(command)

        for attempt in range(self.max_retries):
            try:
                with self._serial_lock:
                    if not self.is_connected():
                        return {"status": "ERROR", "error": "Puerto no encontrado"}

                    print(f"[SERIAL] Enviando comando: {command}, intento: {attempt + 1}")

                    # DEJAMOS DE LIMPIAR LOS BUFFERS DE ENTRADA Y SALIDA ANTES DE CADA SEND_COMAND
                    self.ser.write(packet)
                    self.ser.flush()

                    msg = self.read_packet_blocking(timeout=1.0)

                    ack_matches = False
                    if msg:
                        try:
                            ack = decode_message(msg)
                            ack_matches = (
                                ack.kind == "ACK"
                                and ack.fields.get("TYPE") == "VISION_RESULT"
                                and ack.fields.get("CYCLE") == str(cycle_id)
                                and ack.fields.get("STATUS", "OK") == "OK"
                            )
                        except ProtocolError:
                            ack_matches = False

                    if ack_matches:
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
