from typing import Any, Dict, Optional
from models import DataModel
from views import MainWindow
from parsers import BaseParser


class DataController:
    """Controller layer - connects Model and View."""

    def __init__(self, model: DataModel, view: MainWindow):
        self._model = model
        self._view = view

        self._view.file_selected.connect(self.on_file_selected)
        self._view.parser_changed.connect(self.on_parser_changed)
        self._view.refresh_requested.connect(self.on_refresh)

        self._view.set_parsers(self._model.get_parser_names())

    def on_file_selected(self, file_path: str):
        self._model.set_file(file_path)
        self._view.set_file_label(file_path)

        parser = self._model.auto_detect_parser()
        if parser:
            self._view.combo_parser.setCurrentText(parser.name)
            self.load_data(parser)
        else:
            self._view.show_error("Error", "No suitable parser found")

    def on_parser_changed(self, parser_name: str):
        if not self._model.get_current_file():
            return

        self._model.set_parser(parser_name)
        parser = self._model.get_current_parser()
        if parser:
            self.load_data(parser)

    def load_data(self, parser: Optional[BaseParser] = None):
        result = self._model.parse_file(parser)

        if not result["success"]:
            self._view.show_error("Parse Error", result.get("error", "Unknown error"))
            return

        data = result["data"]
        data_type = data.get("type", "")

        if data_type == "text":
            self._view.display_text_data(data.get("lines", []))
        elif data_type == "json":
            self._view.display_json_data(data.get("content"))
        elif data_type == "csv":
            self._view.display_csv_data(data.get("headers", []), data.get("rows", []))
        elif data_type == "pickle":
            self._view.display_pickle_data(data.get("content"))
        elif data_type == "hex":
            self._view.display_hex_data(data.get("lines", []))

    def on_refresh(self):
        parser = self._model.get_current_parser()
        if parser and self._model.get_current_file():
            self.load_data(parser)