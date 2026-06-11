import cv2
import time
from pylibdmtx.pylibdmtx import decode
from tools.tool_base import ToolBase

class DataMatrixTool(ToolBase):
    def __init__(self, config=None, name="dmtx"):
        """
        config esperado:
        {
            "roi": [x,y,w,h],
            "expected_code": "0402010XB",
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
        retries = int(kwargs.get("retries", 5))
        delay = kwargs.get("delay", 0.05)

        expected_code = kwargs.get("expected_code", self.config.get("expected_code"))
        show_roi = kwargs.get("show_roi", self.config.get("show_roi", False))
        debug_images = kwargs.get("debug_images", None)
        roi_cfg = kwargs.get("roi", self.config.get("roi"))

        if not frame_provider:
            raise ValueError("No se recibio frame_provider")
        
        for i in range(retries):
            frame = frame_provider()
            if frame is None:
                continue
            
            
            roi = self._get_roi(frame, roi_cfg)
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            decoded = decode(gray)

            if not decoded:
                print(f"[DMTX] Frame invalido en intento {i+1}")
                time.sleep(delay)
                continue
            
            codes = []
            bones = []
            for item in decoded:
                code = item.data.decode("utf-8")
                codes.append(code)

                x1, y1, x2, y2 = self._rect_to_tuple(item.rect)
                bones.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})      #MEJORA: REDIMENCIONAR LOS RECTANGULOS DE DETECCION DEL CODIGO Y ESCALARLOS AL FRAME REAL
                cv2.rectangle(roi, (x1, y1), (x2, y2), (0, 255, 0), 2)

            code = codes[0]

            if show_roi and debug_images is not None and len(debug_images) < 10:
                debug_images.append(("ROI_DMTX", roi.copy()))

            if expected_code and code != expected_code:
                print(f"[DMTX] Codigo incorrecto en intento {i+1} : '{code}' ")
                if i == retries - 1:
                    raise ValueError(f"Datamatrix invalido: esperado '{expected_code}', leido '{code}'")
            
            else:
                return {
                    "result": "PASS",
                    "code": code,
                    "boxes": bones
                }

        raise ValueError("No se detecto Datamatrix")

    # HELPERS 

    def _get_roi(self, frame, roi_cfg=None):
        if not roi_cfg:
            return frame

        x1, y1, x2, y2 = roi_cfg
        return frame[y1:y2, x1:x2]

    def _rect_to_tuple(self, rect):
        if hasattr(rect, "left"):
            x1 = rect.left
            y1 = rect.top
            x2 = x1 + rect.width
            y2 = y1 + rect.height

            return x1, y1, x2, y2

        return rect
