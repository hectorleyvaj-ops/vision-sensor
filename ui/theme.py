"""Shared high-contrast Qt stylesheet derived from the active display."""


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
            background-color: rgb(11, 19, 43);
            color: rgb(234, 234, 234);
            font-size: {getattr(profile, "body_points", 10)}pt;
        }}

        QLabel {{
            color: rgb(234, 234, 234);
            background-color: transparent;
        }}

        QPushButton {{
            color: rgb(234, 234, 234);
            border-radius: {button_radius}px;
            border: 2px solid rgb(91, 192, 190);
            background-color: rgb(15, 27, 61);
            min-height: {field_height}px;
            padding: 2px {padding * 2}px;
        }}
        QPushButton:hover {{
            background-color: rgb(20, 38, 82);
            border-color: rgb(46, 196, 182);
        }}
        QPushButton:pressed {{
            background-color: rgb(46, 196, 182);
            color: rgb(11, 19, 43);
        }}
        QPushButton:disabled {{
            color: rgb(130, 142, 162);
            border-color: rgb(65, 83, 112);
            background-color: rgb(20, 29, 53);
        }}

        QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QPlainTextEdit,
        QTextEdit, QTableWidget, QListWidget {{
            color: rgb(245, 247, 250);
            border-radius: {field_radius}px;
            border: 2px solid rgb(91, 192, 190);
            background-color: rgb(15, 27, 61);
            selection-background-color: rgb(46, 196, 182);
            selection-color: rgb(11, 19, 43);
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
            background-color: rgb(15, 27, 61);
            border: 2px solid rgb(91, 192, 190);
            selection-background-color: rgb(46, 196, 182);
            selection-color: rgb(11, 19, 43);
            outline: 0;
        }}

        QDoubleSpinBox::up-button, QSpinBox::up-button,
        QDoubleSpinBox::down-button, QSpinBox::down-button {{
            subcontrol-origin: border;
            width: {field_height - 8}px;
            border-left: 1px solid rgb(91, 192, 190);
            background-color: rgb(20, 38, 82);
        }}
        QDoubleSpinBox::up-button, QSpinBox::up-button {{
            subcontrol-position: top right;
            border-bottom: 1px solid rgb(91, 192, 190);
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
            border: 2px solid rgb(91, 192, 190);
            background-color: rgb(15, 27, 61);
        }}
        QCheckBox::indicator:checked {{
            background-color: rgb(46, 196, 182);
            border-color: rgb(46, 196, 182);
        }}

        QTabWidget::pane {{
            border: 1px solid rgb(65, 83, 112);
            border-radius: {field_radius}px;
        }}
        QTabBar::tab {{
            color: rgb(234, 234, 234);
            background-color: rgb(20, 38, 82);
            min-height: {max(28, field_height - 4)}px;
            padding: 2px {padding * 2}px;
            border: 1px solid rgb(65, 83, 112);
        }}
        QTabBar::tab:selected {{
            color: rgb(11, 19, 43);
            background-color: rgb(91, 192, 190);
        }}

        QHeaderView::section {{
            color: rgb(234, 234, 234);
            background-color: rgb(20, 38, 82);
            border: 1px solid rgb(65, 83, 112);
            padding: {padding}px;
        }}
        QTableWidget::item, QListWidget::item {{
            color: rgb(245, 247, 250);
            background-color: rgb(15, 27, 61);
            padding: {max(2, padding // 2)}px;
        }}
        QTableWidget::item:selected, QListWidget::item:selected {{
            color: rgb(11, 19, 43);
            background-color: rgb(46, 196, 182);
        }}

        QScrollArea, QScrollArea > QWidget > QWidget {{
            border: none;
            background-color: rgb(11, 19, 43);
        }}
        QScrollBar:vertical {{
            background-color: rgb(15, 27, 61);
            width: {scroll_width}px;
            margin: 0;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar::handle:vertical {{
            background-color: rgb(91, 192, 190);
            min-height: {max(32, field_height)}px;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar:horizontal {{
            background-color: rgb(15, 27, 61);
            height: {scroll_width}px;
            margin: 0;
            border-radius: {scroll_radius}px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: rgb(91, 192, 190);
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
            background-color: rgb(11, 19, 43);
        }}
    """
