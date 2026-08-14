"""Bench test for an ESP32 running ``vision_controller_v1``.

The script does not load recipes, Qt or the camera. It lets phase 9 verify the
serial contract while production remains blocked by ``commissioned=false``.
Run it only with the Worksurface application stopped so both processes do not
open the same serial port.
"""

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.controller_protocol import (  # noqa: E402
    PROTOCOL_VERSION,
    ProtocolError,
    decode_message,
    encode_message,
)

STX = b"\x02"
ETX = b"\x03"


class ProtocolTimeout(RuntimeError):
    pass


def send_message(port, kind, **fields):
    payload = encode_message(kind, **fields)
    port.write(STX + payload.encode("utf-8") + ETX)
    port.flush()
    print(f"TX  {payload}")


def read_message(port, timeout):
    deadline = time.monotonic() + timeout
    payload = bytearray()
    receiving = False
    while time.monotonic() < deadline:
        byte = port.read(1)
        if not byte:
            continue
        if byte == STX:
            payload.clear()
            receiving = True
        elif byte == ETX and receiving:
            text = payload.decode("utf-8").strip()
            print(f"RX  {text}")
            return decode_message(text)
        elif receiving:
            payload.extend(byte)
    raise ProtocolTimeout(f"No llego una trama valida en {timeout:.1f} s")


def wait_for(port, expected_kind, timeout, cycle=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = read_message(port, max(0.1, deadline - time.monotonic()))
        if message.kind != expected_kind:
            continue
        if cycle is not None and message.fields.get("CYCLE") != cycle:
            continue
        return message
    raise ProtocolTimeout(f"No llego {expected_kind}")


def handshake(port, timeout):
    send_message(port, "HELLO", proto=PROTOCOL_VERSION, role="VISION_ENGINE")
    hello = wait_for(port, "HELLO_ACK", timeout)
    hello.require("PROTO", "FW", "READY")
    if hello.fields["PROTO"] != PROTOCOL_VERSION:
        raise ProtocolError(
            f"Firmware usa protocolo {hello.fields['PROTO']}; se requiere 1"
        )
    if hello.fields["READY"] != "1":
        raise ProtocolError(
            f"Controlador no listo: {hello.fields.get('REASON', 'sin detalle')}"
        )

    send_message(port, "PING", seq="SMOKE-1")
    pong = wait_for(port, "PONG", timeout)
    if pong.fields.get("SEQ") != "SMOKE-1":
        raise ProtocolError("PONG no conserva la secuencia del PING")
    return hello


def exercise_cycle(port, timeout, vision_result):
    send_message(port, "READY", state=1)
    wait_for(port, "ACK", timeout)
    print("Esperando trigger fisico del banco...")
    trigger = wait_for(port, "TRIGGER", timeout)
    trigger.require("CYCLE", "MODEL")
    cycle = trigger.fields["CYCLE"]
    model = trigger.fields["MODEL"]

    send_message(port, "ACK", type="TRIGGER", cycle=cycle, status="OK")
    send_message(
        port,
        "VISION_RESULT",
        cycle=cycle,
        result=vision_result,
    )
    vision_ack = wait_for(port, "ACK", timeout, cycle=cycle)
    if (
        vision_ack.fields.get("TYPE") != "VISION_RESULT"
        or vision_ack.fields.get("STATUS") != "OK"
    ):
        raise ProtocolError(f"VISION_RESULT rechazado: {vision_ack.fields}")

    final = wait_for(port, "FINAL_RESULT", timeout, cycle=cycle)
    final.require("RESULT")
    send_message(port, "ACK", type="FINAL_RESULT", cycle=cycle, status="OK")
    return {
        "cycle": cycle,
        "model": model,
        "vision_result": vision_result,
        "final_result": final.fields["RESULT"],
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Prueba aislada del protocolo ESP32 Worksurface fase 9",
    )
    parser.add_argument("--port", required=True, help="COM7 o /dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--exercise-cycle",
        action="store_true",
        help="Ademas del handshake, espera un trigger fisico",
    )
    parser.add_argument(
        "--result",
        choices=("NG", "ERROR", "OK"),
        default="ERROR",
        help="Resultado de vision simulado; ERROR es el valor seguro",
    )
    parser.add_argument(
        "--allow-pass-output",
        action="store_true",
        help="Autoriza enviar OK; puede activar GPIO 32 si sensores coinciden",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.result == "OK" and not args.allow_pass_output:
        print(
            "ERROR: --result OK requiere --allow-pass-output. "
            "Desconecta primero GPIO 32 del PLC y prueba en banco.",
            file=sys.stderr,
        )
        return 2

    try:
        import serial
    except ImportError:
        print("ERROR: instala pyserial en el entorno activo", file=sys.stderr)
        return 2

    try:
        with serial.Serial(
            args.port,
            baudrate=args.baudrate,
            timeout=0.1,
        ) as port:
            time.sleep(1.0)
            port.reset_input_buffer()
            hello = handshake(port, args.timeout)
            print(
                f"Handshake OK: firmware={hello.fields['FW']} "
                f"modelo={hello.fields.get('MODEL', 'sin bits activos')}"
            )

            if args.exercise_cycle:
                result = exercise_cycle(
                    port,
                    max(args.timeout, 30.0),
                    args.result,
                )
                print(
                    "Ciclo OK: "
                    f"{result['cycle']} modelo={result['model']} "
                    f"vision={result['vision_result']} "
                    f"final={result['final_result']}"
                )
            send_message(port, "READY", state=0, reason="SMOKE_TEST_FINISHED")
        return 0
    except (OSError, ProtocolError, ProtocolTimeout) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
