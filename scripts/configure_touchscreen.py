"""Generate reversible libinput udev rules without applying a blind transform."""

import argparse
from pathlib import Path


MATRICES = {
    "normal": (1, 0, 0, 0, 1, 0),
    "invert-x": (-1, 0, 1, 0, 1, 0),
    "invert-y": (1, 0, 0, 0, -1, 1),
    "rotate-180": (-1, 0, 1, 0, -1, 1),
    "rotate-90": (0, -1, 1, 1, 0, 0),
    "rotate-270": (0, 1, 0, -1, 0, 1),
}


def udev_rule(vendor, product, profile):
    if profile not in MATRICES:
        raise ValueError("Perfil tactil no soportado")
    if not vendor or not product:
        raise ValueError("Se requieren vendor y product estables de udev")
    matrix = " ".join(str(value) for value in MATRICES[profile])
    return 'ACTION=="add|change", SUBSYSTEM=="input", ENV{{ID_VENDOR_ID}}=="{}", ENV{{ID_MODEL_ID}}=="{}", ENV{{LIBINPUT_CALIBRATION_MATRIX}}="{}"\n'.format(vendor, product, matrix)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor")
    parser.add_argument("--product")
    parser.add_argument("--profile", choices=sorted(MATRICES))
    parser.add_argument("--rule", default="/etc/udev/rules.d/99-vision-sensor-touchscreen.rules")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    target = Path(args.rule)
    if args.rollback:
        if target.exists():
            target.unlink()
        print("Regla tactil retirada. Reinicia o reconecta el dispositivo.")
        return 0
    if not args.vendor or not args.product or not args.profile:
        parser.error("Selecciona vendor, product y profile despues de identificar el touchscreen.")
    rule = udev_rule(args.vendor, args.product, args.profile)
    print(rule, end="")
    if args.apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = target.with_suffix(target.suffix + ".bak")
        if target.exists():
            backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        target.write_text(rule, encoding="utf-8")
        print("Regla escrita. Ejecuta udevadm control --reload-rules y reinicia o reconecta el touch.")
    else:
        print("Revision: usa --apply solo despues de confirmar vendor, product y perfil.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
