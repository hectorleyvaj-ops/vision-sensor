import cv2
import time
import re
import json
import argparse
import subprocess
from pathlib import Path


def run_cmd(cmd, show=False):
    result = subprocess.run(cmd, capture_output=True, text=True)
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if show:
        print("$", " ".join(cmd))
        print("RC:", result.returncode)
        if stdout:
            print("OUT:", stdout)
        if stderr:
            print("ERR:", stderr)

    return result.returncode, stdout, stderr


def list_controls(device):
    rc, out, err = run_cmd(["v4l2-ctl", "-d", device, "--list-ctrls"])
    text = out + "\n" + err

    controls = set()
    for line in text.splitlines():
        line = line.strip()
        match = re.match(r"^([a-zA-Z0-9_]+)\s", line)
        if match:
            controls.add(match.group(1))

    return controls, text


def parse_focus_range(list_ctrls_text):
    """
    Intenta leer algo como:
    focus_absolute 0x009a090a (int) : min=1 max=1023 step=1 default=1 value=...
    """
    for line in list_ctrls_text.splitlines():
        if "focus_absolute" not in line:
            continue

        min_match = re.search(r"min=(-?\d+)", line)
        max_match = re.search(r"max=(-?\d+)", line)
        step_match = re.search(r"step=(-?\d+)", line)

        if min_match and max_match:
            min_v = int(min_match.group(1))
            max_v = int(max_match.group(1))
            step_v = int(step_match.group(1)) if step_match else 1
            return min_v, max_v, max(1, step_v)

    return 1, 1023, 1


def has_control(controls, name):
    return name in controls


def set_ctrl(device, control, value, verify=True):
    rc, out, err = run_cmd(
        ["v4l2-ctl", "-d", device, f"--set-ctrl={control}={value}"],
        show=False
    )

    if rc != 0:
        print(f"[V4L2][ERROR] No se pudo setear {control}={value}: {err or out}")
        return False

    if verify:
        actual = get_ctrl(device, control)
        print(f"[V4L2] {control}: pedido={value}, leído={actual}")

    return True


def get_ctrl(device, control):
    rc, out, err = run_cmd(
        ["v4l2-ctl", "-d", device, f"--get-ctrl={control}"],
        show=False
    )

    text = (out or err or "").strip()
    match = re.search(r"(-?\d+)\s*$", text)

    if match:
        return int(match.group(1))

    print(f"[V4L2][WARNING] No se pudo leer {control}: {text}")
    return None


def apply_base_controls(device, controls):
    """
    Debe parecerse lo más posible a tu producción actual.
    Si algún control no existe, se omite.
    """
    optional_controls = {
        "auto_exposure": 3,
        "exposure_dynamic_framerate": 1,
        "gain": 10,
        "brightness": 0,
        "contrast": 32,
        "sharpness": 3,
        "power_line_frequency": 1,
        "white_balance_automatic": 1,
    }

    for control, value in optional_controls.items():
        if has_control(controls, control):
            set_ctrl(device, control, value, verify=False)


def open_camera(device, width, height, fps):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)

    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir cámara: {device}")

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    for _ in range(10):
        cap.read()
        time.sleep(0.03)

    real_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    real_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    real_fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"[CAMERA] Resolución activa: {real_width}x{real_height} @ {real_fps}")

    return cap


def clamp_roi(roi, frame):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = roi

    x1 = max(0, min(w - 1, int(x1)))
    y1 = max(0, min(h - 1, int(y1)))
    x2 = max(0, min(w, int(x2)))
    y2 = max(0, min(h, int(y2)))

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


