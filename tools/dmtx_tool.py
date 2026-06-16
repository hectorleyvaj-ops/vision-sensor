import cv2
import time
from collections import Counter
from pylibdmtx.pylibdmtx import decode
from tools.tool_base import ToolBase


class DataMatrixTool(ToolBase):
    def __init__(self, config=None, name="dmtx"):
        """
        config esperado:
        {
            "roi": [x1, y1, x2, y2],
            "expected_code": "0402010XB",
            "retries": 5,
            "delay": 0.05,
            "min_expected_reads": 2,
            "max_wrong_reads": 0,
            "show_roi": False
        }
        """
        super().__init__(name)
        self.config = config or {}

    def run(self, frame=None, **kwargs):
        if frame is not None:
            kwargs["frame"] = frame

        return super().run(**kwargs)

    def process(self, **kwargs):
        frame_provider = kwargs.get("frame_provider")
        capture_provider = kwargs.get("capture_provider")
        direct_frame = kwargs.get("frame")

        retries = max(1, int(float(kwargs.get("retries", self.config.get("retries", 5)))))
        delay = float(kwargs.get("delay", self.config.get("delay", 0.05)))

        expected_code = kwargs.get("expected_code", self.config.get("expected_code"))
        expected_code = expected_code.strip() if isinstance(expected_code, str) else expected_code

        min_expected_reads = kwargs.get("min_expected_reads", self.config.get("min_expected_reads"))
        if min_expected_reads is None:
            min_expected_reads = 1 if retries <= 1 else 2
        min_expected_reads = max(1, int(float(min_expected_reads)))

        max_wrong_reads = kwargs.get("max_wrong_reads", self.config.get("max_wrong_reads", 0))
        max_wrong_reads = max(0, int(float(max_wrong_reads)))

        show_roi = kwargs.get("show_roi", self.config.get("show_roi", False))
        debug_images = kwargs.get("debug_images", None)
        roi_cfg = kwargs.get("roi", self.config.get("roi"))

        if direct_frame is None and not frame_provider and not capture_provider:
            raise ValueError("No se recibio frame, frame_provider ni capture_provider")

        all_reads = []
        expected_reads = []
        wrong_reads = []
        no_read_count = 0
        decode_errors = []
        boxes_by_attempt = []
        last_frame_id = None

        for i in range(retries):
            frame, metadata = self._get_frame(
                direct_frame=direct_frame,
                frame_provider=frame_provider,
                capture_provider=capture_provider,
            )

            if frame is None:
                no_read_count += 1
                decode_errors.append(f"Intento {i + 1}: frame no disponible")
                time.sleep(delay)
                continue

            last_frame_id = metadata.get("frame_id", last_frame_id)

            try:
                roi = self._get_roi(frame, roi_cfg)
                gray = self._to_gray(roi)
                decoded = decode(gray)
            except Exception as e:
                no_read_count += 1
                decode_errors.append(f"Intento {i + 1}: error preparando ROI/decode: {e}")
                time.sleep(delay)
                continue

            if show_roi and debug_images is not None and len(debug_images) < 10:
                debug_images.append((f"ROI_DMTX_{i + 1}", roi.copy()))

            if not decoded:
                print(f"[DMTX] Sin lectura en intento {i + 1}/{retries}")
                no_read_count += 1
                time.sleep(delay)
                continue

            attempt_codes = []
            attempt_boxes = []

            for item in decoded:
                code = self._decode_item_data(item)
                if not code:
                    continue

                attempt_codes.append(code)
                all_reads.append(code)

                x1, y1, x2, y2 = self._rect_to_tuple(item.rect)
                attempt_boxes.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            boxes_by_attempt.append(attempt_boxes)

            if not attempt_codes:
                no_read_count += 1
                time.sleep(delay)
                continue

            print(f"[DMTX] Intento {i + 1}/{retries}: {attempt_codes}")

            if expected_code:
                if expected_code in attempt_codes:
                    expected_reads.append(expected_code)

                non_expected = [code for code in attempt_codes if code != expected_code]
                if non_expected:
                    wrong_reads.extend(non_expected)
                    print(
                        f"[DMTX][WARNING] Codigo diferente al esperado en intento {i + 1}: "
                        f"{non_expected}"
                    )

                if len(expected_reads) >= min_expected_reads and len(wrong_reads) <= max_wrong_reads:
                    return self._build_pass(
                        code=expected_code,
                        expected_code=expected_code,
                        reads=all_reads,
                        expected_count=len(expected_reads),
                        wrong_count=len(wrong_reads),
                        no_read_count=no_read_count,
                        boxes=boxes_by_attempt,
                        frame_id=last_frame_id,
                    )

            else:
                counts = Counter(all_reads)
                code, count = counts.most_common(1)[0]

                if count >= min_expected_reads:
                    return self._build_pass(
                        code=code,
                        expected_code=None,
                        reads=all_reads,
                        expected_count=count,
                        wrong_count=0,
                        no_read_count=no_read_count,
                        boxes=boxes_by_attempt,
                        frame_id=last_frame_id,
                    )

            time.sleep(delay)

        summary = {
            "expected_code": expected_code,
            "reads": all_reads,
            "expected_count": len(expected_reads),
            "wrong_reads": wrong_reads,
            "wrong_count": len(wrong_reads),
            "no_read_count": no_read_count,
            "decode_errors": decode_errors,
            "min_expected_reads": min_expected_reads,
            "max_wrong_reads": max_wrong_reads,
            "frame_id": last_frame_id,
        }

        if expected_code and len(wrong_reads) > max_wrong_reads:
            raise ValueError(f"Datamatrix sospechoso: lecturas incorrectas detectadas {summary}")

        if expected_code:
            raise ValueError(f"Datamatrix no confirmado por mayoria: {summary}")

        raise ValueError(f"No se detecto Datamatrix confiable: {summary}")

    # HELPERS

    def _get_frame(self, direct_frame=None, frame_provider=None, capture_provider=None):
        if direct_frame is not None:
            return direct_frame, {}

        if capture_provider is not None:
            result = capture_provider()
            if not result or result.get("status") != "OK":
                error = result.get("error") if isinstance(result, dict) else "captura invalida"
                print(f"[DMTX][WARNING] Captura invalida: {error}")
                return None, result or {}

            return result.get("frame"), result

        if frame_provider is not None:
            return frame_provider(), {}

        return None, {}

    def _get_roi(self, frame, roi_cfg=None):
        if frame is None:
            raise ValueError("Frame vacio")

        if not hasattr(frame, "shape") or frame.size == 0:
            raise ValueError("Frame invalido")

        if not roi_cfg:
            return frame

        if len(roi_cfg) != 4:
            raise ValueError(f"ROI invalida, se esperaban 4 valores: {roi_cfg}")

        height, width = frame.shape[:2]
        x1, y1, x2, y2 = [int(float(v)) for v in roi_cfg]

        x1 = max(0, min(width - 1, x1))
        y1 = max(0, min(height - 1, y1))
        x2 = max(0, min(width, x2))
        y2 = max(0, min(height, y2))

        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"ROI fuera de rango o sin area: {roi_cfg}, frame={width}x{height}")

        return frame[y1:y2, x1:x2]

    def _to_gray(self, image):
        if len(image.shape) == 2:
            return image

        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _decode_item_data(self, item):
        try:
            return item.data.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""

    def _rect_to_tuple(self, rect):
        if hasattr(rect, "left"):
            x1 = rect.left
            y1 = rect.top
            x2 = x1 + rect.width
            y2 = y1 + rect.height

            return x1, y1, x2, y2

        return rect

    def _build_pass(
        self,
        code,
        expected_code,
        reads,
        expected_count,
        wrong_count,
        no_read_count,
        boxes,
        frame_id=None,
    ):
        print(
            f"[DMTX] PASS code='{code}', expected_count={expected_count}, "
            f"wrong_count={wrong_count}, no_read_count={no_read_count}"
        )
        return {
            "result": "PASS",
            "code": code,
            "expected_code": expected_code,
            "reads": list(reads),
            "expected_count": int(expected_count),
            "wrong_count": int(wrong_count),
            "no_read_count": int(no_read_count),
            "boxes": boxes,
            "frame_id": frame_id,
        }
