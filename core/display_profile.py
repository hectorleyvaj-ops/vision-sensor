from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayProfile:
    """Resolution-derived UI policy independent from camera configuration."""

    width: int
    height: int
    mode: str
    scale: float
    margin: int
    spacing: int
    touch_target: int
    title_points: int
    body_points: int
    top_bar_height: int
    log_height: int
    indicator_size: int
    dialog_video_height: int

    @property
    def compact(self):
        return self.mode == "compact"

    @property
    def wide(self):
        return self.mode == "wide"


def build_display_profile(width, height):
    """Return deterministic layout values for the available screen geometry."""
    width = max(320, int(width or 0))
    height = max(240, int(height or 0))

    if width <= 600 or height <= 360:
        mode = "compact"
    elif width >= 1200 and height >= 700:
        mode = "wide"
    else:
        mode = "standard"

    raw_scale = min(width / 800.0, height / 480.0)
    scale = max(0.70, min(1.50, raw_scale))

    if mode == "compact":
        return DisplayProfile(
            width=width,
            height=height,
            mode=mode,
            scale=scale,
            margin=4,
            spacing=4,
            touch_target=34,
            title_points=11,
            body_points=9,
            top_bar_height=38,
            log_height=44,
            indicator_size=48,
            dialog_video_height=max(112, min(140, int(height * 0.40))),
        )

    if mode == "wide":
        return DisplayProfile(
            width=width,
            height=height,
            mode=mode,
            scale=scale,
            margin=14,
            spacing=12,
            touch_target=44,
            title_points=16,
            body_points=12,
            top_bar_height=54,
            log_height=110,
            indicator_size=72,
            dialog_video_height=min(420, int(height * 0.48)),
        )

    return DisplayProfile(
        width=width,
        height=height,
        mode=mode,
        scale=scale,
        margin=9,
        spacing=8,
        touch_target=38,
        title_points=14,
        body_points=10,
        top_bar_height=45,
        log_height=80,
        indicator_size=60,
        dialog_video_height=min(300, int(height * 0.45)),
    )


def preferred_window_size(profile):
    """Choose a useful non-kiosk size without exceeding the active screen."""
    if profile.compact:
        return profile.width, profile.height
    if profile.wide:
        return min(1200, profile.width), min(760, profile.height)
    return min(800, profile.width), min(480, profile.height)


def preferred_dialog_size(profile, requested_width=800, requested_height=600):
    """Fit a dialog within the available desktop while keeping small margins."""
    if profile.compact:
        return profile.width, profile.height
    max_width = max(320, profile.width - 48)
    max_height = max(240, profile.height - 48)
    return min(requested_width, max_width), min(requested_height, max_height)
