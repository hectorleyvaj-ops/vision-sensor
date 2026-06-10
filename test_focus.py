import cv2
import time
import subprocess

DEVICE = "/dev/video0"

def get_focus():
    try:
        r = subprocess.run(
            ["v4l2-ctl", "-d", DEVICE, "--get-ctrl=focus_absolute"],
            capture_output=True,
            text=True
        )
        return r.stdout.strip()
    except Exception as e:
        return f"error: {e}"

def score_focus(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

cap = cv2.VideoCapture(DEVICE, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("No se pudo abrir la cámara")
    raise SystemExit

print("Midiendo enfoque. Presiona Ctrl+C para salir.")

try:
    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("Frame inválido")
            time.sleep(0.2)
            continue

        score = score_focus(frame)
        focus = get_focus()

        print(f"score={score:.2f} | {focus}")

        time.sleep(0.3)

except KeyboardInterrupt:
    print("\nPrueba terminada.")

finally:
    cap.release()