"""Canonical region-of-interest helpers for the universal vision engine.

Every persisted ROI uses pixel coordinates ``[x1, y1, x2, y2]``.  ``x1`` and
``y1`` are inclusive while ``x2`` and ``y2`` are exclusive, matching NumPy
slicing.  The module deliberately has no OpenCV or Qt dependency.
"""


class ROIError(ValueError):
    """Raised when an ROI cannot describe a non-empty rectangle."""


CANONICAL_FORMAT = "xyxy"
LEGACY_XYWH_FORMAT = "xywh"


def normalize_roi(roi, source_format=CANONICAL_FORMAT, allow_none=True):
    """Return a canonical ROI list without clipping it to a frame.

    ``source_format`` is only used while migrating known legacy data.  Runtime
    and editor code must use the canonical ``xyxy`` format.
    """
    if roi is None:
        if allow_none:
            return None
        raise ROIError("ROI obligatoria")

    if not isinstance(roi, (list, tuple)) or len(roi) != 4:
        raise ROIError(f"ROI debe contener cuatro coordenadas: {roi}")

    try:
        values = [int(float(value)) for value in roi]
    except (TypeError, ValueError) as exc:
        raise ROIError(f"ROI contiene coordenadas no numericas: {roi}") from exc

    fmt = str(source_format or CANONICAL_FORMAT).strip().lower()
    if fmt == CANONICAL_FORMAT:
        x1, y1, x2, y2 = values
    elif fmt == LEGACY_XYWH_FORMAT:
        x1, y1, width, height = values
        x2 = x1 + width
        y2 = y1 + height
    else:
        raise ROIError(f"Formato ROI no soportado: {source_format}")

    if x1 < 0 or y1 < 0:
        raise ROIError(f"ROI no admite coordenadas negativas: {roi}")
    if x2 <= x1 or y2 <= y1:
        raise ROIError(f"ROI no tiene area valida: {roi}")

    return [x1, y1, x2, y2]


def pad_and_clip_roi(roi, frame_width, frame_height, padding=0):
    """Normalize, pad and clip an ROI to a frame, preserving non-zero area."""
    canonical = normalize_roi(roi, allow_none=False)
    try:
        width = int(frame_width)
        height = int(frame_height)
        extra = max(0, int(float(padding)))
    except (TypeError, ValueError) as exc:
        raise ROIError("Dimensiones de frame o padding invalidos") from exc

    if width <= 0 or height <= 0:
        raise ROIError(f"Frame sin dimensiones validas: {width}x{height}")

    x1, y1, x2, y2 = canonical
    clipped = [
        max(0, min(width, x1 - extra)),
        max(0, min(height, y1 - extra)),
        max(0, min(width, x2 + extra)),
        max(0, min(height, y2 + extra)),
    ]
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        raise ROIError(
            f"ROI fuera de rango o sin area: {canonical}, frame={width}x{height}"
        )
    return clipped


def crop_image(image, roi=None, padding=0):
    """Crop an ndarray-like image using the canonical ROI representation."""
    if image is None or not hasattr(image, "shape"):
        raise ROIError("Frame invalido")
    if getattr(image, "size", 0) == 0:
        raise ROIError("Frame vacio")
    if roi is None:
        return image

    frame_height, frame_width = image.shape[:2]
    x1, y1, x2, y2 = pad_and_clip_roi(
        roi,
        frame_width=frame_width,
        frame_height=frame_height,
        padding=padding,
    )
    return image[y1:y2, x1:x2]
