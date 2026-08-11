# HERRAMIENTA PARA COMPARAR IMAGENES Y DETECTAR COMPONENTES EN LAS PIEZAS..
# USANDO COMPARE HIST BHATTACHARYYA

import cv2
import numpy
from core.execution_control import check_execution
from core.roi import crop_image
from tools.result import ToolFailure
from tools.tool_base import ToolBase

class CompareImgHistTool(ToolBase):
    def __init__(self, name="compare_img_hist"):
        super().__init__(name)

    # MANDA A LLAMAR A LA FUNCION DE LA CLASE PADRE Y LE DA LA INFORMACION EN KWARGS
    def run(self, **kwargs):
        return super().run(**kwargs)
    
    # FUNCION PRINCIPAL DE LA HERRAMIENTA
    def process(self, **kwargs):
        #BUSCA Y GUARDA LA INFORMACION DE LOS ARGUMENTOS
        frame = kwargs.get("frame")
        template_paths = kwargs.get("template_paths")
        threshold = kwargs.get("threshold", 80.0)
        roi_cfg = kwargs.get("roi")
        show_roi = kwargs.get("show_roi")
        debug_images = kwargs.get("debug_images", None)
        cancel_event = kwargs.get("cancel_event")
        deadline = kwargs.get("deadline")

        check_execution(cancel_event=cancel_event, deadline=deadline)

        if frame is None:
            raise ValueError("No frame recibido")
        
        if not template_paths or len(template_paths) == 0:
            raise ValueError("No template_paths definidos")
        
        # PROCESAR FRAME A EVALUAR
        roi = self._get_roi(frame, roi_cfg)

        if show_roi and debug_images is not None:
            debug_images.append(("ROI_HIST",roi))

            # CONVERSION A ESCALA DE GRISES
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # OBTENER HISTORIGRAMA
        hist_roi = cv2.calcHist([roi_gray], [0], None, [256], [0,256])

            # NORMALIZAR HISTORIGRAMAS
        cv2.normalize(hist_roi, hist_roi)

        best_percent = 0
        best_path = None

        for path in template_paths:
            check_execution(cancel_event=cancel_event, deadline=deadline)
            template = cv2.imread(path)

            if template is None:
                print(f"Warning: no se pudo cargar {path}")
                continue

            template_roi = self._get_roi(template, roi_cfg)
            template_gray = cv2.cvtColor(template_roi, cv2.COLOR_BGR2GRAY)

            hist_template = cv2.calcHist([template_gray], [0], None, [256], [0,256])
            cv2.normalize(hist_template, hist_template)

            # APLICAR COMPARACION
            score = cv2.compareHist(hist_template, hist_roi, cv2.HISTCMP_BHATTACHARYYA)
            percent = (1-score) * 100

            if percent > best_percent:
                best_percent = percent
                best_path = path

        if best_path is None:
            raise ValueError("No se pudo cargar ninguna imagen maestra")

        if best_percent < threshold:
            raise ToolFailure(
                f"Baja similitud: {best_percent:.3f} < {threshold}",
                data={
                    "result": "FAIL",
                    "score": round(best_percent, 3),
                    "threshold": threshold,
                    "best_match": best_path,
                },
                code="HISTOGRAM_BELOW_THRESHOLD",
            )
        
        return {
            "result": "PASS",
            "score": round(best_percent, 3),
            "best_match": best_path
        }


    def _get_roi(self, frame, roi_cfg=None):
        return crop_image(frame, roi=roi_cfg)
    

