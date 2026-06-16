import sys
import time
import threading

from utils.qt_compat import QObject, Signal, Slot, Qt


class TeeStream:
    def __init__(self, original_stream, level, manager):
        self.original_stream = original_stream
        self.level = level
        self.manager = manager
        self.buffer = ""
        self.lock = threading.Lock()

    def write(self, text):
        self.original_stream.write(text)
        self.original_stream.flush()

        if not text:
            return

        with self.lock:
            self.buffer += text

            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                line = line.rstrip("\r")

                if line.strip():
                    self.manager.push_message(self.level, line)

    def flush(self):
        self.original_stream.flush()

    def isatty(self):
        return self.original_stream.isatty()

    def __getattr__(self, name):
        return getattr(self.original_stream, name)


class UiLogger(QObject):
    message_ready = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.installed = False
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self.widgets = []
        self.history = []
        self.max_history = 300

        self.message_ready.connect(self._append_to_widgets)

    def install(self):
        if self.installed:
            return

        sys.stdout = TeeStream(self.original_stdout, "INFO", self)
        sys.stderr = TeeStream(self.original_stderr, "ERROR", self)

        self.installed = True

    def restore(self):
        if not self.installed:
            return

        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        self.installed = False

    def push_message(self, level, message):
        timestamp = time.strftime("%H:%M:%S")

        if level == "ERROR":
            final_message = f"[{timestamp}] [ERROR] {message}"
        else:
            final_message = f"[{timestamp}] {message}"

        self.history.append((level, final_message))

        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        self.message_ready.emit(level, final_message)

    def attach_list_widget(self, widget, max_items=80, load_history=True):
        if widget is None:
            return

        if widget not in self.widgets:
            self.widgets.append(widget)

        widget.setProperty("_ui_logger_max_items", max_items)

        # Muy importante: que no se coma el espacio la barra horizontal.
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        widget.setWordWrap(True)

        self.apply_log_widget_style(widget)

        try:
            widget.destroyed.connect(lambda: self.detach_list_widget(widget))
        except Exception:
            pass

        if load_history:
            for level, message in self.history[-max_items:]:
                self._append_to_single_widget(widget, level, message)

    def detach_list_widget(self, widget):
        if widget in self.widgets:
            self.widgets.remove(widget)

    def apply_log_widget_style(self, widget):
        widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: rgb(234, 234, 234);
                border: none;
                padding: 4px;
                outline: none;
                font-size: 11px;
            }

            QListWidget::item {
                padding: 2px 6px;
            }

            QListWidget::item:selected {
                background-color: rgb(46, 196, 182);
                color: rgb(11, 19, 43);
            }

            QScrollBar:vertical {
                background-color: rgb(18, 31, 68);
                width: 18px;
                margin: 18px 0px 18px 0px;
                border: 1px solid rgb(42, 58, 97);
            }

            QScrollBar::handle:vertical {
                background-color: rgb(71, 101, 150);
                min-height: 24px;
                border-radius: 7px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: rgb(91, 120, 176);
            }

            QScrollBar::sub-line:vertical {
                background-color: rgb(20, 38, 82);
                height: 18px;
                border: 1px solid rgb(74, 101, 150);
                border-radius: 7px;

                subcontrol-position: top;
                subcontrol-origin: margin;
            }
                             
            QScrollBar::add-line:vertical {
                background-color: rgb(20, 38, 82);
                height: 18px;
                border: 1px solid rgb(74, 101, 150);
                border-radius: 7px;

                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
                    
            QScrollBar::sub-line:vertical:hover,
            QScrollBar::add-line:vertical:hover {
                background-color: rgb(27, 50, 105);
                border-color: rgb(91, 192, 190);
            }
            
            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                image: none;
                width: 0px;
                height: 0px;
            }
                             
            QScrollBar::up-arrow:vertical:hover,
            QScrollBar::down-arrow:vertical:hover {
                border-bottom-color: rgb(46, 196, 182);
                border-top-color: rgb(46, 196, 182);
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

    @Slot(str, str)
    def _append_to_widgets(self, level, message):
        dead_widgets = []

        for widget in list(self.widgets):
            try:
                self._append_to_single_widget(widget, level, message)
            except RuntimeError:
                dead_widgets.append(widget)
            except Exception:
                dead_widgets.append(widget)

        for widget in dead_widgets:
            self.detach_list_widget(widget)

    def _append_to_single_widget(self, widget, level, message):
        widget.addItem(message)

        max_items = widget.property("_ui_logger_max_items") or 80

        while widget.count() > max_items:
            widget.takeItem(0)

        bar = widget.verticalScrollBar()
        was_at_btm = bar.value() >= bar.maximum() -2

        if was_at_btm:
            widget.scrollToBottom()


_ui_logger_instance = None


def get_ui_logger():
    global _ui_logger_instance

    if _ui_logger_instance is None:
        _ui_logger_instance = UiLogger()

    return _ui_logger_instance