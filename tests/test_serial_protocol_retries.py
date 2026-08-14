import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

from services.controller_protocol import decode_message, encode_message


if not (
    importlib.util.find_spec("PySide6") or importlib.util.find_spec("PyQt5")
):
    qt_stub = types.ModuleType("utils.qt_compat")

    class QObject:
        def __init__(self, *_args, **_kwargs):
            super().__init__()

    class _BoundSignal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback):
            self.callbacks.append(callback)

        def emit(self, *args):
            for callback in list(self.callbacks):
                callback(*args)

    class Signal:
        def __init__(self, *_args, **_kwargs):
            self.storage_name = None

        def __set_name__(self, _owner, name):
            self.storage_name = f"__test_signal_{name}"

        def __get__(self, instance, _owner):
            if instance is None:
                return self
            signal = instance.__dict__.get(self.storage_name)
            if signal is None:
                signal = _BoundSignal()
                instance.__dict__[self.storage_name] = signal
            return signal

    def Slot(*_args, **_kwargs):
        return lambda function: function

    qt_stub.QObject = QObject
    qt_stub.Signal = Signal
    qt_stub.Slot = Slot
    sys.modules["utils.qt_compat"] = qt_stub

if importlib.util.find_spec("serial") is None:
    serial_stub = types.ModuleType("serial")
    serial_stub.Serial = None
    sys.modules["serial"] = serial_stub

from services.serial_comm import ETX, STX, SerialComm


class FakeSerial:
    def __init__(self):
        self.is_open = True
        self.writes = []
        self.in_waiting = 0

    def write(self, value):
        self.writes.append(bytes(value))
        return len(value)

    def flush(self):
        return None

    def close(self):
        self.is_open = False

    def reset_input_buffer(self):
        return None

    def reset_output_buffer(self):
        return None

    def read(self, _size=1):
        return b""


def framed_payload(packet):
    if not (packet.startswith(STX) and packet.endswith(ETX)):
        raise AssertionError(f"Paquete sin STX/ETX: {packet!r}")
    return packet[1:-1].decode("utf-8")


class SerialProtocolRetryTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSerial()
        patcher = patch("services.serial_comm.serial.Serial", return_value=self.fake)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.comm = SerialComm(
            port="TEST",
            reset_on_connect=False,
            model_map={"A": "MODELO_A"},
        )
        self.comm.synced = True

    def test_duplicate_trigger_is_acked_but_emitted_once(self):
        events = []
        self.comm.cycle_trigger_received.connect(events.append)
        trigger = encode_message("TRIGGER", cycle="BOOT-1", model="A")

        self.comm.process_controller_message(trigger)
        self.comm.process_controller_message(trigger)

        self.assertEqual(len(events), 1)
        acks = [decode_message(framed_payload(value)) for value in self.fake.writes]
        self.assertEqual([item.kind for item in acks], ["ACK", "ACK"])
        self.assertTrue(all(item.fields["STATUS"] == "OK" for item in acks))
        self.assertEqual(self.comm.cycle_guard.active_cycle_id, "BOOT-1")

    def test_duplicate_final_result_is_acked_but_emitted_once(self):
        results = []
        self.comm.esp_result_received.connect(results.append)
        self.comm.cycle_guard.begin("BOOT-1", "A")
        final = encode_message("FINAL_RESULT", cycle="BOOT-1", result="NG")

        self.comm.process_controller_message(final)
        self.comm.process_controller_message(final)

        self.assertEqual(results, ["NG"])
        acks = [decode_message(framed_payload(value)) for value in self.fake.writes]
        self.assertEqual(len(acks), 2)
        self.assertTrue(all(item.fields["STATUS"] == "OK" for item in acks))

    def test_link_timeout_cancels_active_cycle(self):
        cancelled = []
        self.comm.cycle_cancelled.connect(cancelled.append)
        self.comm.cycle_guard.begin("BOOT-1", "A")

        self.comm.mark_link_stale("heartbeat vencido")

        self.assertFalse(self.comm.synced)
        self.assertIsNone(self.comm.cycle_guard.active_cycle_id)
        self.assertEqual(cancelled[0]["cycle_id"], "BOOT-1")


if __name__ == "__main__":
    unittest.main()
