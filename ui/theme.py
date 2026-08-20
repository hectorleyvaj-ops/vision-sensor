"""Shared industrial Qt theme derived from the active display."""


def interface_stylesheet(profile):
    scale = max(0.70, min(1.50, float(getattr(profile, "scale", 1.0))))
    button_radius = max(6, round(10 * scale))
    field_radius = max(3, round(5 * scale))
    scroll_radius = max(5, round(8 * scale))
    scroll_width = max(16, round(20 * scale))
    field_height = max(28, int(getattr(profile, "touch_target", 38)))
    padding = max(4, round(6 * scale))

    return f"""
        QWidget {{
            background-color: rgb(7, 17, 31);
            color: rgb(235, 241, 248);
            font-family: "DejaVu Sans";
            font-size: {getattr(profile, "body_points", 10)}pt;
        }}

        QLabel {{
            color: rgb(235, 241, 248);
            background-color: transparent;
        }}
        QLabel[uiRole="summary"] {{
            color: rgb(174, 205, 224);
            background-color: rgb(13, 27, 44);
            border: 1px solid rgb(35, 57, 78);
            border-radius: {field_radius + 3}px;
            padding: {padding}px;
            font-weight: 700;
        }}
        QFrame#top_bar, QFrame#frame {{
            background-color: rgb(9, 23, 39);
            border: 1px solid rgb(35, 57, 78);
            border-radius: {field_radius + 4}px;
        }}
        QFrame#frame QLabel, QFrame#frame QListWidget {{
            background-color: transparent;
        }}
        QFrame#frame QListWidget {{
            border: none;
        }}
        QFrame#line, QFrame#line_2 {{
            color: rgb(35, 57, 78);
            background-color: rgb(35, 57, 78);
            border: none;
        }}

        QPushButton {{
            color: rgb(235, 241, 248);
            border-radius: {button_radius}px;
            border: 1px solid rgb(58, 82, 108);
            background-color: rgb(17, 32, 51);
            min-height: {field_height}px;
            padding: 2px {padding * 2}px;
        }}
        QPushButton:hover {{
            background-color: rgb(24, 48, 72);
            border-color: rgb(57, 198, 200);
        }}
        QPushButton:pressed {{
            background-color: rgb(57, 198, 200);
            color: rgb(5, 19, 28);
        }}
        QPushButton:disabled {{
            color: rgb(130, 142, 162);
            border-color: rgb(40, 56, 74);
            background-color: rgb(14, 26, 41);
        }}
        QPushButton[buttonRole="primary"] {{
            color: rgb(4, 24, 31);
            border-color: rgb(57, 198, 200);
            background-color: rgb(57, 198, 200);
            font-weight: 700;
        }}
        QPushButton[buttonRole="danger"] {{
            color: rgb(255, 226, 229);
            border-color: rgb(159, 60, 72);
            background-color: rgb(92, 32, 43);
        }}

        QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QPlainTextEdit,
        QTextEdit, QTableWidget, QListWidget {{
            color: rgb(245, 247, 250);
            border-radius: {field_radius}px;
            border: 1px solid rgb(58, 82, 108);
            background-color: rgb(13, 27, 44);
            selection-background-color: rgb(57, 198, 200);
            selection-color: rgb(5, 19, 28);
        }}
        QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {{
            min-height: {field_height}px;
            padding-left: {padding}px;
            padding-right: {padding * 4}px;
        }}
        QPlainTextEdit, QTextEdit {{
            padding: {padding}px;
        }}
        QComboBox:hover, QLineEdit:hover, QDoubleSpinBox:hover,
        QSpinBox:hover, QPlainTextEdit:hover, QTextEdit:hover {{
            border-color: rgb(46, 196, 182);
        }}
        QComboBox QAbstractItemView {{
            color: rgb(245, 247, 250);
            background-color: rgb(13, 27, 44);
            border: 1px solid rgb(58, 82, 108);
            selection-background-color: rgb(57, 198, 200);
            selection-color: rgb(5, 19, 28);
            outline: 0;
        }}

        QDoubleSpinBox::up-button, QSpinBox::up-button,
        QDoubleSpinBox::down-button, QSpinBox::down-button {{
            subcontrol-origin: border;
            width: {field_height - 8}px;
            border-left: 1px solid rgb(58, 82, 108);
            background-color: rgb(24, 48, 72);
        }}
        QDoubleSpinBox::up-button, QSpinBox::up-button {{
            subcontrol-position: top right;
            border-bottom: 1px solid rgb(58, 82, 108);
        }}
        QDoubleSpinBox::down-button, QSpinBox::down-button {{
            subcontrol-position: bottom right;
        }}

        QCheckBox {{
            color: rgb(234, 234, 234);
            background-color: transparent;
            min-height: {field_height}px;
            spacing: {padding}px;
        }}
        QCheckBox::indicator {{
            width: {max(15, round(17 * scale))}px;
            height: {max(15, round(17 * scale))}px;
            border-radius: {field_radius}px;
            border: 2px solid rgb(57, 198, 200);
            background-color: rgb(13, 27, 44);
        }}
        QCheckBox::indicator:checked {{
            background-color: rgb(57, 198, 200);
            border-color: rgb(57, 198, 200);
        }}

        QTabWidget::pane {{
            border: 1px solid rgb(65, 83, 112);
            border-radius: {field_radius}px;
        }}
        QTabBar::tab {{
            color: rgb(234, 234, 234);
            background-color: rgb(24, 48, 72);
            min-height: {max(28, field_height - 4)}px;
            padding: 2px {padding * 2}px;
            border: 1px solid rgb(65, 83, 112);
        }}
        QTabBar::tab:selected {{
            color: rgb(5, 19, 28);
            background-color: rgb(57, 198, 200);
        }}

        QHeaderView::section {{
            color: rgb(234, 234, 234);
            background-color: rgb(24, 48, 72);
            border: 1px solid rgb(65, 83, 112);
            padding: {padding}px;
        }}
        QTableWidget::item, QListWidget::item {{
            color: rgb(245, 247, 250);
            background-color: rgb(13, 27, 44);
            padding: {max(2, padding // 2)}px;
        }}
        QTableWidget::item:selected, QListWidget::item:selected {{
            color: rgb(5, 19, 28);
            background-color: rgb(57, 198, 200);
        }}

        QScrollArea, QScrollArea > QWidget > QWidget {{
            border: none;
            background-color: rgb(7, 17, 31);
        }}
        QScrollBar:vertical {{
            background-color: rgb(13, 27, 44);
            width: {scroll_width}px;
            margin: 0;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar::handle:vertical {{
            background-color: rgb(57, 198, 200);
            min-height: {max(32, field_height)}px;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar:horizontal {{
            background-color: rgb(13, 27, 44);
            height: {scroll_width}px;
            margin: 0;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: rgb(57, 198, 200);
            min-width: {max(32, field_height)}px;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0;
            height: 0;
            border: none;
            background: transparent;
        }}
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: transparent;
        }}

        QMessageBox, QInputDialog, QToolTip {{
            color: rgb(245, 247, 250);
            background-color: rgb(7, 17, 31);
        }}
        QMessageBox QLabel, QInputDialog QLabel {{
            color: rgb(245, 247, 250);
            background-color: transparent;
            min-width: {max(220, round(280 * scale))}px;
        }}
        QMessageBox QPushButton, QInputDialog QPushButton {{
            color: rgb(235, 241, 248);
            background-color: rgb(17, 32, 51);
            border: 1px solid rgb(58, 82, 108);
            min-width: {max(76, round(92 * scale))}px;
            min-height: {field_height}px;
        }}
    """


