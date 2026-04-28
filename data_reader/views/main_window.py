from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QComboBox, QTextEdit, QLabel,
                               QFileDialog, QMessageBox)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent


class DropTextEdit(QTextEdit):
    """QTextEdit with drag and drop support."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.file_dropped.emit(file_path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class MainWindow(QMainWindow):
    """View layer - main application window."""

    file_selected = Signal(str)
    parser_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Reader - MVC")
        self.setGeometry(100, 100, 900, 600)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        toolbar = QHBoxLayout()
        self.btn_open = QPushButton("Open File")
        self.combo_parser = QComboBox()
        self.combo_parser.setEnabled(False)
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet("color: gray;")

        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(QLabel("Parser:"))
        toolbar.addWidget(self.combo_parser)
        toolbar.addWidget(self.lbl_file, stretch=1)

        self.text_edit = DropTextEdit()
        self.text_edit.setFont(QFont("Courier New", 10))
        self.text_edit.setReadOnly(True)
        self.text_edit.file_dropped.connect(self.file_selected.emit)

        layout.addLayout(toolbar)
        layout.addWidget(self.text_edit)

        self.btn_open.clicked.connect(self._on_open_clicked)
        self.combo_parser.currentTextChanged.connect(self._on_parser_changed)

    def _on_open_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Data File")
        if path:
            self.file_selected.emit(path)

    def _on_parser_changed(self, parser_name: str):
        if parser_name:
            self.parser_changed.emit(parser_name)

    def set_parsers(self, parser_names: list):
        self.combo_parser.clear()
        self.combo_parser.addItems(parser_names)
        self.combo_parser.setEnabled(True)

    def set_file_label(self, path: str):
        self.lbl_file.setText(path)
        self.lbl_file.setStyleSheet("color: black;")

    def display_text_data(self, lines: list):
        self.text_edit.setPlainText("".join(str(line) for line in lines))

    def display_json_data(self, content):
        import json
        self.text_edit.setPlainText(json.dumps(content, indent=2, ensure_ascii=False))

    def display_csv_data(self, headers: list, rows: list):
        lines = []
        if headers:
            lines.append(",".join(headers))
        for row in rows:
            lines.append(",".join(row))
        self.text_edit.setPlainText("\n".join(lines))

    def display_hex_data(self, lines: list):
        self.text_edit.setPlainText("\n".join(lines))

    def _format_dict_list(self, obj, indent=0):
        """Format dict/list with newlines after commas, like a text formatter."""
        spaces = "    " * indent
        if isinstance(obj, dict):
            lines = ["{"]
            for k, v in obj.items():
                comma = "," if list(obj.keys())[-1] != k else ""
                if isinstance(v, (dict, list)):
                    formatted = self._format_dict_list(v, indent + 1)
                    lines.append(f'{spaces}    "{k}": {formatted}{comma}')
                else:
                    lines.append(f'{spaces}    "{k}": {repr(v)}{comma}')
            lines.append(spaces + "}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            lines = ["["]
            for i, item in enumerate(obj):
                comma = "," if i < len(obj) - 1 else ""
                if isinstance(item, (dict, list)):
                    formatted = self._format_dict_list(item, indent + 1)
                    lines.append(f'{spaces}    {formatted}{comma}')
                else:
                    lines.append(f'{spaces}    {repr(item)}{comma}')
            lines.append(spaces + "]")
            return "\n".join(lines)
        else:
            return repr(obj)

    def display_pickle_data(self, content):
        if isinstance(content, (dict, list)):
            self.text_edit.setPlainText(self._format_dict_list(content))
        else:
            self.text_edit.setPlainText(repr(content))

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.file_selected.emit(file_path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)
