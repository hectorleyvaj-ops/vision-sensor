from core.display_profile import (
    build_display_profile,
    preferred_dialog_size,
    preferred_window_size,
)
from utils.qt_compat import QSizePolicy


WIDGET_SIZE_MAX = 16777215


def profile_from_screen(screen, fallback=(800, 480)):
    if screen is None:
        return build_display_profile(*fallback)
    geometry = screen.availableGeometry()
    return build_display_profile(geometry.width(), geometry.height())


def profile_from_widget(widget, fallback=(800, 480)):
    screen = widget.screen() if widget is not None else None
    return profile_from_screen(screen, fallback=fallback)


def _unlock(widget, minimum=(0, 0)):
    widget.setMinimumSize(*minimum)
    widget.setMaximumSize(WIDGET_SIZE_MAX, WIDGET_SIZE_MAX)


def _set_font_points(widget, points, bold=None):
    font = widget.font()
    font.setPointSize(points)
    if bold is not None:
        font.setBold(bold)
    widget.setFont(font)


def apply_main_window_layout(window, ui, profile):
    """Remove generated fixed geometry and apply one resolution policy."""
    _unlock(window, (320, 240))
    _unlock(ui.centralwidget, (0, 0))
    ui.centralwidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    width, height = preferred_window_size(profile)
    window.resize(width, height)

    ui.verticalLayout_3.setContentsMargins(
        profile.margin, profile.margin, profile.margin, profile.margin
    )
    ui.verticalLayout_3.setSpacing(profile.spacing)
    ui.top_bar.setMinimumSize(0, profile.top_bar_height)
    ui.top_bar.setMaximumSize(WIDGET_SIZE_MAX, profile.top_bar_height)
    ui.horizontalLayout_5.setContentsMargins(
        profile.margin, 2, profile.margin, 2
    )
    ui.horizontalLayout_5.setSpacing(profile.spacing)

    for widget in (
        ui.lbl_tittle,
        ui.lbl_cam,
        ui.lbl_video,
        ui.lbl_model,
        ui.btn_config,
        ui.lbl_indicator_1,
        ui.bttm_bar,
        ui.list_log,
    ):
        _unlock(widget, (0, 0))

    _set_font_points(ui.lbl_tittle, profile.title_points, bold=True)
    for widget in (ui.lbl_cam, ui.lbl_model, ui.lbl_indicator_1, ui.list_log):
        _set_font_points(widget, profile.body_points)

    ui.btn_minimizar.setFixedSize(profile.touch_target, profile.touch_target)
    ui.btn_cerrar.setFixedSize(profile.touch_target, profile.touch_target)
    ui.btn_config.setMinimumHeight(profile.touch_target)
    ui.btn_config.setMaximumHeight(profile.touch_target + 6)
    ui.indicator_1.setFixedSize(profile.indicator_size, profile.indicator_size)
    ui.lbl_model.setMinimumHeight(profile.touch_target + 10)
    ui.lbl_indicator_1.setMinimumHeight(profile.indicator_size)

    ui.left_panel.setSpacing(profile.spacing)
    ui.left_panel.setContentsMargins(0, 0, 0, 0)
    ui.right_panel.setSpacing(profile.spacing)
    ui.right_panel.setContentsMargins(
        profile.spacing, 0, 0, 0
    )
    ui.status_1.setContentsMargins(0, 0, 0, 0)
    ui.status_1.setSpacing(profile.spacing)
    ui.central_panel.setSpacing(profile.spacing)
    ui.central_panel.setStretch(0, 5)
    ui.central_panel.setStretch(1, 3)

    ui.bttm_bar.setMinimumHeight(profile.log_height)
    ui.bttm_bar.setMaximumHeight(profile.log_height)
    ui.list_log.setMinimumHeight(0)
    ui.list_log.setMaximumHeight(WIDGET_SIZE_MAX)
    ui.lbl_cam.setVisible(not profile.compact)

    ui.verticalSpacer.changeSize(0, 0)
    ui.horizontalSpacer.changeSize(0, 0)
    ui.verticalSpacer_2.changeSize(0, 0)

    window.setProperty("displayMode", profile.mode)
    return profile


def apply_config_window_layout(window, ui, profile):
    _unlock(window, (320, 240))
    window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    width, height = preferred_window_size(profile)
    window.resize(width, height)

    ui.verticalLayout.setContentsMargins(
        profile.margin, profile.margin, profile.margin, profile.margin
    )
    ui.verticalLayout.setSpacing(profile.spacing)
    ui.central_layout.setSpacing(profile.spacing)
    ui.bttm_layout.setSpacing(profile.spacing)
    ui.bttm_layout.setContentsMargins(0, profile.spacing, 0, profile.spacing)

    for widget in (
        ui.top_bar,
        ui.lbl_tittle,
        ui.lbl_recipes,
        ui.cmb_recipes,
        ui.lbl_tools,
        ui.cmb_tools,
        ui.line,
        ui.line_2,
        ui.lbl_focus,
        ui.frame,
        ui.list_log_config,
    ):
        _unlock(widget, (0, 0))

    for button in (
        ui.btn_add_r,
        ui.btn_del_r,
        ui.btn_select_r,
        ui.btn_add_t,
        ui.btn_del_t,
        ui.btn_edit_t,
        ui.btn_focus_config,
        ui.btn_save,
        ui.btn_out,
    ):
        _unlock(button, (0, profile.touch_target))
        button.setMaximumHeight(WIDGET_SIZE_MAX)

    ui.top_bar.setMinimumHeight(profile.top_bar_height)
    ui.top_bar.setMaximumHeight(profile.top_bar_height)
    _set_font_points(ui.lbl_tittle, profile.title_points, bold=True)
    for widget in (ui.lbl_recipes, ui.lbl_tools, ui.lbl_focus):
        _set_font_points(widget, profile.body_points, bold=True)

    ui.horizontalSpacer_3.changeSize(0, 0)
    ui.central_layout.setStretch(0, 1)
    ui.central_layout.setStretch(2, 1)

    ui.frame.setMinimumHeight(0)
    ui.frame.setMaximumHeight(profile.log_height)
    ui.frame.setVisible(not profile.compact)
    window.setProperty("displayMode", profile.mode)
    return profile


def configure_dialog(dialog, profile, requested=(800, 600), fullscreen=False):
    """Fit modal editors to the detected screen; caller chooses exec()."""
    dialog.setMinimumSize(0, 0)
    dialog.setMaximumSize(profile.width, profile.height)
    width, height = preferred_dialog_size(profile, *requested)
    dialog.resize(width, height)
    dialog.setProperty("displayMode", profile.mode)
    if profile.compact or fullscreen:
        dialog.showFullScreen()
    return profile


def compact_stylesheet(profile):
    return f"""
        QWidget[displayMode=\"compact\"] {{
            font-size: {profile.body_points}pt;
        }}
        QWidget[displayMode=\"compact\"] QPushButton {{
            min-height: {profile.touch_target}px;
            padding: 2px 6px;
            border-radius: 7px;
        }}
        QWidget[displayMode=\"compact\"] QLineEdit,
        QWidget[displayMode=\"compact\"] QComboBox,
        QWidget[displayMode=\"compact\"] QSpinBox,
        QWidget[displayMode=\"compact\"] QDoubleSpinBox {{
            min-height: {profile.touch_target}px;
        }}
    """