def operator_stylesheet(profile):
    """Semantic styling for the production dashboard."""
    indicator_size = int(getattr(profile, "indicator_size", 60))
    indicator_radius = max(20, indicator_size // 2)
    detail_points = max(8, int(getattr(profile, "body_points", 10)) - 1)
    return f"""
        QFrame#top_bar {{
            background-color: rgb(9, 23, 39);
            border: 1px solid rgb(35, 57, 78);
            border-radius: 10px;
        }}
        QLabel#lbl_tittle {{
            color: rgb(242, 247, 251);
            font-weight: 700;
            letter-spacing: 1px;
        }}
        QLabel#lbl_cam {{
            color: rgb(143, 165, 187);
            font-weight: 700;
        }}
        QLabel#lbl_video {{
            color: rgb(143, 165, 187);
            background-color: black;
            border: 1px solid rgb(35, 57, 78);
            border-radius: 10px;
        }}
        QLabel#lbl_model {{
            color: rgb(143, 165, 187);
            background-color: rgb(13, 27, 44);
            border: 1px solid rgb(35, 57, 78);
            border-radius: 10px;
            padding: 8px;
            font-weight: 700;
        }}
        QLabel#lbl_indicator_1 {{
            color: rgb(235, 241, 248);
            background-color: transparent;
            font-size: {detail_points}pt;
            font-weight: 600;
        }}
        QLabel[uiRole="logCaption"] {{
            color: rgb(143, 165, 187);
            font-size: {detail_points}pt;
            font-weight: 700;
            padding: 2px 8px;
        }}
        QFrame#bttm_bar {{
            background-color: rgb(9, 23, 39);
            border: 1px solid rgb(35, 57, 78);
            border-radius: 10px;
        }}
        QListWidget#list_log {{
            color: rgb(177, 194, 211);
            background-color: transparent;
            border: none;
            padding: 2px;
        }}
        QPushButton#btn_config {{
            color: rgb(4, 24, 31);
            background-color: rgb(57, 198, 200);
            border: 1px solid rgb(57, 198, 200);
            font-weight: 700;
        }}
        QPushButton#btn_minimizar {{
            background-color: rgb(17, 32, 51);
            border: 1px solid rgb(58, 82, 108);
        }}
        QPushButton#btn_cerrar {{
            background-color: rgb(92, 32, 43);
            border: 1px solid rgb(159, 60, 72);
        }}
        QPushButton#indicator_1 {{
            min-width: {indicator_size}px;
            max-width: {indicator_size}px;
            min-height: {indicator_size}px;
            max-height: {indicator_size}px;
            border-radius: {indicator_radius}px;
            font-weight: 800;
            padding: 0;
        }}
        QPushButton#indicator_1[statusLevel="ready"] {{
            color: rgb(57, 198, 200);
            background-color: rgb(12, 43, 55);
            border: 2px solid rgb(57, 198, 200);
        }}
        QPushButton#indicator_1[statusLevel="working"] {{
            color: rgb(207, 231, 255);
            background-color: rgb(25, 67, 108);
            border: 2px solid rgb(77, 157, 226);
        }}
        QPushButton#indicator_1[statusLevel="ok"] {{
            color: white;
            background-color: rgb(31, 111, 77);
            border: 2px solid rgb(77, 201, 139);
        }}
        QPushButton#indicator_1[statusLevel="ng"] {{
            color: white;
            background-color: rgb(151, 42, 54);
            border: 2px solid rgb(244, 100, 112);
        }}
        QPushButton#indicator_1[statusLevel="warning"] {{
            color: rgb(255, 243, 204);
            background-color: rgb(111, 76, 17);
            border: 2px solid rgb(238, 180, 62);
        }}
        QPushButton#indicator_1[statusLevel="critical"] {{
            color: white;
            background-color: rgb(116, 30, 40);
            border: 2px solid rgb(244, 100, 112);
        }}
    """
