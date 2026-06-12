# LOGICA DE FOCO MANUAL
# BARRIDO DE FRAMES: GRUESO -> FINO -> MICRO. CALCULO DE SCORE POR ROI, VERIFICACION FINAL Y RETORNO DEL MEJOR FOCUS ABOSOLUTE

import cv2
import time
from dataclasses import dataclass, field

@dataclass
class ManualFocusResult:
    ok: bool
    focus_value: int | None
    median_score: int
    peak_score: int
    min_score: int
    roi: tuple | None
    coarse_best: int | None = None
    fine_best: int | None = None
    micro_best: int | None = None
    coarse_results: list = field(default_factory=list)
    fine_results: list = field(default_factory=list)
    micro_results: list = field(default_factory=list)

class ManualFocusController:
    def __init__(
            self,
            cap,
            set_focus_absolute,
            get_focus_absolute,
            set_autofocus,
            emit_frame=None,
            is_running=None,
            focus_min=1,
            focus_max=1023,
            focus_step=1,
        ):
        self.cap = cap
        self.set_focus_absolute = set_focus_absolute
        self.get_focus_absolute = get_focus_absolute
        self.set_autofocus = set_autofocus
        self.emit_frame = emit_frame
        self.is_running = is_running or (lambda: True)
        
        self.focus_min = int(focus_min)
        self.focus_max = int(focus_max)
        self.focus_step = max(1, int(focus_step))

    @staticmethod
    def clamp_roi(roi, frame):
        if roi is None:
            return None
        
        h, w = frame.shape[:2]

        x1, y1, x2, y2 = roi

        # LIMITA LOS VALORES DEL ROI PARA QUE NO SALGAN DEL FRAME
        x1 = max(0, min(w - 1, int(x1)))
        y1 = max(0, min(h - 1, int(y1)))
        x2 = max(0, min(w, int(x2)))
        y2 = max(0, min(h, int(y2)))

        # VERIFICA QUE EL ROI TENGA SENTIDO
        if x2 <= x1 or y2 <= y1:
            return None
        
        return x1, y1, x2, y2
    
    @classmethod
    def focus_score(cls, frame, roi=None):
        try:
            if roi is not None:
                clean_roi = cls.clamp_roi(roi, frame)
                if clean_roi is not None:
                    x1, y1, x2, y2 = clean_roi
                    frame = frame [y1:y2, x1:x2]    # RECORTAMOS EL FRAME AL ROI - COLUMNAS * FILAS

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return int(cv2.Laplacian(gray, cv2.CV_64F).var())
        
        except Exception:
            return -1
        
    # RETORNA UNA LISTA DE VALORES DESDE INICIO A FIN AVANZANDO SEGUN STEP PARA EL FOCO
    @staticmethod
    def make_range(start, stop, step):
        step = max(1, step)
        values = []
        value = int(start)

        # RECORREMOS LOS VALORES DEL FOCO DESDE EL INICIO HASTA EL LIMITE SUMANDO STEP Y GUARDAMOS EN UNA LISTA
        while value <= int(stop):
            values.append(value)
            value += step

        if int(stop) not in values:
            values.append(int(stop))

        return values
    
    def read_good_frame(self, retries=10, delay=0.03):
        for _ in range(retries):
            if not self.is_running():
                return None
            
            ret, frame = self.cap.read()

            if ret and frame is not None and hasattr(frame, "shape") and frame.size > 0:
                return frame
            
            time.sleep(delay)

        return None
    
    def _emit_preview(self, frame):
        if self.emit_frame is not None and frame is not None:
            self.emit_frame(frame)

    def capture_focus_score(
        self,
        roi=None,
        discard=5,
        samples=7,
        delay=0.04,
        focus_value=None,
    ):
        # DESCARTA LOS PRIMEROS FRAMES PARA ESTABILIZAR
        for _ in range(discard):
            if not self.is_running():
                break

            self.cap.read()
            time.sleep(delay)


        scores = []
        best_frame = None
        best_score = None

        # OBTIENE LOS VALORES DE SCORE
        for _ in range(samples):
            if not self.is_running():
                break

            frame = self.read_good_frame()

            if frame is None:
                time.sleep(delay)
                continue
            
            # CALCULA EL SCORE DEL ROI O FRAME USADNDO LAPLACIANO
            score = self.focus_score(frame, roi)
            scores.append(score)

            if score > best_score:
                best_score = score
                best_frame = frame.copy()

            self._emit_preview(frame)
            time.sleep(delay)

        if not scores:
            return -1, -1, best_frame
        
        scores_sorted = sorted(scores)
        median_score = scores_sorted[len(scores_sorted) // 2]

        return int(median_score), int(best_score), best_frame
    

    # FUNCION DE BARRIDO
    def sweep_focus(
        self,
        roi,
        values,
        label="sweep",
        settle=0.12,
        discard=4,
        samples=7,
        delay=0.035,
    ):
        best_value = None
        best_median_score = -1
        best_peak_score = -1
        results = []

        print(f"[FOCUS][SWEEP] Iniciando barrido {label}. Valores: {len(values)}")

        for value in values:
            if not self.is_running():
                break

            value = int(value)
            print(f"[FOCUS][SWEEP] {label} focus_absolute={value}")
            
            if not self.set_focus_absolute(value):
                print(f"[FOCUS][WARNING] No se pudo aplicar focus_absolute={value}")
                continue

            time.sleep(delay)

            median_score, peak_score, _ = self.capture_focus_score(
                roi=roi,
                discard=discard,
                samples=samples,
                delay=delay,
                focus_value=value
            )

            results.append({
                "focus": value,
                "median_score": median_score,
                "peak_score": peak_score,
            })

            print(
                f"[FOCUS][SWEEP] focus={value}, "
                f"median_score={median_score}, peak_score={peak_score}"
            )

            if median_score > best_median_score:
                best_median_score = median_score,
                best_peak_score = peak_score,
                best_value = value

        print(
            f"[FOCUS][SWEEP] Mejor {label}: "
            f"focus={best_value}, median_score={best_median_score}, peak_score={best_peak_score}"
        )

        return best_value, best_median_score, best_peak_score, results
    
    def apply_focus(self, focus_value, settle=0.35):
        if focus_value is None:
            return False
        
        self.set_autofocus(False)
        time.sleep(0.15)

        if not self.set_focus_absolute(int(focus_value)):
            return False
        
        time.sleep(settle)
        return True
    
    def verify_focus(
        self,
        focus_value=None,
        roi=None,
        min_score=350,
        samples=12,
        delay=0.04,
        apply_value=False,
    ):
        if apply_value and focus_value is not None:
            if not self.apply_focus(focus_value):
                return False, -1, -1

        median_score, peak_score, _ = self.capture_focus_score(
            roi=roi,
            discard=8,
            samples=samples,
            delay=delay,
            focus_value=focus_value,
        )


        ok = median_score > min_score

        print(
            f"[FOCUS][VERIFY] focus={focus_value}, "
            f"median_score={median_score}, peak_score={peak_score}, "
            f"min_score={min_score}, ok={ok}"
        )

        return ok, int(median_score), int(peak_score)
    
    def calibrate(
        self,
        roi=None,
        coarse_step=50,
        fine_span=80,
        fine_step=10,
        micro_span=20,
        micro_step=2,
        min_score_ratio=0.65,
    ):
        print("[FOCUS] Iniciando autofocus manual")

        self.set_autofocus(False)
        time.sleep(0.5)

        course_values = self.make_range(
            self.focus_min,
            self.focus_max,
            max(coarse_step, self.focus_step)
        )

        coarse_best, coarse_median, coarse_peak, coarse_results = self.sweep_focus(
            roi=roi,
            values=course_values,
            label="grueso",
            settle=0.16,
            discard=4,
            samples=7,
            delay=0.035,
        )

        if coarse_best is None:
            print("[FOCUS][ERROR] No se encontró foco en barrido grueso")
            # USA LA CLASE MODULAR DE RESULTADOS
            return ManualFocusResult(
                ok=False,
                focus_value=None,
                median_score=-1,
                peak_score=-1,
                min_score=-1,
                roi=roi,
                coarse_results=coarse_results,
            )
        
        # DEFINE EL RANGO Y VALORES PARA EL BARRINO FINO
        fine_start = max(self.focus_min, coarse_best - fine_span)
        fine_stop = max(self.focus_max, coarse_best + fine_span)
        fine_values = self.make_range(
            fine_start,
            fine_stop,
            max(fine_step, self.focus_step)
        )

        fine_best, fine_median, fine_peak, fine_results = self.sweep_focus(
            roi=roi,
            values=fine_values,
            label="fino",
            settle=0.12,
            discard=4,
            samples=7,
            delay=0.05,
        )

        if fine_best is None:
            print("[FOCUS][ERROR] No se encontró foco en barrido fino")
            # USA LA CLASE MODULAR DE RESULTADOS
            return ManualFocusResult(
                ok=False,
                focus_value=None,
                median_score=-1,
                peak_score=-1,
                min_score=-1,
                roi=roi,
                coarse_best=coarse_best,
                coarse_results=coarse_results,
                fine_results=fine_results,
            )
        
        # DEFINE EL RANGO Y LOS VALORES PARA EL BARRIDO FINO
        micro_start = max(self.focus_min, fine_best - fine_span)
        micro_stop = max(self.focus_max, fine_best + fine_span)
        micro_values = self.make_range(
            micro_start,
            micro_stop,
            max(micro_step, self.focus_step)
        )

        micro_best, micro_median, micro_peak, micro_results = self.sweep_focus(
            roi=roi,
            values=micro_values,
            label="micro",
            settle=0.10,
            discard=4,
            samples=7,
            delay=0.035,
        )

        if micro_best is None:
            print("[FOCUS][ERROR] No se encontró foco en barrido micro")
            # USA LA CLASE MODULAR DE RESULTADOS
            return ManualFocusResult(
                ok=False,
                focus_value=None,
                median_score=-1,
                peak_score=-1,
                min_score=-1,
                roi=roi,
                coarse_best=coarse_best,
                fine_best=fine_best,
                coarse_results=coarse_results,
                fine_results=fine_results,
                micro_results=micro_results,
            )
        
        print(f"[FOCUS] Aplicando mejor foco final: {micro_best}")

        if not self.apply_focus(micro_best):
             return ManualFocusResult(
                ok=False,
                focus_value=micro_best,
                median_score=-1,
                peak_score=-1,
                min_score=-1,
                roi=roi,
                coarse_best=coarse_best,
                fine_best=fine_best,
                micro_best=micro_best,
                coarse_results=coarse_results,
                fine_results=fine_results,
                micro_results=micro_results,
            )
        
        final_median, final_peak, _ = self.capture_focus_score(
            roi=roi,
            discard=8,
            samples=12,
            delay=0.04,
            focus_value=micro_best
        )

        recommended_min_score = int(final_median * min_score_ratio)
        print(
            f"[FOCUS][OK] focus={micro_best}, "
            f"final_median={final_median}, final_peak={final_peak}, "
            f"recommended_min_score={recommended_min_score}"
        )

        return ManualFocusResult(
            ok=True,
            focus_value=int(micro_best),
            median_score=int(final_median),
            peak_score=int(final_peak),
            min_score=int(recommended_min_score),
            roi=roi,
            coarse_best=int(coarse_best),
            fine_best=int(fine_best),
            micro_best=int(micro_best),
            coarse_results=coarse_results,
            fine_results=fine_results,
            micro_results=micro_results,
        )