def focus_score(frame, roi=None):
    try:
        if roi is not None:
            roi = clamp_roi(roi, frame)
            if roi is not None:
                x1, y1, x2, y2 = roi
                frame = frame[y1:y2, x1:x2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return int(cv2.Laplacian(gray, cv2.CV_64F).var())

    except Exception:
        return -1


def read_good_frame(cap, retries=10):
    for _ in range(retries):
        ret, frame = cap.read()
        if ret and frame is not None and hasattr(frame, "shape") and frame.size > 0:
            return frame
        time.sleep(0.03)
    return None


def select_focus_roi(cap):
    frame = read_good_frame(cap)

    if frame is None:
        raise RuntimeError("No se pudo leer frame para seleccionar ROI")

    print("[ROI] Selecciona el área de enfoque y presiona ENTER o SPACE.")
    print("[ROI] Presiona C para cancelar y usar frame completo.")

    selected = cv2.selectROI("Seleccionar ROI de enfoque", frame, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow("Seleccionar ROI de enfoque")

    x, y, w, h = selected

    if w <= 0 or h <= 0:
        print("[ROI] Sin ROI seleccionado. Se usará frame completo.")
        return None

    roi = (int(x), int(y), int(x + w), int(y + h))
    print(f"[ROI] ROI seleccionado: {roi}")
    return roi


def capture_focus_score(cap, roi=None, discard=5, samples=7, delay=0.04, preview=True, focus_value=None):
    for _ in range(discard):
        cap.read()
        time.sleep(delay)

    scores = []
    best_frame = None
    best_score = -1

    for _ in range(samples):
        frame = read_good_frame(cap)

        if frame is None:
            time.sleep(delay)
            continue

        score = focus_score(frame, roi)
        scores.append(score)

        if score > best_score:
            best_score = score
            best_frame = frame.copy()

        if preview:
            shown = frame.copy()

            if roi is not None:
                x1, y1, x2, y2 = clamp_roi(roi, shown)
                cv2.rectangle(shown, (x1, y1), (x2, y2), (0, 255, 0), 2)

            text = f"focus={focus_value} score={score}"
            cv2.putText(shown, text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            cv2.imshow("Manual focus test", shown)
            cv2.waitKey(1)

        time.sleep(delay)

    if not scores:
        return -1, -1, best_frame

    scores_sorted = sorted(scores)
    median_score = scores_sorted[len(scores_sorted) // 2]

    return median_score, best_score, best_frame


def sweep_focus(device, cap, roi, values, label, settle=0.12, preview=True):
    best_value = None
    best_median_score = -1
    best_peak_score = -1
    results = []

    print(f"\n[SWEEP] Iniciando barrido {label}. Valores: {len(values)}")

    for value in values:
        print(f"[SWEEP] {label} focus_absolute={value}")

        if not set_ctrl(device, "focus_absolute", value, verify=False):
            continue

        time.sleep(settle)

        median_score, peak_score, _ = capture_focus_score(
            cap,
            roi=roi,
            discard=4,
            samples=7,
            delay=0.035,
            preview=preview,
            focus_value=value
        )

        results.append({
            "focus": int(value),
            "median_score": int(median_score),
            "peak_score": int(peak_score),
        })

        print(f"[SWEEP] focus={value}, median_score={median_score}, peak_score={peak_score}")

        # Usamos mediana para decidir, porque evita escoger un pico falso por ruido.
        if median_score > best_median_score:
            best_median_score = median_score
            best_peak_score = peak_score
            best_value = value

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("[SWEEP] Cancelado por usuario.")
            break

    print(f"[SWEEP] Mejor {label}: focus={best_value}, median_score={best_median_score}, peak_score={best_peak_score}")

    return best_value, best_median_score, best_peak_score, results


def make_range(start, stop, step):
    if step <= 0:
        step = 1

    values = []
    v = start

    while v <= stop:
        values.append(v)
        v += step

    if stop not in values:
        values.append(stop)

    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--roi", default="select", help='select, full, o "x1,y1,x2,y2"')
    parser.add_argument("--coarse-step", type=int, default=50)
    parser.add_argument("--fine-span", type=int, default=80)
    parser.add_argument("--fine-step", type=int, default=10)
    parser.add_argument("--micro-span", type=int, default=20)
    parser.add_argument("--micro-step", type=int, default=2)
    parser.add_argument("--output", default="manual_focus_result.json")
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args()

    device = args.device

    controls, list_text = list_controls(device)

    if "focus_absolute" not in controls:
        raise RuntimeError("La cámara no expone focus_absolute")

    if "focus_automatic_continuous" not in controls:
        raise RuntimeError("La cámara no expone focus_automatic_continuous")

    focus_min, focus_max, focus_step = parse_focus_range(list_text)
    print(f"[FOCUS] Rango detectado: min={focus_min}, max={focus_max}, step={focus_step}")

    print("[CAMERA] Aplicando controles base...")
    apply_base_controls(device, controls)

    print("[FOCUS] Apagando autofocus nativo...")
    set_ctrl(device, "focus_automatic_continuous", 0, verify=True)
    time.sleep(0.5)

    cap = open_camera(device, args.width, args.height, args.fps)

    try:
        if args.roi == "select":
            roi = select_focus_roi(cap)
        elif args.roi == "full":
            roi = None
            print("[ROI] Usando frame completo.")
        else:
            values = [int(v.strip()) for v in args.roi.split(",")]
            if len(values) != 4:
                raise ValueError("--roi debe ser select, full, o x1,y1,x2,y2")
            roi = tuple(values)
            print(f"[ROI] Usando ROI manual: {roi}")

        preview = not args.no_preview

        coarse_values = make_range(focus_min, focus_max, args.coarse_step)

        coarse_best, coarse_median, coarse_peak, coarse_results = sweep_focus(
            device,
            cap,
            roi,
            coarse_values,
            label="grueso",
            settle=0.16,
            preview=preview
        )

        if coarse_best is None:
            raise RuntimeError("No se encontró foco en barrido grueso")

        fine_start = max(focus_min, coarse_best - args.fine_span)
        fine_stop = min(focus_max, coarse_best + args.fine_span)
        fine_values = make_range(fine_start, fine_stop, args.fine_step)

        fine_best, fine_median, fine_peak, fine_results = sweep_focus(
            device,
            cap,
            roi,
            fine_values,
            label="fino",
            settle=0.12,
            preview=preview
        )

        micro_start = max(focus_min, fine_best - args.micro_span)
        micro_stop = min(focus_max, fine_best + args.micro_span)
        micro_values = make_range(micro_start, micro_stop, args.micro_step)

        micro_best, micro_median, micro_peak, micro_results = sweep_focus(
            device,
            cap,
            roi,
            micro_values,
            label="micro",
            settle=0.10,
            preview=preview
        )

        print("\n[FOCUS] Aplicando mejor foco final...")
        set_ctrl(device, "focus_absolute", micro_best, verify=True)
        time.sleep(0.4)

        final_median, final_peak, final_frame = capture_focus_score(
            cap,
            roi=roi,
            discard=8,
            samples=12,
            delay=0.04,
            preview=preview,
            focus_value=micro_best
        )

        recommended_min_score = int(final_median * 0.65)

        result = {
            "device": device,
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "focus_roi": roi,
            "focus_value": int(micro_best),
            "final_median_score": int(final_median),
            "final_peak_score": int(final_peak),
            "recommended_min_focus_score": recommended_min_score,
            "coarse_best": int(coarse_best),
            "coarse_median_score": int(coarse_median),
            "fine_best": int(fine_best),
            "fine_median_score": int(fine_median),
            "micro_best": int(micro_best),
            "micro_median_score": int(micro_median),
            "coarse_results": coarse_results,
            "fine_results": fine_results,
            "micro_results": micro_results,
        }

        output_path = Path(args.output)
        output_path.write_text(json.dumps(result, indent=4), encoding="utf-8")

        print("\n[RESULTADO]")
        print(f"Mejor focus_absolute: {micro_best}")
        print(f"Score final mediana: {final_median}")
        print(f"Score final pico: {final_peak}")
        print(f"Score mínimo recomendado: {recommended_min_score}")
        print(f"Resultado guardado en: {output_path.resolve()}")

        print("\nPresiona cualquier tecla en la ventana de video para salir.")
        cv2.waitKey(0)

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()